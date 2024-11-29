from datetime import date
import sqlite3

from bs4 import BeautifulSoup
import requests


def main() -> None:
    r = requests.get("https://radioairplay.fm/")
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows: list[tuple[str, str, str, str, str]] = []
    day = date.today().isoformat()
    for box in soup.find_all(class_="date-box"):
        author = box.find(class_="head-two").get_text().strip()
        title = box.find(class_="head-one").get_text().strip()
        radio = box.find("img")["title"].strip()
        time = box.find(class_="dj-time").get_text().strip()
        rows.append((radio, day, time, author, title))
    conn = sqlite3.Connection("radio.sqlite3")
    conn.executemany(
        "INSERT OR IGNORE INTO radioairplay_logs (radio, day, time, artist, title) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()


if __name__ == "__main__":
    main()
