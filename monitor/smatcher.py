import unicodedata
from time import sleep
from typing import TYPE_CHECKING, NamedTuple

from monitor import utils
from monitor.spotify import SpSong, get_token, spotify_find
from monitor.utils import calc_score

if TYPE_CHECKING:
    from onlymaps import Database


class Song(NamedTuple):
    title: str
    s_performers: str
    l_performers: tuple[str, ...] | tuple[()]
    isrc: str | None
    year: int | None
    country: str | None
    duration: int | None

    @classmethod
    def from_spotify(cls, s: SpSong) -> "Song":
        return cls(
            s.title,
            s.s_performers,
            s.l_performers,
            s.isrc,
            s.year if s.year > 1900 else None,
            s.country,
            s.duration,
        )

    def unique_key(self) -> str:
        atitle = unicodedata.normalize("NFKD", self.title).encode("ascii", "ignore")
        aperformers = unicodedata.normalize("NFKD", self.s_performers).encode("ascii", "ignore")
        return (atitle + b"|" + aperformers).decode("ascii").lower()


class CandidateByID(NamedTuple):
    song_id: int
    score: float
    method: str


class CandidateBySong(NamedTuple):
    song: Song
    score: float
    method: str


type CandidateList = list[CandidateByID] | list[CandidateBySong]


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


def db_find(title: str, performer: str, conn: "Database") -> list[tuple[int, float]]:
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
        v.title,
        v.performers,
        bm25(song_fts) AS score
    FROM song_fts AS fts
    JOIN song_alias AS v ON v.song_alias_id = fts.rowid
    JOIN song AS s ON s.song_id = v.song_id
    WHERE song_fts MATCH ?
    ORDER BY score ASC
    LIMIT 10
    """

    rows = [
        (
            row[0],
            1.0
            if calc_score(title, performer, row[3], row[4]) == 1.0  # perfect alias match
            else calc_score(title, performer, row[1], row[2]),
        )
        for row in conn.fetch_many(tuple[int, str, str, str, str, float], sql, match_expr)
    ]
    return sorted(rows, key=lambda r: r[1], reverse=True)[:5]


def find_play_todo(conn: "Database", limit=20) -> list[tuple[int, str, str]]:
    return conn.fetch_many(
        tuple[int, str, str],
        """
