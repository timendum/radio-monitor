import sqlite3
from pathlib import Path

from monitor import db_init


def backup_tables(tables: list[str], out_sql_path: str, conn: sqlite3.Connection) -> None:
    sql_lines = []
    # Disable FKs in the dump for safe bulk import
    sql_lines.append("PRAGMA foreign_keys=OFF;")
    sql_lines.append("BEGIN;")
    for tbl in tables:
        # Get stable column order from PRAGMA table_info
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})")]
        if not cols:
            raise ValueError(f"Table not found or has no columns: {tbl}")
        col_list = ", ".join([f'"{c}"' for c in cols])

        select_parts = " || ',' || ".join([f"quote({c})" for c in cols])
        sql = f"""
            SELECT 'INSERT INTO "{tbl}"({col_list}) VALUES('
                || {select_parts} || ');'
            FROM "{tbl}"
        """
        for (insert_stmt,) in conn.execute(sql):
            sql_lines.append(insert_stmt)

    sql_lines.append("COMMIT;")
    sql_lines.append("PRAGMA foreign_keys=ON;")

    Path(out_sql_path).write_text("\n".join(sql_lines), encoding="utf-8")
    print(f"Wrote data-only dump for {len(tables)} table(s) to {out_sql_path}")


def main() -> None:
    conn = sqlite3.Connection("radio.sqlite3")
    backup_tables(["country", "station", "play"], "play_backup.sql", conn)
    backup_tables(["artist", "song", "song_artist"], "songs_backup.sql", conn)
    conn.close()
    Path("radio.sqlite3").unlink()
    conn = sqlite3.Connection("radio.sqlite3")
    db_init.init_schema(conn)
    conn.executescript(Path("play_backup.sql").read_text(encoding="utf-8"))
    print("Restored play data")
    db_init.init_data(conn)
    conn.commit()
    conn.close()
    print("Done")

if __name__ == "__main__":
    main()
