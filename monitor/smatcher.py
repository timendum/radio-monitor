import sqlite3
from time import sleep
from typing import Any, NamedTuple

from monitor import utils
from monitor.spotify import SpSong, get_token, spotify_find
from monitor.utils import calc_score


class Song(NamedTuple):
    title: str
    s_performers: str
    l_performers: tuple[str] | tuple[()]
    isrc: str | None
    year: int
    country: str
    duration: int

    @classmethod
    def from_spotify(cls, s: SpSong) -> "Song":
        return cls(s.title, s.s_performers, s.l_performers, s.isrc, s.year, s.country, s.duration)


class Candidate(NamedTuple):
    song: tuple[Song, None] | tuple[None, int]
    """ Song or song_id"""
    score: float
    method: str


def quote_phrase(s: str) -> str:
    """Escape for FTS5 MATCH"""
    s = s.strip()
    if not s:
        return ""
    # Escape double quotes for FTS5 phrase literals
    return '"' + s.replace('"', '""') + '"'


def build_match_expr(title: str, performer: str) -> str:
    """
    Build a column-scoped FTS5 MATCH expression.
    """
    parts = []
    t_phrase = quote_phrase(title)
    p_phrase = quote_phrase(performer)

    if t_phrase:
        parts.append(f"title:{t_phrase}")
    if p_phrase:
        parts.append(f"performers:{p_phrase}")

    if not parts:
        raise ValueError("At least one of title or performer must be non-empty.")

    # Combine with AND to require both when present
    return " AND ".join(parts)


def db_find(title: str, performer: str, conn: sqlite3.Connection) -> list[tuple[int, float]]:
    """
    Search FTS5 by title and/or performer.
    Returns canonical display fields with bm25 score:
      (song_id, song_title, song_performers, score)
    """
    match_expr = build_match_expr(title, performer)

    sql = """
    SELECT
        v.song_id,
        s.song_title,
        s.song_performers,
        bm25(song_fts) AS score
    FROM song_fts AS fts
    JOIN song_alias AS v ON v.song_alias_id = fts.rowid
    JOIN song AS s ON s.song_id = v.song_id
    WHERE song_fts MATCH ?
    ORDER BY score ASC
    LIMIT 10
    """

    cur = conn.execute(sql, (match_expr,))
    rows = [(row[0], calc_score(title, performer, row[1], row[2])) for row in cur.fetchall()]
    return sorted(rows, key=lambda r: r[1], reverse=True)[:5]


def find_play_todo(conn: sqlite3.Connection) -> list[Any]:
    return conn.execute("""
SELECT p.play_id, p.title_raw, p.performer_raw
FROM play AS p
LEFT JOIN match_candidate AS mc ON mc.play_id = p.play_id
WHERE mc.play_id IS NULL
ORDER BY p.inserted_at ASC
LIMIT 20""").fetchall()


def save_candidates(candidates: dict[int, list[Candidate]], conn: sqlite3.Connection):
    # SONG
    conn.executemany(
        """
    INSERT OR IGNORE INTO song
        (song_title, song_performers, isrc, year, country, duration) VALUES
        (?,          ?,               ?,    ?,    ?,       ?     )""",
        (
            (
                c.song[0].title,
                c.song[0].s_performers,
                c.song[0].isrc,
                c.song[0].year,
                c.song[0].country,
                c.song[0].duration,
            )
            for cl in candidates.values()
            for c in cl
            if c.song[0] is not None
        ),
    )
    # artist
    conn.executemany(
        """
    INSERT OR IGNORE INTO artist
        (artist_name) VALUES
        (?)""",
        (
            (p,)
            for cl in candidates.values()
            for c in cl
            if c.song[0] is not None
            for p in c.song[0].l_performers
        ),
    )
    # song_artist
    conn.executemany(
        """
    INSERT OR IGNORE INTO song_artist
        (song_id, artist_id) VALUES
        ((SELECT s.song_id FROM song s WHERE song_title = ? AND song_performers = ?),
                  (SELECT artist_id FROM artist WHERE artist_name = ?))""",
        (
            (c.song[0].title, c.song[0].s_performers, p)
            for cl in candidates.values()
            for c in cl
            if c.song[0] is not None
            for p in c.song[0].l_performers
        ),
    )
    # match_candidate
    conn.executemany(
        """
    INSERT INTO match_candidate
        (play_id, song_id, candidate_score, method) VALUES
        (?,       (SELECT s.song_id from song s where song_title = ? AND song_performers = ?),
                           ?,               ?     )""",
        (
            (play_id, c.song[0].title, c.song[0].s_performers, c.score, c.method)
            for play_id, cl in candidates.items()
            for c in cl
            if c.song[0] is not None
        ),
    )


