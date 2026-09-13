import logging

from core import SupportSession
from services.assistant import SupportAssistant
from services.storage import SqliteSessionRepository
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)

LEAD_FIRST_QUESTION = "Как к вам обращаться?"
SUPPORT_FIRST_QUESTION = "Как к вам обращаться?"

FINAL_LEAD_MESSAGE = (
    "Спасибо! Заявку на диагностику принял. "
    "Обычно это 1–2 рабочих дня — Максим напишет в Telegram и предложит понятный следующий шаг."
)
FINAL_SUPPORT_MESSAGE = (
    "Спасибо! Передал обращение специалисту NeiroBridge. "
    "Мы свяжемся с вами в ближайшее время."
)


class SupportWorkflowService:
    def __init__(
        self,
        assistant: SupportAssistant,
        notifier: OperatorNotifier,
        session_repository: SqliteSessionRepository,
    ) -> None:
        self._assistant = assistant
        self._notifier = notifier
        self._sessions = session_repository

    def start_mode(self, session: SupportSession, mode: str) -> str:
        session.reset()
        session.started = True
        session.ticket.mode = mode  # type: ignore[assignment]
        self._prefill_contact_from_telegram(session)
        question = LEAD_FIRST_QUESTION if mode == "lead" else SUPPORT_FIRST_QUESTION
        session.add_assistant_message(question)
        self._sessions.save(session)
        return question

    async def process_message(self, session: SupportSession, message_text: str) -> str:
        if session.submitted:
            already = (
                FINAL_LEAD_MESSAGE if session.ticket.mode == "lead" else FINAL_SUPPORT_MESSAGE
            )
            return f"{already} Если нужна новая заявка, нажмите /reset."

        if not session.ticket.mode:
            return (
                "Сначала выберите сценарий: новая заявка на диагностику или поддержка по проекту."
            )

        self._prefill_contact_from_telegram(session)
        history_before_turn = session.recent_history()
        is_new_session = not history_before_turn and not session.started

        turn = await self._assistant.generate_turn(
            current_ticket=session.ticket,
            user_message=message_text,
            is_new_session=is_new_session,
            conversation_history=history_before_turn,
            last_assistant_message=session.last_assistant_message,
            telegram_first_name=session.telegram_first_name,
        )

        session.add_user_message(message_text)
        session.ticket.merge(turn.extracted_ticket)
        session.started = True

        if session.ticket.is_complete() and turn.ready_to_submit:
            await self._notifier.send_ticket(session)
            session.submitted = True
            final_message = (
                FINAL_LEAD_MESSAGE if session.ticket.mode == "lead" else FINAL_SUPPORT_MESSAGE
            )
            session.add_assistant_message(final_message)
            self._sessions.save(session)
            logger.info("Ticket submitted for user_id=%s mode=%s", session.user_id, session.ticket.mode)
            return final_message

        session.add_assistant_message(turn.reply)
        self._sessions.save(session)
        return turn.reply

    @staticmethod
    def _prefill_contact_from_telegram(session: SupportSession) -> None:
        if session.ticket.contact:
            return
        if session.telegram_username:
            session.ticket.contact = f"@{session.telegram_username}"

    async def close(self) -> None:
        await self._assistant.close()
