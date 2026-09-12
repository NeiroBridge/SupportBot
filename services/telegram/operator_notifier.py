from aiogram import Bot
from aiogram.enums import ParseMode

from core import Settings, SupportSession
from bot.utils.formatter import format_operator_ticket


class OperatorNotifier:
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings

    async def send_ticket(self, session: SupportSession) -> None:
        await self._bot.send_message(
            self._settings.operator_chat_id,
            format_operator_ticket(session),
            parse_mode=ParseMode.HTML,
        )
