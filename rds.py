from datetime import datetime
import sqlite3

import requests


def main() -> None:
    r = requests.get("https://cdnapi.rds.it/v2/site/get_player_info")
    r.raise_for_status()
    d = r.json()["song_status"]["current_song"]
    if d["artist"] == "RDS":
        return
    conn = sqlite3.Connection("radio.sqlite3")
    pa, pt = conn.execute(
        "SELECT artist, title FROM radio_logs WHERE radio = ? ORDER BY dtime desc LIMIT 1",
        ("rds",),
    ).fetchone() or ("", "")
    if pa == d["artist"] and pt == d["title"]:
        conn.close()
        return
    conn.execute(
        "INSERT INTO radio_logs (radio, dtime, artist, title) VALUES (?,?,?,?)",
        (
            "rds",
            datetime.now().timestamp(),
            d["artist"],
            d["title"],
        ),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
