from html import escape

from core import IntakeTicket, SupportSession

MODE_TITLES = {
    "lead": "Новая заявка · диагностика",
    "support": "Поддержка по проекту",
}


def format_operator_ticket(session: SupportSession) -> str:
    ticket = session.ticket
    title = MODE_TITLES.get(ticket.mode or "", "Заявка")
    username = f"@{session.telegram_username}" if session.telegram_username else "—"
    lines = [
        f"<b>NeiroBridge · {escape(title)}</b>",
        "",
        f"<b>Имя:</b> {escape(ticket.name or '—')}",
        f"<b>Контакт:</b> {escape(ticket.contact or '—')}",
    ]
    if ticket.mode == "lead":
        lines.extend(
            [
                f"<b>Компания / ниша:</b> {escape(ticket.company or '—')}",
                f"<b>Тип запроса:</b> {escape(ticket.request_type or '—')}",
                f"<b>Задача:</b> {escape(ticket.goal or '—')}",
                f"<b>Чем пользуются:</b> {escape(ticket.current_tools or '—')}",
                f"<b>Срок:</b> {escape(ticket.deadline or '—')}",
            ]
        )
    else:
        lines.extend(
            [
                f"<b>Проект:</b> {escape(ticket.project_name or '—')}",
                f"<b>Проблема:</b> {escape(ticket.problem_summary or '—')}",
                f"<b>Когда возникло:</b> {escape(ticket.occurred_at or '—')}",
                f"<b>Где:</b> {escape(ticket.location or '—')}",
                f"<b>Приоритет:</b> {escape(ticket.priority or '—')}",
            ]
        )
    lines.extend(
        [
            "",
            f"<b>Telegram id:</b> {session.user_id}",
            f"<b>Telegram:</b> {escape(username)}",
            "",
            "Сайт: https://neirobridge.ru",
        ]
    )
    return "\n".join(lines)


def format_collected_ticket(ticket: IntakeTicket) -> str:
    lines = [
        f"Режим: {ticket.mode or '—'}",
        f"Имя: {ticket.name or '—'}",
        f"Контакт: {ticket.contact or '—'}",
        f"Компания: {ticket.company or '—'}",
        f"Тип запроса: {ticket.request_type or '—'}",
        f"Задача: {ticket.goal or '—'}",
        f"Инструменты: {ticket.current_tools or '—'}",
        f"Срок: {ticket.deadline or '—'}",
        f"Проект: {ticket.project_name or '—'}",
        f"Проблема: {ticket.problem_summary or '—'}",
        f"Когда: {ticket.occurred_at or '—'}",
        f"Где: {ticket.location or '—'}",
        f"Приоритет: {ticket.priority or '—'}",
    ]
    return "\n".join(lines)
