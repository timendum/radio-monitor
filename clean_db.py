import sqlite3


def main() -> None:
    conn = sqlite3.Connection("radio.sqlite3")
    conn.execute("""
        DELETE FROM song_check AS a
        WHERE NOT EXISTS (
            SELECT b.id
            FROM radio_songs b
            WHERE b.id = a.id
        )""")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
