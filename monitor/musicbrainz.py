import httpx

from monitor.spotify import SpSong
from monitor.utils import calc_score, print_ascii_table


def find_releases(title: str, artist: str) -> list[SpSong]:
    # fetch musicbrainz API
    r = httpx.get(
        "https://musicbrainz.org/ws/2/recording/",
        params={
            "query": f"title:{title} AND artist:{artist}",
            "inc": "isrcs+media+artist-credits",
            "fmt": "json",
        },
    )
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(e)
        return []
    tree = r.json()
    findings: list[SpSong] = []
    if not tree["recordings"]:
        return []
    for recording in tree["recordings"]:
        if "releases" not in recording:
            continue
        isrc = recording.get("isrcs", [""])[0] or None
        iartist = ", ".join(a["name"] for a in recording["artist-credit"])
        for release in recording["releases"]:
            country = str(release.get("country", "XW"))
            try:
                if isrc:
                    country = isrc[:2]
            except BaseException:
                pass
            findings.append(
                SpSong(
                    year=int(release.get("date", "0000")[:4]),
                    country=country,
                    title=str(recording["title"]),
                    s_performers=iartist,
                    l_performers=tuple(a["name"] for a in recording["artist-credit"]),
                    score=calc_score(title, artist, recording["title"], iartist),
                    isrc=isrc,
                    duration=recording.get("length", 0) // 1000,
                )
            )
    if not findings:
        return []
    # findings = [r for r in findings if r.year == min_year]
    findings = sorted(findings, key=lambda r: r.year / r.score)
    return findings[:5]


def main():
    while True:
        title = input("Title (or q): ").strip()
        if not title:
            continue
        if title.lower() == "q":
            break
        artist = input("Artist: ").strip()
        if not artist:
            continue
        rr = find_releases(title, artist)
        if not rr:
            print(" -> Not found")
            continue
        print(" -> Found")
        print_ascii_table([[r.title, r.s_performers, r.year, r.country, r.score] for r in rr])


if __name__ == "__main__":
    main()
