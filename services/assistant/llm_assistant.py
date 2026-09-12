import asyncio
import json
import logging
import re

import httpx

from core import AssistantTurn, IntakeTicket, Settings
from core.schemas import DialogueMessage
from services.assistant.prompts import ASSISTANT_RESPONSE_SCHEMA, SUPPORT_ASSISTANT_PROMPT

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}

LEAD_QUESTIONS = {
    "name": "Как к вам обращаться?",
    "contact": "Оставьте контакт для связи: телефон, Telegram или email.",
    "company": "Как называется компания или в какой вы нише? Если для себя — так и напишите.",
    "request_type": "Что нужно автоматизировать: AI-агент, Telegram-бот, RAG, n8n, сайт, CRM / интеграции или другое?",
    "goal": "Какую задачу или боль хотите закрыть в первую очередь?",
    "current_tools": "Чем уже пользуетесь: CRM, таблицы, Telegram, n8n — или пока ничего?",
    "deadline": "Когда это нужно: на этой неделе, в ближайший месяц или без жёсткого срока?",
}

SUPPORT_QUESTIONS = {
    "name": "Как к вам обращаться?",
    "contact": "Оставьте контакт для связи: телефон, Telegram или email.",
    "project_name": "По какому проекту или боту нужна поддержка?",
    "problem_summary": "Коротко опишите, что случилось.",
    "occurred_at": "Когда проблема началась?",
    "location": "Где проявляется: сайт, бот, n8n, CRM, сервер или другое?",
    "priority": "Насколько срочно: срочно, средне или низкий приоритет?",
}

REQUEST_TYPE_ALIASES = {
    "агент": "AI-агент",
    "ai": "AI-агент",
    "бот": "Telegram-бот",
    "telegram": "Telegram-бот",
    "rag": "RAG",
    "баз": "RAG",
    "n8n": "n8n",
    "сайт": "сайт",
    "лендинг": "сайт",
    "crm": "CRM / интеграции",
    "интеграц": "CRM / интеграции",
}

LOCATION_ALIASES = {
    "сайт": "сайт",
    "бот": "бот",
    "telegram": "бот",
    "n8n": "n8n",
    "crm": "CRM",
    "сервер": "сервер",
    "vps": "сервер",
}