def save_skipped(items: list[tuple[int, str, str]], conn: sqlite3.Connection):
    conn.executemany(
        """
    INSERT INTO play_resolution
    (play_id, song_id, chosen_score, status) VALUES
    (?,       (SELECT s.song_id from song s where song_title = 'TODO' AND song_performers = 'TODO'),
                       ?,               ?     )""",
        ((i[0], 0, "pending") for i in items),
    )


RES_TODO = Candidate((Song("TODO", "TODO", (), None, 0, "", 0), None), 0, "todo")


def find_best_candidate(candidates_list: list[Candidate]) -> tuple[Candidate, str]:
    resolution = None
    status = "pending"
    if candidates_list != sorted(candidates_list, key=lambda c: c.score, reverse=True):
        raise ValueError("Candidates list not sorted")
    if candidates_list[0].score < 0.5:
        # Low confidence, no auto-resolution
        return RES_TODO, "pending"
    # Assert: 0.5 < Best core
    if candidates_list[0].score >= 0.9:
        # High confidence, resolved
        resolution = candidates_list[0]
        status = "auto"
    # Assert: 0.5 < Best core < 0.9
    if not resolution and len(candidates_list) < 2:
        # Good confidence, no other options, resolved
        resolution = candidates_list[0]
        status = "auto"
    # Assert:0.5 < Best core < 0.9 ; more than 1 candidate
    if not resolution and (candidates_list[0].score - candidates_list[1].score) > 0.2:
        # Good confidence, clear margin over next option, resolved
        resolution = candidates_list[0]
        status = "auto"
    if not resolution:
        resolution = candidates_list[0]
        status = "pending"
    return resolution if resolution else RES_TODO, status


def save_resolution(candidates: dict[int, list[Candidate]], conn: sqlite3.Connection):
    for play_id, candidates_list in candidates.items():
        if not candidates_list:
            continue
        resolution, status = find_best_candidate(candidates_list)
        # Save to DB
        song_id = None
        if resolution.song[1] is not None:
            song_id = resolution.song[1]
        else:
            # Look up song_id
            cur = conn.execute(
                """
            SELECT song_id FROM song
            WHERE song_title = ? AND song_performers = ?""",
                (resolution.song[0].title, resolution.song[0].s_performers),
            )
            row = cur.fetchone()
            if row:
                song_id = row[0]
        if not song_id:
            raise ValueError("Song resolved but not found in DB")
        conn.execute(
            """INSERT INTO play_resolution
            (play_id, song_id, chosen_score, status) VALUES
            (?,       ?,       ?,            ?     )""",
            (play_id, song_id, resolution.score, status),
        )


def main() -> None:
    conn = utils.conn_db()
    candidates: dict[int, list[Candidate]] = {}
    to_skip: list[tuple[int, str, str]] = []
    todos = find_play_todo(conn)
    for play_id, title, performer in todos:
        # DB first
        song_match = db_find(title, performer, conn)
        if song_match:
            candidates[play_id] = [Candidate((None, s[0]), s[1], "db") for s in song_match]
        if play_id not in candidates:
            releases = spotify_find(title, performer, get_token())
            if releases:
                candidates[play_id] = [
                    Candidate((Song.from_spotify(ss), None), ss.score, "spotify") for ss in releases
                ]
        if play_id not in candidates:
            to_skip.append((play_id, performer, title))
        sleep(1)
        if not song_match:
            continue
    save_candidates(candidates, conn)
    conn.commit()
    save_resolution(candidates, conn)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
