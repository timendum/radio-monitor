from typing import TYPE_CHECKING, NamedTuple

from monitor import smatcher, utils
from monitor.musicbrainz import find_releases as mb_find_releases
from monitor.smatcher import CandidateByID, CandidateBySong, CandidateList, Song, db_find
from monitor.utils import print_ascii_table

if TYPE_CHECKING:
    from onlymaps import Database


def find_play_tocheck(last_id: int, conn: "Database") -> tuple[int, int] | None:
    return conn.fetch_one_or_none(
        tuple[int, int],
        """
SELECT play_id, song_id
FROM play_resolution
WHERE status = 'pending'
AND play_id > ?
ORDER BY play_id ASC
LIMIT 1""",
        last_id,
    )


def find_play(play_id: int, conn: "Database") -> tuple[str, str]:
    return conn.fetch_one(
        tuple[str, str],
        """
SELECT title_raw, performer_raw
FROM play
WHERE play_id = ?
""",
        play_id,
    )


class __FullCandidate(NamedTuple):
    title: str
    performers: str
    isrc: str | None
    year: int | None
    country: str | None
    duration: float | None
    song_id: int
    nuses: int


def _print_cl(title: str, performer: str, cl: list[__FullCandidate]) -> None:
    print_ascii_table(
        [
            ["v", title, performer, "year", "country", "#uses"],
        ]
        + [
            [
                str(row[6]) + ("!" if i == 0 else ""),
                row.title,
                row.performers,
                row.year or "",
                row.country or "",
                str(row.nuses),
            ]
            for i, row in enumerate(cl)
        ],
        head=0,
    )


def find_match_candidates(play_id: int, conn: "Database") -> list[__FullCandidate]:
    return conn.fetch_many(
        __FullCandidate,
        """
SELECT
    s.song_title,
    s.song_performers,
    s.isrc,
    s.year,
    s.country,
    s.duration,
    mc.song_id,
    (
        SELECT COUNT(play_id)
        FROM play_resolution AS pr
        WHERE pr.song_id = mc.song_id AND status != 'pending'
    )
FROM match_candidate AS mc
JOIN song AS s ON s.song_id = mc.song_id
WHERE mc.play_id = ?
ORDER BY mc.candidate_score DESC
""",
        play_id,
    )


def count_todo(last_id: int, conn: "Database") -> int:
    return conn.fetch_one(
        int,
        """
            SELECT COUNT(play_id)
            FROM play_resolution
                WHERE status = 'pending'
                AND play_id > ?""",
        last_id,
    )


def solve_similar_candidates(
    play_id: int, title: str, performer: str, rows: list[__FullCandidate]
) -> __FullCandidate | None:
    clear_title = utils.clear_title(title)
    clear_performer = utils.clear_artist(performer)
    similar_oldest: tuple[None | int, int] = (None, -1)
    clean_oldest: tuple[None | int, int] = (None, -1)
    titles = set[str]()
    performers = set[str]()
    for row in rows:
        row_title = utils.clear_title(row.title)
        row_performers = utils.clear_artist(row.performers)
        titles.add(row_title)
        performers.add(row_performers)
        if row.year and (similar_oldest[0] is None or row.year < similar_oldest[0]):
            similar_oldest = (row.year, row.song_id)
        if utils.calc_score(clear_title, clear_performer, row_title, row_performers) == 1:
            if row.year and (clean_oldest[0] is None or row.year < clean_oldest[0]):
                clean_oldest = (row.year, row.song_id)
            if not row.year and clean_oldest[0] is None and clean_oldest[1] == -1:
                clean_oldest = (row.year, row.song_id)
    if len(titles) == 1 and len(performers) == 1 and similar_oldest[0] is not None:
        if utils.calc_score(clear_title, clear_performer, titles.pop(), performers.pop()) > 0.8:
            return next((row for row in rows if row.song_id == similar_oldest[1]), None)
    return next((row for row in rows if row.song_id == clean_oldest[1]), None)


def input_from_user(full=True) -> Song | None:
    title = input("Title (manual): ").strip()
    if not title:
        return None
    artist = input("Artist (manual): ").strip()
    if not artist:
        return None
    if not full:
        return Song(title, artist, tuple(a.strip() for a in artist.split(",")), None, 0, "", 0)
    year = -1
    while year == -1:
        tyear = input("Year (manual): ").strip()
        if not tyear:
            return None
        try:
            year = int(tyear)
        except ValueError:
            continue
    country = input("Country (manual): ").strip().upper()
    if not country:
        return None
    return Song(
        title, artist, tuple(a.strip() for a in artist.split(",")), None, year, country, None
    )


