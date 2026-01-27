from pathlib import Path

from onlymaps import Database

from monitor import utils


def init_schema(conn: Database) -> None:
    base = Path(__file__).parent / Path("sql")
    with (base / Path("db_init.sql")).open("rt") as fi:
        sql = fi.read()
        statems = [""]
        for line in sql.splitlines():
            if not line:
                statems.append("")
            else:
                statems[-1] = statems[-1] + "\n" + line
    with conn.transaction():
        for statem in statems:
            if statem.strip():
                conn.exec(statem)


def init_data(conn: Database) -> None:
    base = Path(__file__).parent / Path("sql")
    with (base / Path("data_init.sql")).open("rt") as fi:
        with conn.transaction():
            sql = fi.read()
            for statem in sql.split(";"):
                conn.exec(statem)


def main() -> None:
    with utils.conn_db() as conn:
        init_schema(conn)
        init_data(conn)


if __name__ == "__main__":
    main()
