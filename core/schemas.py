from typing import Literal

from pydantic import BaseModel, Field, field_validator

Mode = Literal["lead", "support"]
MessageRole = Literal["user", "assistant"]
Priority = Literal["срочно", "средне", "низкий приоритет"]
RequestType = Literal[
    "AI-агент",
    "Telegram-бот",
    "RAG",
    "n8n",
    "сайт",
    "CRM / интеграции",
    "другое",
]
SupportLocation = Literal["сайт", "бот", "n8n", "CRM", "сервер", "другое"]

LEAD_REQUIRED_FIELDS = (
    "name",
    "contact",
    "company",
    "request_type",
    "goal",
    "current_tools",
    "deadline",
)
SUPPORT_REQUIRED_FIELDS = (
    "name",
    "contact",
    "project_name",
    "problem_summary",
    "occurred_at",
    "location",
    "priority",
)


class IntakeTicket(BaseModel):
    mode: Mode | None = None
    name: str | None = None
    contact: str | None = None
    company: str | None = None
    request_type: RequestType | None = None
    goal: str | None = None
    current_tools: str | None = None
    deadline: str | None = None
    project_name: str | None = None
    problem_summary: str | None = None
    occurred_at: str | None = None
    location: SupportLocation | None = None
    priority: Priority | None = None

    @field_validator(
        "name",
        "contact",
        "company",
        "goal",
        "current_tools",
        "deadline",
        "project_name",
        "problem_summary",
        "occurred_at",
    )
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    def merge(self, other: "IntakeTicket") -> None:
        for field_name, value in other.model_dump().items():
            if field_name == "mode":
                continue
            if value not in (None, ""):
                setattr(self, field_name, value)

    def required_fields(self) -> tuple[str, ...]:
        if self.mode == "lead":
            return LEAD_REQUIRED_FIELDS
        if self.mode == "support":
            return SUPPORT_REQUIRED_FIELDS
        return ()

    def missing_fields(self) -> list[str]:
        return [name for name in self.required_fields() if not getattr(self, name)]

    def is_complete(self) -> bool:
        return bool(self.mode) and not self.missing_fields()


class DialogueMessage(BaseModel):
    role: MessageRole
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            raise ValueError("Dialogue message cannot be empty")
        return cleaned


class AssistantTurn(BaseModel):
    reply: str = Field(min_length=1)
    extracted_ticket: IntakeTicket = Field(default_factory=IntakeTicket)
    ready_to_submit: bool = False


class SupportSession(BaseModel):
    user_id: int
    chat_id: int
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    started: bool = False
    submitted: bool = False
    ticket: IntakeTicket = Field(default_factory=IntakeTicket)
    history: list[DialogueMessage] = Field(default_factory=list)

    def add_user_message(self, text: str) -> None:
        self._append_history("user", text)

    def add_assistant_message(self, text: str) -> None:
        self._append_history("assistant", text)

    def recent_history(self, limit: int = 8) -> list[DialogueMessage]:
        return list(self.history[-limit:])

    @property
    def last_assistant_message(self) -> str | None:
        for message in reversed(self.history):
            if message.role == "assistant":
                return message.text
        return None

    def reset(self) -> None:
        self.started = False
        self.submitted = False
        self.ticket = IntakeTicket()
        self.history = []

    def _append_history(self, role: MessageRole, text: str) -> None:
        self.history.append(DialogueMessage(role=role, text=text))
        if len(self.history) > 20:
            self.history = self.history[-20:]