def save_alias_solution(s: Song | int, play_id: int, conn: "Database", method="human") -> None:
    if isinstance(s, int):
        c = CandidateByID(s, 1, method)
        cl: list[CandidateByID] = [c]
    else:
        c = CandidateBySong(s, 1, method)
        cl: list[CandidateBySong] = [c]
    candidates: dict[int, CandidateList] = {}
    candidates[play_id] = cl
    smatcher.save_candidates(candidates, conn)
    smatcher.save_resolution(candidates, conn, method)
    if isinstance(s, int):
        conn.exec(
            """
            INSERT INTO song_alias
            (song_id, kind,  title, performers, source) VALUES
            (?,       'alias',
                            (SELECT pt.title_raw FROM play pt WHERE pt.play_id = ?),
                                    (SELECT pp.performer_raw FROM play pp WHERE pp.play_id = ?),
                                                'manual')""",
            s,
            play_id,
            play_id,
        )
    else:
        conn.exec(
            """
            INSERT INTO song_alias
            (song_id, kind,  title, performers, source) VALUES
            ((SELECT s.song_id FROM song s WHERE song_key = ?),
                    'alias',
                            (SELECT pt.title_raw FROM play pt WHERE pt.play_id = ?),
                                    (SELECT pp.performer_raw FROM play pp WHERE pp.play_id = ?),
                                                'manual')""",
            s.unique_key(),
            play_id,
            play_id,
        )


def ask_user(play_id: int, conn: "Database") -> bool:
    r = input_from_user(True)
    if not r:
        return False
    save_alias_solution(r, play_id, conn)
    return True


def query_spotify(play_id: int, token: str, conn: "Database") -> bool:
    r = input_from_user(False)
    if not r:
        return False
    releases = smatcher.spotify_find(r.title, r.s_performers, token)
    if releases:
        print_ascii_table(
            [
                ["v", "title", "artist", "year", "country"],
            ]
            + [
                [
                    str(i) + ("!" if i == 0 else ""),
                    r.title,
                    r.s_performers,
                    r.year or "",
                    r.country or "",
                ]
                for i, r in enumerate(releases)
            ],
            head=0,
        )
        decision = input("Action (id to save, skip): ").strip()
        if decision == "!" or decision == ".":
            decision = "0"
        try:
            releases_id = int(decision)
            if releases_id < len(releases):
                save_alias_solution(Song.from_spotify(releases[releases_id]), play_id, conn)
                print(f" -> Saved {releases_id} for play {play_id}")
                return True
        except ValueError:
            print(" -> Skipped")
    else:
        print(" -> No results found")
    return False


def edit_song(conn: "Database", default_song_id: int) -> None:
    decision = input("Edit SONG - enter song id: ").strip().lower()
    try:
        song_id = int(decision)
    except ValueError:
        if decision == "!" or decision == ".":
            song_id = default_song_id
        else:
            print("Edit terminated")
            return
    row = conn.fetch_one_or_none(
        tuple[str, str, str | int, str, str, str | float],
        """
    SELECT
        song_title,
        song_performers,
        COALESCE(year, "")     AS year,
        COALESCE(country, "")  AS country,
        COALESCE(isrc, "")     AS isrc,
        COALESCE(duration, "") AS duration
    FROM song
    WHERE
        song_id = ?
    """,
        song_id,
    )
    if not row:
        print("Edit terminated - song not found")
        return
    print_ascii_table(
        [
            ["id", str(song_id)],
            ["title", row[0]],
            ["performers", row[1]],
            ["year", str(row[2])],
            ["country", row[3]],
            ["isrc", str(row[4])],
            ["duration (s)", row[5]],
        ]
    )
    decision = input("Edit SONG - Year: ").strip().lower()
    year = None
    try:
        year = int(decision)
    except ValueError:
        pass
    decision = input("Edit SONG - Country: ").strip().lower()
    country = None
    try:
        country = decision.upper() if len(decision) == 2 else None
    except ValueError:
        pass
    if year or country:
        conn.exec(
            """
        UPDATE song
        SET
            year = COALESCE(?, year),
            country = COALESCE(?, country)
        WHERE song_id = ?
        """,
            year,
            country,
            song_id,
        )
    else:
        print("Edit terminated - no data")
    return


def join_songs(conn: "Database") -> None:
    tinput = input("Join songs - enter OLD id: ").strip().lower()
    try:
        old_song = int(tinput)
    except ValueError:
        print("Edit terminated")
        return
    tinput = input("Join songs - enter NEW id: ").strip().lower()
    try:
        new_song = int(tinput)
    except ValueError:
        print("Edit terminated")
        return
    conn.exec(
        """
    UPDATE play_resolution
    SET
        song_id = ?
    WHERE
        song_id = ?
""",
        new_song,
        old_song,
    )
    conn.exec(
        """
    UPDATE song_alias
    SET
        song_id = ?
    WHERE
        song_id = ? AND
        source = 'manual'
""",
        new_song,
        old_song,
    )
    print(f"Done, changed {old_song} to {new_song}")
    return


