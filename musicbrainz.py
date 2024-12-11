import sqlite3
from collections import Counter
from time import sleep
from typing import NamedTuple

import requests

Record = NamedTuple("Record", (("year", int), ("country", str), ("title", str), ("artist", str)))


def find_releases(title: str, artist: str) -> list[Record]:
    title = title.replace('"', "")
    artist = artist.replace('"', "")
    # Clean title
    # - case 'lorem ipsum (mutam edition)'
    try:
        title = title[: title.index("(")].strip()
    except BaseException:
        pass
    # fetch musicbrainz API
    r = requests.get(
        "https://musicbrainz.org/ws/2/recording/",
        {
            "query": f"title:{title} AND artist:{artist}",
            "fmt": "json",
        },
    )
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
    tree = r.json()
    findings: list[Record] = []
    if not tree["recordings"]:
        return []
    for recording in tree["recordings"]:
        if recording["score"] < 90:
            continue
        if "releases" not in recording:
            recording["releases"] = [recording]
        frdate = recording.get("first-release-date", "0000")[:4]
        for release in recording["releases"]:
            iartist = artist
            try:
                iartist = str(release["artist-credit"][0]["name"])
            except KeyError:
                pass
            findings.append(
                Record(
                    int(release.get("date", "")[:4] or frdate),
                    str(release.get("country", "XW")),
                    str(recording["title"]),
                    iartist,
                )
            )
    if not findings:
        return []
    min_year = min([e.year for e in findings])
    return [r for r in findings if r.year == min_year]


def main() -> None:
    conn = sqlite3.Connection("radio.sqlite3")
    todos = conn.execute("""
SELECT lo.id, lo.artist, lo.title, lo.dtime, lo.radio
    FROM radio_logs lo
    LEFT JOIN radio_songs so
        ON so.id = lo.id
    WHERE so.id is null
    ORDER BY lo.id DESC
    LIMIT 20""").fetchall()
    to_insert = []
    for id, artist, title, dtime, radio in todos:
        releases = find_releases(title, artist)
        if not releases:
            print("Not found:", artist, "-", title)
            continue
        icountry = "XW"
        if len(releases) < 4 and "it" in {r.country.lower() for r in releases}:
            icountry = "IT"
        to_insert.append(
            (
                id,
                radio,
                dtime,
                Counter([r.artist for r in releases]).most_common(1)[0][0],
                Counter([r.title for r in releases]).most_common(1)[0][0],
                releases[0].year,
                icountry,
            )
        )
        sleep(1)
    conn.executemany(
        """
    INSERT INTO radio_songs
        (id, radio, dtime, artist, title, year, country) VALUES
        (?,  ?,     ?,     ?,      ?,     ?,    ?)""",
        to_insert,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
