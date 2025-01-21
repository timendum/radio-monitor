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
    conn.execute("""
        DELETE FROM radio_songs AS a
        WHERE NOT EXISTS (
            SELECT b.id
            FROM radio_logs AS b
            WHERE b.id = a.id
        )""")
    conn.execute("""
        DELETE FROM song_skipped AS a
        WHERE NOT EXISTS (
            SELECT b.id
            FROM radio_logs AS b
            WHERE b.title = a.title
            AND b.artist = a.artist
        )""")
    conn.commit()
    conn.execute("VACUUM")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
