import base64
import os
import sqlite3
from difflib import SequenceMatcher
from time import sleep
from typing import NamedTuple

import requests

SPOTIFY_AUTH = os.environ["SPOTIFY_AUTH"]


class Record(NamedTuple):
    year: int
    country: str
    title: str
    artist: str
    score: float


def get_token() -> str:
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": "Basic " + base64.b64encode(SPOTIFY_AUTH.encode()).decode("ascii")
        },
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    jr = r.json()
    return jr["access_token"]


def calc_score(otitle: str, oartist: str, title: str, artist: str) -> float:
    otitle, oartist, title, artist = otitle.lower(), oartist.lower(), title.lower(), artist.lower()
    try:
        title = title[: title.index("(")].strip()
    except BaseException:
        pass
    rtitle = SequenceMatcher(None, title, otitle).ratio()
    rartist = SequenceMatcher(None, artist, oartist).ratio()
    return (rtitle + rartist) / 2


def find_releases(title: str, artist: str, token: str) -> Record | None:
    title = title.replace('"', "")
    artist = artist.replace('"', "")
    # get only the first artist in a list
    if "," in artist:
        artist = artist[: artist.index(",")]
    if " ft" in artist:
        artist = artist[: artist.index(" ft")]

    # Clean title
    # - case 'lorem ipsum (mutam edition)'
    try:
        title = title[: title.index("(")].strip()
    except BaseException:
        pass
    # fetch spotify API
    r = requests.get(
        "https://api.spotify.com/v1/search",
        {
            "q": f"{title} artist:{artist}",
            "type": "track",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        return None
    tree = r.json()
    findings: list[Record] = []
    best_skipped: None | Record = None
    for item in tree["tracks"]["items"]:
        country = "XX"
        try:
            country = item["external_ids"]["isrc"][:2]
        except BaseException:
            pass
        r = Record(
            year=int(item["album"]["release_date"][:4]),
            country=country,
            title=item["name"],
            artist=", ".join(a["name"] for a in item["artists"]),
            score=max(
                [calc_score(title, artist, item["name"], a["name"]) for a in item["artists"]]
            ),
        )
        if r.score < 0.5:
            if not best_skipped or best_skipped.score < r.score:
                best_skipped = r
            continue

        findings.append(r)
    if len(findings) > 1:
        return sorted(findings, key=lambda r: r.year / r.score)[0]
    if not findings:
        if best_skipped:
            r = best_skipped
            print(f"Skipped: {title} - {artist} = {r.title} - {r.artist}")
        return None
    return findings[0]


def main() -> None:
    token = get_token()
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
        release = find_releases(title, artist, token)
        if not release:
            print(f"Not found ({id}): {artist} - {title}")
            continue
        if release.score < 0.8:
            print(
                f"OK ({id}) {release.score}: {title} - {artist} ="
                + " {release.title} - {release.artist} - {release.year} - {release.country}"
            )
        to_insert.append(
            (
                id,
                radio,
                dtime,
                release.artist,
                release.title,
                release.year,
                release.country,
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
