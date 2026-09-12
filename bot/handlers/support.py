import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.utils import mode_keyboard
from core import SupportSession
from services import SupportWorkflowService
from services.storage import SqliteSessionRepository

logger = logging.getLogger(__name__)
router = Router()

START_MESSAGE = (
    "Здравствуйте! Я ассистент студии NeiroBridge.\n"
    "Помогаю оформить заявку на диагностику или передать обращение в поддержку.\n\n"
    "Сайт: neirobridge.ru\n"
    "Telegram: @neirobridge_ai\n\n"
    "Выберите, с чего начнём."
)
HELP_MESSAGE = (
    "Я собираю заявку для NeiroBridge в двух режимах:\n"
    "• новая заявка — бесплатная диагностика, 1–2 рабочих дня;\n"
    "• поддержка — если уже есть проект и что-то сломалось.\n\n"
    "Команды: /start — начать, /reset — начать заново.\n"
    "Сайт: https://neirobridge.ru"
)
RESET_MESSAGE = "Диалог сброшен. Выберите сценарий, и начнём заново."
GENERIC_ERROR_MESSAGE = "Сейчас не удалось обработать обращение. Попробуйте ещё раз через пару минут."
UNSUPPORTED_MESSAGE = "Напишите, пожалуйста, текстом — так я смогу оформить заявку."
MODE_LEAD_INTRO = "Отлично, оформляю заявку на бесплатную диагностику."
MODE_SUPPORT_INTRO = "Хорошо, оформляю обращение в поддержку по проекту."


@router.message(Command("start"))
async def handle_start(
    message: Message,
    session_repository: SqliteSessionRepository,
) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя. Попробуйте ещё раз.")
        return

    session = session_repository.get_or_create(
        user_id=user.id,
        chat_id=message.chat.id,
        telegram_username=user.username,
        telegram_first_name=user.first_name,
    )
    session.reset()
    session.started = True
    session.add_assistant_message(START_MESSAGE)
    session_repository.save(session)
    await message.answer(START_MESSAGE, reply_markup=mode_keyboard())


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(HELP_MESSAGE, reply_markup=mode_keyboard())


@router.message(Command("reset"))
async def handle_reset(
    message: Message,
    session_repository: SqliteSessionRepository,
) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось сбросить диалог. Попробуйте ещё раз.")
        return

    session_repository.reset(user.id)
    session = session_repository.get_or_create(
        user_id=user.id,
        chat_id=message.chat.id,
        telegram_username=user.username,
        telegram_first_name=user.first_name,
    )
    session.started = True
    session.add_assistant_message(RESET_MESSAGE)
    session_repository.save(session)
    await message.answer(RESET_MESSAGE, reply_markup=mode_keyboard())


@router.callback_query(F.data.in_({"mode:lead", "mode:support"}))
async def handle_mode_choice(
    callback: CallbackQuery,
    session_repository: SqliteSessionRepository,
    workflow: SupportWorkflowService,
) -> None:
    user = callback.from_user
    if callback.message is None:
        await callback.answer()
        return

    mode = "lead" if callback.data == "mode:lead" else "support"
    session: SupportSession = session_repository.get_or_create(
        user_id=user.id,
        chat_id=callback.message.chat.id,
        telegram_username=user.username,
        telegram_first_name=user.first_name,
    )
    question = workflow.start_mode(session, mode)
    intro = MODE_LEAD_INTRO if mode == "lead" else MODE_SUPPORT_INTRO
    await callback.answer()
    await callback.message.answer(f"{intro} {question}")


@router.message(F.text)
async def handle_text_message(
    message: Message,
    session_repository: SqliteSessionRepository,
    workflow: SupportWorkflowService,
) -> None:
    user = message.from_user
    if user is None or not message.text:
        await message.answer("Не удалось обработать сообщение. Попробуйте ещё раз.")
        return

    session: SupportSession = session_repository.get_or_create(
        user_id=user.id,
        chat_id=message.chat.id,
        telegram_username=user.username,
        telegram_first_name=user.first_name,
    )

    try:
        reply = await workflow.process_message(session, message.text)
        markup = mode_keyboard() if not session.ticket.mode else None
        await message.answer(reply, reply_markup=markup)
    except Exception:
        logger.exception("Failed to process incoming support message")
        await message.answer(GENERIC_ERROR_MESSAGE)


@router.message()
async def handle_unsupported_message(message: Message) -> None:
    await message.answer(UNSUPPORTED_MESSAGE)
