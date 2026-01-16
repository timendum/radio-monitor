import sqlite3

from monitor import smatcher, utils
from monitor.smatcher import Candidate, Song, db_find
from monitor.utils import print_ascii_table


def find_play_tocheck(last_id: int, conn: sqlite3.Connection) -> tuple[int, int]:
    return conn.execute(
        """
SELECT play_id, song_id
FROM play_resolution
WHERE status = 'pending'
AND play_id > ?
ORDER BY play_id ASC
LIMIT 1""",
        (last_id,),
    ).fetchone()


def find_play(play_id: int, conn: sqlite3.Connection) -> tuple[str, str]:
    return conn.execute(
        """
SELECT title_raw, performer_raw
FROM play
WHERE play_id = ?
""",
        (play_id,),
    ).fetchone()


def print_match_candidates(
    play_id: int, title: str, performer: str, conn: sqlite3.Connection
) -> list[int]:
    rows = conn.execute(
        """
SELECT s.song_title, s.song_performers, s.year, s.country, mc.song_id
FROM match_candidate as mc
LEFT JOIN song as s ON s.song_id = mc.song_id
WHERE play_id = ?
ORDER BY mc.candidate_score DESC
""",
        (play_id,),
    ).fetchall()

    print_ascii_table(
        [
            ["v", "title", "artist", "year", "country"],
            ["", title, performer, "", ""],
        ]
        + [
            [
                str(row[4]) + ("!" if i == 0 else ""),
                row[0],
                row[1],
                row[2],
                row[3],
            ]
            for i, row in enumerate(rows)
        ]
    )
    return [row[4] for row in rows]


def count_todo(last_id: int, conn: sqlite3.Connection) -> int:
    return conn.execute(
        """
            SELECT COUNT(play_id)
            FROM play_resolution
                WHERE status = 'pending'
                AND play_id > ?""",
        (last_id,),
    ).fetchone()[0]


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
    return Song(title, artist, tuple(a.strip() for a in artist.split(",")), None, year, country, 0)


def save_human_alias(r: Song, play_id: int, conn: sqlite3.Connection) -> None:
    c = Candidate((r, None), 1, "human")
    candidates: dict[int, list[Candidate]] = {}
    candidates[play_id] = [c]
    smatcher.save_candidates(candidates, conn)
    smatcher.save_resolution(candidates, conn)
    conn.execute(
        """
        INSERT INTO song_alias
        (song_id, kind,  title, performers, source) VALUES
        ((SELECT s.song_id FROM song s WHERE song_title = ? AND song_performers = ?),
                 'alias',
                        (SELECT pt.title_raw FROM play pt WHERE pt.play_id = ?),
                                (SELECT pp.performer_raw FROM play pp WHERE pp.play_id = ?),
                                            'manual')""",
        (r.title, r.s_performers, play_id, play_id),
    )
    conn.commit()


def ask_user(play_id: int, conn: sqlite3.Connection) -> bool:
    r = input_from_user(True)
    if not r:
        return False
    save_human_alias(r, play_id, conn)
    return True


def query_spotify(play_id: int, token: str, conn: sqlite3.Connection) -> bool:
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
                    str(i),
                    r.title,
                    r.s_performers,
                    r.year,
                    r.country,
                ]
                for i, r in enumerate(releases)
            ]
        )
        decision = input("Action (id to save, skip): ").strip()
        try:
            releases_id = int(decision)
            if releases_id < len(releases):
                save_human_alias(Song.from_spotify(releases[releases_id]), play_id, conn)
                print(f" -> Saved {releases_id} for play {play_id}")
                return True
        except ValueError:
            pass
    return True


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
            candidates: dict[int, list[Candidate]] = {}
            # check again on DB, maybe something new is there
            title, performer = find_play(play_id, conn)
            song_match = db_find(title, performer, conn)
            if song_match:
                # Found in DB!
                candidates[play_id] = [Candidate((None, s[0]), s[1], "db") for s in song_match]
                smatcher.save_candidates(candidates, conn)
                smatcher.save_resolution(candidates, conn)
                conn.commit()
                last_id -= 1
                # go back and check if fixed
                continue
            ncount = count_todo(last_id, conn)
            print(f"ID: {play_id} (todo: {ncount})")
            mc_song_ids = print_match_candidates(play_id, title, performer, conn)
            decision = (
                input(
                    "Action (Quit, Best, id to save, Retry, Spotify, iGnore, Insert Manualy, skip): "
                )
                .strip()
                .lower()
            )
            try:
                song_id = int(decision)
                if song_id in mc_song_ids:
                    smatcher.save_resolution(
                        {play_id: [Candidate((None, song_id), 1, "human")]}, conn
                    )
                    conn.commit()
                    print(f" -> Saved {song_id} for play {play_id}")
                    continue
            except ValueError:
                pass
            match decision:
                case "q":
                    break
                case "r":
                    releases = smatcher.spotify_find(title, performer, token)
                    if releases:
                        candidates[play_id] = [
                            Candidate((Song.from_spotify(ss), None), ss.score, "spotify")
                            for ss in releases
                        ]
                        smatcher.save_candidates(candidates, conn)
                        smatcher.save_resolution(candidates, conn)
                        conn.commit()
                        last_id -= 1
                        continue
                    print(" -> No spotify results")
                    continue
                case "s":
                    r = query_spotify(play_id, token, conn)
                    if not r:
                        last_id -= 1
                    continue
                case "e":
                    ask_user(play_id, conn)
                    continue
                case "i":
                    ask_user(play_id, conn)
                    continue
                case "g":
                    candidates[play_id] = [smatcher.CAND_IGNORED]
                    smatcher.save_candidates(candidates, conn)
                    smatcher.save_resolution(candidates, conn)
                    conn.commit()
                    print(" -> Ignored!")
                    continue
                case _:
                    print(" -> Skipped!")
                    continue
            break


if __name__ == "__main__":
    main()
