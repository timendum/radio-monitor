import base64
import os
import sqlite3
from difflib import SequenceMatcher
from functools import cache
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


@cache
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
    oartist, artist = clear_artist(oartist), clear_artist(artist)
    otitle, title = clear_title(otitle), clear_title(title)
    try:
        title = title[: title.index("(")].strip()
    except BaseException:
        pass
    rtitle = SequenceMatcher(None, title, otitle).ratio()
    rartist = SequenceMatcher(None, artist, oartist).ratio()
    return (rtitle + rartist) / 2


def clear_artist(artist: str) -> str:
    # get only the first artist in a list
    artist = artist.lower()
    for sep in (",", "&", " ft", " feat", " e ", " and "):
        if sep in artist:
            artist = artist[: artist.index(sep)].strip()
    return artist


def clear_title(title: str) -> str:
    # get only the first artist in a list
    for sep in ("(", " - "):
        if sep in title and title.index(sep) > 2:
            title = title[: title.index(sep)].strip()
    return title


def find_releases(title: str, artist: str, token: str) -> Record | None:
    title = clear_title(title)
    artist = clear_artist(artist)

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
        title = item["name"]
        for suff in ("(with ", "(feat"):
            if suff in title and title.find(suff) > 2:
                title = title[: title.find(suff)].strip()
        r = Record(
            year=int(item["album"]["release_date"][:4]),
            country=country,
            title=title,
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
            # print(f"Skipped: {title} - {artist} = {r.title} - {r.artist}")
        return None
    return findings[0]


def spotify_find(title: str, artist: str, token: str) -> Record | None:
    release = find_releases(title, artist, token)
    if not release:
        if " X " in artist:
            release = find_releases(title, artist[: artist.index(" X ")], token)
            if release:
                return release
        return None
    return release


def db_find(title: str, artist: str, conn: sqlite3.Connection) -> Record | None:
    drelease = conn.execute(
        """
SELECT okyear, okcountry, oktitle, okartist, 1
    FROM song_matches
    WHERE title = ?
        AND artist = ?""",
        (title, artist),
    ).fetchone()
    if drelease:
        return Record(*drelease)
    return None


def main() -> None:
    token = get_token()
    conn = sqlite3.Connection("radio.sqlite3")
    todos = conn.execute("""
        SELECT lo.id, lo.artist, lo.title, lo.dtime, lo.radio
        FROM radio_logs lo
        LEFT JOIN radio_songs so
            ON so.id = lo.id
        LEFT JOIN song_skipped ss
            ON ss.title = lo.title
            AND ss.artist = lo.artist
        WHERE so.id is null
            AND ss.id is null
        ORDER BY lo.id DESC
        LIMIT 20""").fetchall()
    to_insert = []
    to_matches = []
    to_skip = []
    to_check = []
    for id, artist, title, dtime, radio in todos:
        release = db_find(title, artist, conn)
        if not release:
            release = spotify_find(title, artist, token)
            if release and release.score >= 1:
                to_matches.append(
                    (
                        artist,
                        title,
                        release.artist,
                        release.title,
                        release.year,
                        release.country,
                    )
                )
            elif release and release.score < 0.8:
                to_matches.append(
                    (
                        artist,
                        title,
                        release.artist,
                        release.title,
                        release.year,
                        release.country,
                    )
                )
                to_check.append((id,))
            else:
                # print(f"Not found ({id}): {artist} - {title}")
                to_skip.append((artist, title))
        if not release:
            continue
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
    conn.executemany(
        """
    INSERT OR IGNORE INTO song_matches
        (artist, title, okartist, oktitle, okyear, okcountry) VALUES
        (?,      ?,     ?,        ?,       ?,      ?)""",
        to_matches,
    )
    conn.executemany(
        """
    INSERT OR IGNORE INTO song_skipped
        (artist, title) VALUES
        (?,      ?)""",
        to_skip,
    )
    conn.executemany(
        """
    INSERT OR IGNORE INTO song_check
        (id) VALUES (?)""",
        to_check,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
