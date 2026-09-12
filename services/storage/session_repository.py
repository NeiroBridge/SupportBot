import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core import SupportSession


class SqliteSessionRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id INTEGER PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def get_or_create(
        self,
        user_id: int,
        chat_id: int,
        telegram_username: str | None,
        telegram_first_name: str | None,
    ) -> SupportSession:
        session = self._load(user_id)
        if session is None:
            session = SupportSession(
                user_id=user_id,
                chat_id=chat_id,
                telegram_username=telegram_username,
                telegram_first_name=telegram_first_name,
            )
            self.save(session)
            return session

        session.chat_id = chat_id
        session.telegram_username = telegram_username
        session.telegram_first_name = telegram_first_name
        self.save(session)
        return session

    def save(self, session: SupportSession) -> None:
        payload = session.model_dump_json()
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (user_id, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (session.user_id, payload, updated_at),
            )
            connection.commit()

    def reset(self, user_id: int) -> None:
        session = self._load(user_id)
        if session is None:
            return
        session.reset()
        self.save(session)

    def _load(self, user_id: int) -> SupportSession | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM sessions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return SupportSession.model_validate_json(row["payload"])
