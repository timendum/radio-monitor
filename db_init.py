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
CREATE INDEX IF NOT EXISTS "radio_logs_radioidx" ON "radio_logs" (
    "radio"
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
    conn.execute("""
CREATE TABLE IF NOT EXISTS "radio_songs" (
    "id" INTEGER PRIMARY KEY,
    "radio" TEXT NOT NULL,
    "dtime" INTEGER NOT NULL,
    "artist" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "year" INT NOT NULL,
    "country" TEXT NOT NULL,
    UNIQUE ("radio", "dtime")
)
""")
    conn.execute("""
CREATE TABLE IF NOT EXISTS "song_matches" (
    "id" INTEGER PRIMARY KEY,
    "artist" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "okartist" TEXT NOT NULL,
    "oktitle" TEXT NOT NULL,
    "okyear" INT NOT NULL,
    "okcountry" TEXT NOT NULL,
    UNIQUE ("artist", "title")
)
""")
    conn.execute("""
CREATE TABLE IF NOT EXISTS "song_skipped" (
    "id" INTEGER PRIMARY KEY,
    "artist" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    UNIQUE ("artist", "title")
)
""")
    conn.execute("""
CREATE TABLE IF NOT EXISTS "song_check" (
    "id" INTEGER PRIMARY KEY
)
""")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
