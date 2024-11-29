from datetime import datetime
import sqlite3

import requests


def main() -> None:
    r = requests.get("https://www.deejay.it/api/broadcast_airplay/?get=now")
    r.raise_for_status()
    d = r.json()["result"]
    conn = sqlite3.Connection("radio.sqlite3")
    conn.execute(
        "INSERT OR IGNORE INTO radio_logs (radio, dtime, artist, title) VALUES (?,?,?,?)",
        (
            "deejay",
            datetime.fromisoformat(d["datePlay"]).timestamp(),
            d["artist"],
            d["title"],
        ),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
