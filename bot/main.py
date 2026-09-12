import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode

from bot.handlers import router
from core import get_settings, setup_logging
from services import SupportWorkflowService
from services.assistant import SupportAssistant
from services.storage import SqliteSessionRepository
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)


def _build_bot(token: str, telegram_api_url: str) -> Bot:
    session = None
    if telegram_api_url:
        session = AiohttpSession(api=TelegramAPIServer.from_base(telegram_api_url))
        logger.info("Using custom Telegram API: %s", telegram_api_url)
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def run_bot() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    bot = _build_bot(settings.telegram_bot_token, settings.telegram_api_url)
    session_repository = SqliteSessionRepository(settings.sqlite_path)
    assistant = SupportAssistant(settings)
    notifier = OperatorNotifier(bot, settings)
    workflow = SupportWorkflowService(
        assistant=assistant,
        notifier=notifier,
        session_repository=session_repository,
    )

    dp = Dispatcher()
    dp.include_router(router)
    dp["session_repository"] = session_repository
    dp["workflow"] = workflow

    logger.info("Starting NeiroBridge support bot")
    try:
        await dp.start_polling(bot)
    finally:
        await workflow.close()
        await bot.session.close()
