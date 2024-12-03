from datetime import datetime
import sqlite3


def insert_into_radio(
    radio: str, artist: str, title: str, timestamp: None | float | int = None
) -> None | tuple[str, str, str]:
    artist = artist.strip()
    title = title.strip()
    conn = sqlite3.Connection("radio.sqlite3")
    if not timestamp:
        timestamp = datetime.now().timestamp()
    pa, pt = conn.execute(
        "SELECT artist, title FROM radio_logs WHERE radio = ? ORDER BY abs(dtime-?) asc LIMIT 1",
        (radio, timestamp),
    ).fetchone() or ("", "")
    if pa == artist and pt == title:
        conn.close()
        return
    if not timestamp:
        timestamp = datetime.now().timestamp()
    conn.execute(
        "INSERT OR IGNORE INTO radio_logs (radio, dtime, artist, title) VALUES (?,?,?,?)",
        (
            radio,
            timestamp,
            artist,
            title,
        ),
    )
    conn.commit()
    conn.close()
    return radio, artist, title