SELECT p.play_id, p.title_raw, p.performer_raw
FROM play AS p
LEFT JOIN match_candidate AS mc ON mc.play_id = p.play_id
WHERE mc.play_id IS NULL
ORDER BY p.inserted_at ASC
LIMIT ?""",
        limit,
    )


CAND_TODO = CandidateBySong(Song("TODO", "TODO", (), None, 0, "", 0), 0, "todo")
CAND_IGNORED = CandidateBySong(Song("TODO", "TODO", (), None, 1, "", 0), 1, "todo")


def save_candidates(candidates: dict[int, CandidateList], conn: "Database"):
    with conn.transaction():
        for cl in candidates.values():
            for c in cl:
                if c == CAND_TODO or c == CAND_IGNORED:
                    continue
                if isinstance(c, CandidateBySong):
                    # SONG
                    conn.exec(
                        """
    INSERT INTO song
        (song_title, song_performers, song_key, isrc, year, country, duration) VALUES
        (?,          ?,               ?,        ?,    ?,    ?,       ?     )
        ON CONFLICT DO NOTHING""",
                        c.song.title,
                        c.song.s_performers,
                        c.song.unique_key(),
                        c.song.isrc,
                        c.song.year,
                        c.song.country,
                        c.song.duration,
                    )
        # artist
        for cl in candidates.values():
            for c in cl:
                if c == CAND_TODO or c == CAND_IGNORED:
                    continue
                if isinstance(c, CandidateBySong):
                    for p in c.song.l_performers:
                        conn.exec(
                            """
                        INSERT INTO artist
                            (artist_name) VALUES
                            (?)
                            ON CONFLICT DO NOTHING""",
                            p,
                        )
        # song_artist
        for cl in candidates.values():
            for c in cl:
                if c == CAND_TODO or c == CAND_IGNORED:
                    continue
                if isinstance(c, CandidateBySong):
                    for p in c.song.l_performers:
                        conn.exec(
                            """
                        INSERT INTO song_artist
                            (song_id, artist_id) VALUES
                            ((SELECT s.song_id FROM song s WHERE song_key = ?),
                                    (SELECT artist_id FROM artist WHERE artist_name = ?))
                            ON CONFLICT DO NOTHING""",
                            c.song.unique_key(),
                            p,
                        )
        # never delete old match_candidate entries
        # match_candidate by song title+performers
        for play_id, cl in candidates.items():
            for c in cl:
                if isinstance(c, CandidateBySong):
                    conn.exec(
                        """
                    INSERT INTO match_candidate
                        (play_id, song_id, candidate_score, method) VALUES
                        (?,       (SELECT s.song_id FROM song s WHERE song_key = ?),
                                        ?,               ?     )
                        ON CONFLICT DO NOTHING""",
                        play_id,
                        c.song.unique_key(),
                        c.score,
                        c.method,
                    )
                    # match_candidate by song id
                else:
                    conn.exec(
                        """
                    INSERT INTO match_candidate
                        (play_id, song_id, candidate_score, method) VALUES
                        (?,       ?,       ?,               ?     )
                        ON CONFLICT DO NOTHING""",
                        play_id,
                        c.song_id,
                        c.score,
                        c.method,
                    )


def find_best_candidate(
    candidates_list: CandidateList, reason: str
) -> tuple[CandidateByID | CandidateBySong, str]:
    resolution = None
    status = "pending"
    if not candidates_list:
        return CAND_TODO, "pending"
    if candidates_list != sorted(candidates_list, key=lambda c: c.score, reverse=True):
        raise ValueError("Candidates list not sorted")
    if not candidates_list:
        raise ValueError("No candidates")
    if candidates_list[0].score >= 0.9:
        # High confidence, resolved
        resolution = candidates_list[0]
        status = reason
    # Assert: 0.6 < Best core < 0.9
    if not resolution and candidates_list[0].score > 0.6 and len(candidates_list) < 2:
        # Good confidence, no other options, resolved
        resolution = candidates_list[0]
        status = reason
    if not resolution and len(candidates_list) == 1:
        # Low confidence, no other options, resolved
        resolution = candidates_list[0]
        status = "pending"
    # Assert:0.5 < Best core < 0.9 ; more than 1 candidate
    if not resolution and (candidates_list[0].score - candidates_list[1].score) > 0.2:
        # Good confidence, clear margin over next option, resolved
        resolution = candidates_list[0]
        status = reason
    if not resolution:
        resolution = candidates_list[0]
        status = "pending"
    return resolution if resolution else CAND_TODO, status


def save_resolution(
    candidates: dict[int, CandidateList], conn: "Database", reason="auto"
) -> dict[int, bool]:
    resolution_map = dict[int, bool]()
    for play_id, candidates_list in candidates.items():
        resolution, status = find_best_candidate(candidates_list, reason)
        # Save to DB
        song_id = None
        if isinstance(resolution, CandidateByID):
            song_id = resolution.song_id
        else:
            # Look up song_id
            song_id = conn.fetch_one_or_none(
                int,
                """
            SELECT song_id FROM song
            WHERE song_key = ?""",
                resolution.song.unique_key(),
            )
        if not song_id:
            raise ValueError("Song resolved but not found in DB")
        conn.exec(
            """INSERT OR REPLACE INTO play_resolution
            (play_id, song_id, chosen_score, status) VALUES
            (?,       ?,       ?,            ?     )""",
            play_id,
            song_id,
            resolution.score,
            status,
        )
        resolution_map[play_id] = status != "pending"
    return resolution_map


def unique_candidates(candidates: dict[int, CandidateList]) -> dict[int, CandidateList]:
    """Keep only one candidate for song
    in case of multiple songs with the same title+performer (and different year/country/...)"""
    new_candidates_list = dict[int, CandidateList]()
    for play_id, candidates_list in candidates.items():
        if candidates_list != sorted(candidates_list, key=lambda c: c.score, reverse=True):
            raise ValueError("Candidates list not sorted")
        seen_song = dict[str, CandidateBySong]()
        seen_id = dict[int, CandidateByID]()
        oks = list[CandidateBySong | CandidateByID]()
        for candidate in candidates_list:
            if isinstance(candidate, CandidateByID):
                if candidate.song_id not in seen_id:
                    oks.append(candidate)
                    seen_id[candidate.song_id] = candidate
            else:
                k = candidate.song.unique_key()
                if k not in seen_song:
                    seen_song[k] = candidate
                else:
                    # Keep best
                    if candidate.score > seen_song[k].score:
                        seen_song[k] = candidate
                    # Or keep older
                    elif candidate.song.year is not None and candidate.song.year > 1:
                        current = seen_song[k]
                        if (
                            current.song.year is None
                            or current.song.year <= 1
                            or current.song.year > candidate.song.year
                        ):
                            seen_song[k] = candidate
        if seen_id and seen_song:
            raise ValueError(f"Mixed candidate types for play {play_id}")
        if seen_id:
            new_candidates_list[play_id] = list(seen_id.values())
        else:
            new_candidates_list[play_id] = list(seen_song.values())
    return new_candidates_list


def main() -> None:
    with utils.conn_db() as conn:
        spotify_limit = 20
        while spotify_limit > 0:
            candidates: dict[int, CandidateList] = {}
            todos = find_play_todo(conn, spotify_limit)
            if not todos:
                break
            for play_id, title, performer in todos:
                if not title.strip() or not performer.strip():
                    # empty parts, do not handle
                    candidates[play_id] = [CAND_TODO]
                    continue
                # DB first
                song_match = db_find(title, performer, conn)
                if song_match:
                    candidates[play_id] = [CandidateByID(s[0], s[1], "db") for s in song_match]
                if play_id not in candidates:
                    releases = []
                    releases = spotify_find(title, performer, get_token())
                    if releases:
                        candidates[play_id] = [
                            CandidateBySong(Song.from_spotify(ss), ss.score, "spotify")
                            for ss in releases
                        ]
                    spotify_limit -= 1
                    sleep(1)
                if play_id not in candidates:
                    # Generate one fake candidate
                    candidates[play_id] = [CAND_TODO]
            candidates = unique_candidates(candidates)
            save_candidates(candidates, conn)
            save_resolution(candidates, conn)
            spotify_limit -= 1


if __name__ == "__main__":
    main()