class SupportAssistant:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.openai_base_url,
            timeout=httpx.Timeout(45.0, connect=12.0),
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
        )

    async def generate_turn(
        self,
        current_ticket: IntakeTicket,
        user_message: str,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        last_assistant_message: str | None,
        telegram_first_name: str | None,
    ) -> AssistantTurn:
        payload = {
            "model": self._settings.openai_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SUPPORT_ASSISTANT_PROMPT},
                {
                    "role": "user",
                    "content": self._build_user_prompt(
                        current_ticket=current_ticket,
                        user_message=user_message,
                        is_new_session=is_new_session,
                        conversation_history=conversation_history,
                        last_assistant_message=last_assistant_message,
                        telegram_first_name=telegram_first_name,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": ASSISTANT_RESPONSE_SCHEMA,
            },
        }

        try:
            response = await self._post_with_retries(payload)
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return AssistantTurn.model_validate(json.loads(content))
        except Exception:
            logger.exception("Falling back to local support turn generation")
            return self._build_fallback_turn(
                current_ticket=current_ticket,
                user_message=user_message,
                last_assistant_message=last_assistant_message,
            )

    async def close(self) -> None:
        await self._client.aclose()

    async def _post_with_retries(self, payload: dict) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(1, 4):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in RETRYABLE_STATUS_CODES or attempt == 3:
                    raise
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == 3:
                    break
            await asyncio.sleep(0.75 * attempt)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _build_user_prompt(
        current_ticket: IntakeTicket,
        user_message: str,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        last_assistant_message: str | None,
        telegram_first_name: str | None,
    ) -> str:
        ticket_json = json.dumps(current_ticket.model_dump(), ensure_ascii=False, indent=2)
        history_json = json.dumps(
            [message.model_dump() for message in conversation_history],
            ensure_ascii=False,
            indent=2,
        )
        return (
            f"is_new_session: {str(is_new_session).lower()}\n"
            f"telegram_first_name: {telegram_first_name or 'null'}\n"
            f"current_ticket:\n{ticket_json}\n\n"
            f"conversation_history:\n{history_json}\n\n"
            f"last_assistant_message:\n{last_assistant_message or 'null'}\n\n"
            f"latest_user_message:\n{user_message}"
        )

    def _build_fallback_turn(
        self,
        current_ticket: IntakeTicket,
        user_message: str,
        last_assistant_message: str | None,
    ) -> AssistantTurn:
        message = " ".join(user_message.split()).strip()
        extracted = IntakeTicket()
        requested = self._detect_requested_field(last_assistant_message, current_ticket.mode)

        if self._is_repeat_question_request(message.lower()):
            repeated = last_assistant_message or "Пока мы не дошли до следующего вопроса."
            return AssistantTurn(
                reply=f"Последний вопрос был таким: {repeated}",
                extracted_ticket=extracted,
                ready_to_submit=current_ticket.is_complete(),
            )

        if requested == "name" or (not current_ticket.name and self._looks_like_name(message)):
            if self._looks_like_name(message):
                extracted.name = message
        if requested == "contact" or not current_ticket.contact:
            contact = self._extract_contact(message)
            if contact:
                extracted.contact = contact
        if current_ticket.mode == "lead":
            self._fill_lead_fallback(extracted, current_ticket, message, requested)
        elif current_ticket.mode == "support":
            self._fill_support_fallback(extracted, current_ticket, message, requested)

        merged = current_ticket.model_copy(deep=True)
        merged.merge(extracted)
        return AssistantTurn(
            reply=self._next_question(merged),
            extracted_ticket=extracted,
            ready_to_submit=merged.is_complete(),
        )

    def _fill_lead_fallback(
        self,
        extracted: IntakeTicket,
        current: IntakeTicket,
        message: str,
        requested: str | None,
    ) -> None:
        if requested == "company" or (not current.company and requested is None):
            if not self._looks_like_name(message) or requested == "company":
                extracted.company = message
        request_type = self._extract_request_type(message)
        if request_type and (requested == "request_type" or not current.request_type):
            extracted.request_type = request_type
        if requested == "goal":
            extracted.goal = message
        if requested == "current_tools":
            extracted.current_tools = message
        if requested == "deadline":
            extracted.deadline = message

    def _fill_support_fallback(
        self,
        extracted: IntakeTicket,
        current: IntakeTicket,
        message: str,
        requested: str | None,
    ) -> None:
        if requested == "project_name":
            extracted.project_name = message
        if requested == "problem":
            extracted.problem_summary = message
        if requested == "occurred_at" or self._looks_like_time_answer(message.lower()):
            if requested == "occurred_at" or not current.occurred_at:
                extracted.occurred_at = message
        location = self._extract_location(message)
        if location and (requested == "location" or not current.location):
            extracted.location = location
        priority = self._extract_priority(message.lower())
        if priority and (requested == "priority" or not current.priority):
            extracted.priority = priority

    def _next_question(self, ticket: IntakeTicket) -> str:
        questions = LEAD_QUESTIONS if ticket.mode == "lead" else SUPPORT_QUESTIONS
        missing = ticket.missing_fields()
        if not missing:
            return "Спасибо! Проверяю, всё ли собрано по заявке."
        return questions[missing[0]]

    @staticmethod
    def _is_repeat_question_request(message_lower: str) -> bool:
        triggers = (
            "какой был прошлый вопрос",
            "повтори вопрос",
            "что ты спрашивал",
            "что вы спрашивали",
        )
        return any(trigger in message_lower for trigger in triggers)

    @staticmethod
    def _detect_requested_field(last_assistant_message: str | None, mode: str | None) -> str | None:
        if not last_assistant_message:
            return None
        message = last_assistant_message.lower()
        mapping = [
            (("как к вам обращаться", "как вас зовут"), "name"),
            (("контакт", "телефон", "email"), "contact"),
            (("компания", "нише"), "company"),
            (("автоматизировать", "ai-агент", "telegram-бот"), "request_type"),
            (("задачу", "боль"), "goal"),
            (("пользуетесь", "crm", "пока ничего"), "current_tools"),
            (("когда это нужно", "срок"), "deadline"),
            (("какому проекту", "какому боту"), "project_name"),
            (("что случилось", "опишите"), "problem"),
            (("когда проблема", "когда началась"), "occurred_at"),
            (("где проявляется", "сайт, бот"), "location"),
            (("насколько срочно", "приоритет"), "priority"),
        ]
        for phrases, field in mapping:
            if any(phrase in message for phrase in phrases):
                if mode == "lead" and field in {"project_name", "problem", "occurred_at", "location", "priority"}:
                    continue
                if mode == "support" and field in {"company", "request_type", "goal", "current_tools", "deadline"}:
                    continue
                return field
        return None

    @staticmethod
    def _looks_like_name(message: str) -> bool:
        lowered = message.lower()
        blockers = ("проблем", "ошибк", "сайт", "бот", "срочно", "не ", "n8n", "crm")
        if any(blocker in lowered for blocker in blockers):
            return False
        if any(char.isdigit() for char in message):
            return False
        words = [word for word in re.split(r"\s+", message) if word]
        return 1 <= len(words) <= 3

    @staticmethod
    def _extract_contact(message: str) -> str | None:
        if message.startswith("@") and len(message) > 1:
            return message
        if "@" in message and "." in message:
            return message
        compact = re.sub(r"[^\d+]", "", message)
        digits = re.sub(r"\D", "", compact)
        if len(digits) >= 10:
            return compact
        return None

    @staticmethod
    def _looks_like_time_answer(message_lower: str) -> bool:
        tokens = ("минут", "час", "день", "недел", "месяц", "сегодня", "вчера", "утром", "назад")
        return any(token in message_lower for token in tokens)

    @staticmethod
    def _extract_priority(message_lower: str) -> str | None:
        if any(token in message_lower for token in ("срочно", "критично", "горит")):
            return "срочно"
        if "низк" in message_lower:
            return "низкий приоритет"
        if any(token in message_lower for token in ("средне", "не срочно", "терпит")):
            return "средне"
        return None

    @staticmethod
    def _extract_request_type(message: str) -> str | None:
        lowered = message.lower()
        for alias, value in REQUEST_TYPE_ALIASES.items():
            if alias in lowered:
                return value
        return None

    @staticmethod
    def _extract_location(message: str) -> str | None:
        lowered = message.lower()
        for alias, value in LOCATION_ALIASES.items():
            if alias in lowered:
                return value
        return None
