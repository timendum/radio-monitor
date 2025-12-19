import base64
import os
from functools import cache
from typing import NamedTuple

import httpx

from monitor.utils import calc_score, clear_artist, clear_title, print_ascii_table

SPOTIFY_AUTH = os.environ["SPOTIFY_AUTH"]


class SpSong(NamedTuple):
    title: str
    s_performers: str
    l_performers: tuple[str]
    isrc: str | None
    year: int
    country: str
    score: float
    duration: int  # in seconds


@cache
def get_token() -> str:
    r = httpx.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": "Basic " + base64.b64encode(SPOTIFY_AUTH.encode()).decode("ascii")
        },
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    jr = r.json()
    return jr["access_token"]


def find_releases(title: str, artist: str, token: str) -> list[SpSong]:
    # fetch spotify API
    r = httpx.get(
        "https://api.spotify.com/v1/search",
        params={
            "q": f"{clear_title(title)} artist:{clear_artist(artist)}",
            "type": "track",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(e)
        return []
    tree = r.json()
    findings: list[SpSong] = []
    for item in tree["tracks"]["items"]:
        country = "XX"
        try:
            country = item["external_ids"]["isrc"][:2]
        except BaseException:
            pass
        title = item["name"]
        # for suff in ("(with ", "(feat"):
        #     if suff in title and title.find(suff) > 2:
        #         title = title[: title.find(suff)].strip()
        r = SpSong(
            year=int(item["album"]["release_date"][:4]),
            country=country,
            title=title,
            s_performers=", ".join(a["name"] for a in item["artists"]),
            l_performers=tuple(a["name"] for a in item["artists"]),
            score=max(
                [calc_score(title, artist, item["name"], a["name"]) for a in item["artists"]]
            ),
            isrc=item["external_ids"]["isrc"],
            duration=int(item["duration_ms"] / 1000),
        )
        findings.append(r)
    if findings:
        return sorted(findings, key=lambda r: r.year / r.score)[:5]
    return []


def spotify_find(title: str, artist: str, token: str) -> list[SpSong]:
    release = find_releases(title, artist, token)
    if not release:
        if " X " in artist:
            release = find_releases(title, artist.split(" X ")[0], token)
            if release:
                return release
        return []
    return release


def main():
    token = get_token()
    while True:
        title = input("Title (or q): ").strip()
        if not title:
            continue
        if title.lower() == "q":
            break
        artist = input("Artist: ").strip()
        if not artist:
            continue
        rr = find_releases(title, artist, token)
        if not rr:
            print(" -> Not found")
            continue
        print(" -> Found")
        r = rr[0]
        print_ascii_table([[r.title, r.s_performers, r.year, r.country]])


if __name__ == "__main__":
    main()
