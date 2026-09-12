from core import SupportSession
from services.storage import SqliteSessionRepository


def test_sqlite_persists_and_reloads_session(tmp_path) -> None:
    db_path = tmp_path / "sessions.db"
    repository = SqliteSessionRepository(db_path)
    session = repository.get_or_create(7, 70, "demo", "Максим")
    session.ticket.mode = "lead"
    session.ticket.name = "Максим"
    session.add_user_message("нужен бот для заявок")
    repository.save(session)

    reloaded = SqliteSessionRepository(db_path).get_or_create(7, 70, "demo", "Максим")
    assert reloaded.ticket.mode == "lead"
    assert reloaded.ticket.name == "Максим"
    assert reloaded.history[0].text == "нужен бот для заявок"


def test_sqlite_reset_clears_state(tmp_path) -> None:
    repository = SqliteSessionRepository(tmp_path / "sessions.db")
    session = repository.get_or_create(3, 30, None, "Иван")
    session.ticket.mode = "support"
    session.submitted = True
    repository.save(session)

    repository.reset(3)
    restored = repository.get_or_create(3, 30, None, "Иван")
    assert restored.ticket.mode is None
    assert restored.submitted is False
