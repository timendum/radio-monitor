import sqlite3
from pathlib import Path

from monitor import utils


def init_schema(conn: sqlite3.Connection) -> None:
    base = Path(__file__).parent / Path("sql")
    with (base / Path("db_init.sql")).open("rt") as fi:
        conn.executescript(fi.read())
    conn.commit()


def init_data(conn: sqlite3.Connection) -> None:
    base = Path(__file__).parent / Path("sql")
    with (base / Path("data_init.sql")).open("rt") as fi:
        conn.executescript(fi.read())
    conn.commit()


def main() -> None:
    with utils.conn_db() as conn:
        init_schema(conn)
        init_data(conn)


if __name__ == "__main__":
    main()
