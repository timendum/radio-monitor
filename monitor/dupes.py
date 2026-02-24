from collections.abc import Iterable
from typing import TYPE_CHECKING, NamedTuple

from monitor import utils
from monitor.utils import print_ascii_table
from monitor.check_song import edit_song

if TYPE_CHECKING:
    from onlymaps import Database

import logging

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)


class __FullSong(NamedTuple):
    song_id: int
    title: str
    performers: str
    year: int | None
    country: str | None
    master_song_id: int
    uses: int


def find_song_tocheck(last_song_id: int, conn: "Database") -> "__FullSong | None":
    return conn.fetch_one_or_none(
        __FullSong,
        """
SELECT
    song.song_id,
    song.song_title,
    song.song_performers,
    song.year,
    song.country,
    COALESCE((SELECT MAX(song_id_b) FROM song_work_review WHERE song_id_a = song.song_id), 0),
    song.resolution_count
FROM v_master_song AS song
WHERE song.song_id > ?
ORDER BY song.song_id ASC
LIMIT 1""",
        last_song_id,
    )


class __SongCandidate(NamedTuple):
    song_id: int
    title: str
    performers: str
    year: int | None
    country: str | None
    uses: int


def find_song_dupes(song_id: int, min_match_id: int, conn: "Database") -> list[__SongCandidate]:
    return conn.fetch_many(
        __SongCandidate,
        """
SELECT
    song.song_id,
    song.song_title,
    song.song_performers,
    song.year,
    song.country,
    song.resolution_count
FROM v_master_song AS song
WHERE song.song_id > ?
ORDER BY song.song_id ASC""",
        max(min_match_id, song_id),
    )


def save_work_review(song_id: int, other_ids: Iterable[int], same: bool, conn: "Database") -> None:
    with conn.transaction():
        for other_id in other_ids:
            conn.exec(
                """INSERT INTO song_work_review (song_id_a, song_id_b, same_work)
        VALUES (?, ?, ?)""",
                min(song_id, other_id),
                max(song_id, other_id),
                1 if same else 0,
            )
            if same:
                conn.exec(
                    """INSERT INTO song_work (master_song_id, song_id)
            VALUES (?, ?)""",
                    song_id,
                    other_id,
                )


def join_songs(song_ids: set[int], conn: "Database") -> bool:
    tinput = input("Join songs - enter MASTER id: ").strip().lower()
    try:
        master_song = int(tinput)
    except ValueError:
        print("Edit terminated")
        return False
    slave_songs = []
    while True:
        tinput = input("Join songs - enter CHILD id: ").strip().lower()
        if not tinput or "q" == tinput:
            break
        try:
            slave_songs.append(int(tinput))
        except ValueError:
            print("ERROR - invalid id, try again")
            continue
    if not slave_songs:
        print("No child songs, join terminated")
        return False
    # check for consistency
    if master_song not in song_ids:
        print("Master song not in candidates, join terminated")
        return False
    if set(slave_songs) - song_ids:
        print("Some child songs not in candidates, join terminated", set(slave_songs) - song_ids)
        return False
    save_work_review(master_song, slave_songs, True, conn)
    print(f"Done, {','.join(map(str, slave_songs))} are children of {master_song}")
    return True


def sort_cand(candidates: list[__SongCandidate], song: __FullSong) -> list[__SongCandidate]:
    scandidates: list[tuple[float, __SongCandidate]] = [
        (
            utils.calc_score(
                c.title,
                c.performers,
                song.title,
                song.performers,
            ),
            c,
        )
        for c in candidates
    ]
    scandidates = sorted(scandidates, key=lambda x: x[0], reverse=True)
    return [c for _, c in scandidates]


def main() -> None:
    with utils.conn_db() as conn:
        last_id = -1
        while True:
            song = find_song_tocheck(last_id, conn)
            if not song:
                # no more songs to check
                break
            last_id = song.song_id
            candidates = find_song_dupes(last_id, song.master_song_id, conn)
            if not candidates:
                continue
            max_c_id = max(c.song_id for c in candidates)
            # filter candidates for likeness
            candidates = [
                c
                for c in candidates
                if utils.calc_score(
                    c.title,
                    c.performers,
                    song.title,
                    song.performers,
                )
                > 0.7
            ]
            if not candidates:
                save_work_review(song.song_id, [max_c_id], False, conn)
                print(f"No dupes for {song.song_id} (untill {max_c_id})")
                continue
            candidates = sort_cand(candidates, song)
            print_ascii_table(
                [
                    ["v", "title", "performers", "year", "country", "#uses"],
                    [song.song_id, song.title, song.performers, song.year, song.country, song.uses],
                    *[
                        [c.song_id, c.title, c.performers, c.year, c.country, c.uses]
                        for c in candidates
                    ],
                ],
                {0, 1},
            )
            decision = input("Quit, Join, Different, skip: ").strip().lower()
            match decision:
                case "j" | "join":
                    # Join songs
                    ok = join_songs({c.song_id for c in candidates} | {song.song_id}, conn)
                    if ok:
                        save_work_review(song.song_id, [max_c_id], False, conn)
                    last_id -= 1
                    continue
                case "q" | "quit":
                    # Halt script
                    break
                case "d":
                    # Different songs
                    save_work_review(song.song_id, [c.song_id for c in candidates], False, conn)
                    last_id -= 1
                    continue
                case "e" | "edit":
                    # Edit song entry
                    edit_song(conn, song.song_id)
                    last_id -= 1
                    continue
                case _:
                    # Other, skip
                    print(" -> Skipped!")
                    continue
            break


if __name__ == "__main__":
    main()
