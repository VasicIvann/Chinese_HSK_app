"""Reset the quiz database and reseed with the CSV data."""

from __future__ import annotations

from sqlalchemy import delete

from db import init_db, get_session
from models import Entry, Quiz
from seed import ensure_seeded


def main() -> None:
    init_db()
    with get_session() as session:
        session.execute(delete(Entry))
        session.execute(delete(Quiz))
    ensure_seeded()


if __name__ == "__main__":
    main()