def main() -> None:
    with utils.conn_db() as conn:
        last_id = -1
        token = smatcher.get_token()
        while True:
            to_check = find_play_tocheck(last_id, conn)
            if not to_check:
                break
            play_id, _ = to_check
            last_id = play_id
            candidates: dict[int, CandidateList] = {}
            # check again on DB, maybe something new is there
            title, performer = find_play(play_id, conn)
            if not title or not performer:
                # Missing data, ignore
                candidates[play_id] = [smatcher.CAND_IGNORED]
                smatcher.save_candidates(candidates, conn)
                smatcher.save_resolution(candidates, conn, "human")
                continue
            song_match = db_find(title, performer, conn)
            if song_match:
                # Found in DB!
                cl: list[CandidateByID] = [CandidateByID(s[0], s[1], "db") for s in song_match]
                candidates[play_id] = cl
                smatcher.save_candidates(candidates, conn)
                res = smatcher.save_resolution(candidates, conn)
                if res[play_id]:
                    # go back and should be solved
                    last_id -= 1
                    continue
            ncount = count_todo(last_id, conn)
            print(f"ID: {play_id} (todo: {ncount})")
            songs = find_match_candidates(play_id, conn)
            best = solve_similar_candidates(
                play_id, title, performer, songs
            ) or solve_similar_candidates(play_id, title, performer, songs)
            if best:
                songs = [best] + [s for s in songs if s.song_id != best.song_id]
            _print_cl(title, performer, songs)
            mc_song_ids = [s.song_id for s in songs]
            decision = (
                input("Quit, Best, id to save, Retry, Spotify, iGnore, Insert, Mbrainz, skip: ")
                .strip()
                .lower()
            )
            try:
                song_id = int(decision)
                if song_id in mc_song_ids:
                    save_alias_solution(song_id, play_id, conn)
                    print(f" -> Saved {song_id} for play {play_id}")
                    continue
            except ValueError:
                pass
            match decision:
                case "":
                    if best:
                        song_id = mc_song_ids[0]
                        save_alias_solution(song_id, play_id, conn)
                        print(f" -> Saved {song_id} for play {play_id}")
                    continue
                case "e" | "edit":
                    # Edit song entry
                    edit_song(conn, mc_song_ids[0])
                    last_id -= 1
                    continue
                case "q" | "quit":
                    # Halt script
                    break
                case "b" | "!" | "best" | ".":
                    # Save best candidate
                    song_id = mc_song_ids[0]
                    save_alias_solution(song_id, play_id, conn)
                    print(f" -> Saved {song_id} for play {play_id}")
                    continue
                case "r" | "retry":
                    # Retry spotify search
                    releases = smatcher.spotify_find(title, performer, token)
                    if releases:
                        candidates[play_id] = [
                            CandidateBySong(Song.from_spotify(ss), ss.score, "mspotify")
                            for ss in releases
                        ]
                        smatcher.save_candidates(candidates, conn)
                        smatcher.save_resolution(candidates, conn)
                        print(" -> New results found")
                    else:
                        print(" -> No spotify results")
                    last_id -= 1
                    continue
                case "m" | "mb" | "mbrainz" | "musicbrainz":
                    # Try MusicBrainz search
                    releases = mb_find_releases(
                        utils.clear_title(title), utils.clear_artist(performer)
                    )
                    if releases:
                        candidates[play_id] = [
                            CandidateBySong(Song.from_spotify(ss), ss.score, "mbrainz")
                            for ss in releases
                        ]
                        smatcher.save_candidates(candidates, conn)
                        smatcher.save_resolution(candidates, conn)
                        print(" -> New results found")
                    else:
                        print(" -> No musicbrainz results")
                    last_id -= 1
                    continue
                case "s" | "spotify":
                    # Query Spotify with manual input for title+performer
                    _ = query_spotify(play_id, token, conn)
                    last_id -= 1
                    continue
                case "e" | "i" | "entry" | "insert":
                    # Manual insert song
                    ask_user(play_id, conn)
                    continue
                case "g" | "ignore":
                    # I*g*nore
                    candidates[play_id] = [smatcher.CAND_IGNORED]
                    smatcher.save_candidates(candidates, conn)
                    smatcher.save_resolution(candidates, conn, "human")
                    print(" -> Ignored!")
                    continue
                case "j" | "join":
                    join_songs(conn)
                    continue
                case _:
                    # Other, skip
                    print(" -> Skipped!")
                    continue
            break


if __name__ == "__main__":
    main()
