from core.schemas import IntakeTicket, SupportSession


def test_lead_ticket_is_complete_only_with_lead_fields() -> None:
    ticket = IntakeTicket(
        mode="lead",
        name="Анна",
        contact="@anna",
        company="пекарня",
        request_type="Telegram-бот",
        goal="собирать заявки ночью",
        current_tools="WhatsApp",
        deadline="в течение месяца",
    )
    assert ticket.is_complete()
    assert ticket.missing_fields() == []


def test_support_ticket_ignores_lead_fields() -> None:
    ticket = IntakeTicket(
        mode="support",
        name="Иван",
        contact="+79001234567",
        project_name="DeskMate",
        problem_summary="бот не отвечает",
        occurred_at="сегодня утром",
        location="бот",
        priority="срочно",
    )
    assert ticket.is_complete()


def test_incomplete_without_mode() -> None:
    ticket = IntakeTicket(name="Анна", contact="@anna")
    assert not ticket.is_complete()


def test_merge_does_not_change_mode() -> None:
    ticket = IntakeTicket(mode="lead", name="Анна")
    ticket.merge(IntakeTicket(mode="support", company="студия"))
    assert ticket.mode == "lead"
    assert ticket.company == "студия"


def test_submitted_session_keeps_mode() -> None:
    session = SupportSession(user_id=1, chat_id=1)
    session.ticket.mode = "support"
    session.submitted = True
    assert session.submitted
    assert session.ticket.mode == "support"


def test_session_reset_clears_ticket_and_history() -> None:
    session = SupportSession(user_id=1, chat_id=1)
    session.ticket.mode = "lead"
    session.add_user_message("привет")
    session.submitted = True
    session.reset()
    assert session.ticket.mode is None
    assert session.history == []
    assert session.submitted is False
