import sqlite3


def main() -> None:
    conn = sqlite3.Connection("radio.sqlite3")
    conn.execute("""
CREATE TABLE IF NOT EXISTS "radioairplay_logs" (
    "id" INTEGER PRIMARY KEY,
    "radio" TEXT NOT NULL,
    "day" TEXT NOT NULL,
    "time" TEXT,
    "artist" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    UNIQUE ("radio", "time", "artist", "title")
)
""")
    conn.execute("""
CREATE TABLE IF NOT EXISTS "radio_logs" (
    "id" INTEGER PRIMARY KEY,
    "radio" TEXT NOT NULL,
    "dtime" INTEGER NOT NULL,
    "artist" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    UNIQUE ("radio", "dtime")
)
""")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
