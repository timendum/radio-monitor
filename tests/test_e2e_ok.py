"""Test to check happy path deejay+spotify"""

import sqlite3
import unittest
from pathlib import Path

import vcr
from vcr.record_mode import RecordMode

from monitor import db_init, smatcher, utils
from monitor.radio import deejay


def empty_songs_checks(self: unittest.TestCase, conn: sqlite3.Connection):
    """Sanity check - empty tables"""
    rows = conn.execute("SELECT artist_id FROM artist").fetchall()
    self.assertFalse(rows, "Table artist should be empty")
    rows = conn.execute("SELECT song_id, song_title FROM song").fetchall()
    self.assertEqual(len(rows), 1, "Table song should be empty")
    self.assertEqual(rows[0][1], "TODO", "Table song contains only TODO")
    rows = conn.execute("SELECT song_id FROM song_artist").fetchall()
    self.assertFalse(rows, "Table song_artist should be empty")
    rows = conn.execute("SELECT song_id, title FROM song_alias").fetchall()
    self.assertEqual(len(rows), 1, "Table song_alias should be empty")
    self.assertEqual(rows[0][1], "TODO", "Table song_alias contains only TODO")
    rows = conn.execute("SELECT song_id FROM match_candidate").fetchall()
    self.assertFalse(rows, "Table match_candidate should be empty")
    rows = conn.execute("SELECT song_id FROM play_resolution").fetchall()
    self.assertFalse(rows, "Table play_resolution should be empty")


def one_play_checks(self: unittest.TestCase, conn: sqlite3.Connection) -> tuple[str, str, str, str]:
    rows = conn.execute(
        "SELECT station_id, title_raw, performer_raw, acquisition_id, play_id FROM play"
    ).fetchall()
    self.assertTrue(rows, "Table play should not be empty")
    self.assertGreaterEqual(len(rows), 1, "Table play should contains one record")
    row = rows[0]
    # Check station id
    s_rows = conn.execute(
        "SELECT station_code, display_name, active FROM station WHERE station_id = ?",
        (row[0],),
    ).fetchone()
    self.assertTrue(s_rows, "Table station should contains one record")
    station_name = s_rows[1].lower()
    title = row[1]
    performer = row[2]
    acquisition_id = row[3]
    play_id = row[4]
    self.assertIsInstance(play_id, int)
    return station_name, title, performer, acquisition_id


def basic_match_checks(self: unittest.TestCase, conn: sqlite3.Connection) -> str:
    # Play id
    p_rows = conn.execute("SELECT play_id, title_raw, performer_raw FROM play").fetchall()
    self.assertEqual(len(p_rows), 1, "Table play should have exactly one row")
    self.assertEqual(len(p_rows[0]), 3)
    play_id, ptitle, pperformer = p_rows[0]
    self.assertIsInstance(play_id, int, "play_id should be an int")
    self.assertIsInstance(ptitle, str, "title_raw should be an str")
    self.assertIsInstance(pperformer, str, "performer_raw should be an istrnt")

    # artist
    rows = conn.execute("SELECT artist_id, artist_name FROM artist").fetchall()
    artist_ids = []
    for row in rows:
        artist_ids.append(row[0])
        self.assertGreaterEqual(
            utils.calc_score("title", row[1], "title", pperformer),
            0.5,
            f"Every artist should be similar enough: '{row[1]}' vs '{pperformer}",
        )
    # song 1
    rows = conn.execute("SELECT song_id, song_title, song_key FROM song").fetchall()
    song_ids = []
    for row in rows:
        if row[1] == "TODO":
            continue
        song_ids.append(row[0])
        self.assertGreaterEqual(len(row[2]), 1, "Every song should have a song_key")
        self.assertIsInstance(row[2], str, "Every song should have a song_key")
        self.assertGreaterEqual(
            utils.calc_score(row[1], "performer", ptitle, "performer"),
            0.5,
            f"Every song title should be similar enough: '{row[1]}' vs '{ptitle}",
        )
    # song_artist by artist_id
    for artist_id in artist_ids:
        rows = conn.execute(
            "SELECT artist_id FROM song_artist WHERE artist_id = ?", (artist_id,)
        ).fetchall()
        self.assertGreaterEqual(
            len(rows),
            1,
            f"Every artist should have at least one song_artist row: {artist_id} has {len(rows)}",
        )
    # song_artist by song_id
    for song_id in song_ids:
        rows = conn.execute(
            "SELECT artist_id FROM song_artist WHERE song_id = ?", (song_id,)
        ).fetchall()
        self.assertGreaterEqual(
            len(rows),
            1,
            f"Every song should have at least one song_artist row: {song_id} has {len(rows)}",
        )
    # song_alias by song_id
    for song_id in song_ids:
        rows = conn.execute(
            "SELECT song_id FROM song_alias WHERE song_id = ?", (song_id,)
        ).fetchall()
        self.assertEqual(
            len(rows),
            1,
            f"Every song should have one song_alias row: {song_id} has {len(rows)}",
        )
    # match_candidate by play_id
    rows = conn.execute(
        "SELECT song_id FROM match_candidate WHERE play_id=?", (play_id,)
    ).fetchall()
    self.assertGreaterEqual(
        len(rows), 1, f"Every play has at least one match_candidate row, {play_id} has {len(rows)}"
    )
    for row in rows:
        # song by match_candidate.song_id
        mc_rows = conn.execute(
            "SELECT song_id, song_title FROM song WHERE song_id = ?", (row[0],)
        ).fetchall()
        self.assertEqual(
            len(mc_rows),
            1,
            f"Every mc should have one song row: {row[0]} has {len(mc_rows)}",
        )
    # play_resolution by play_id
    rows = conn.execute(
        "SELECT song_id, status FROM play_resolution WHERE play_id=?", (play_id,)
    ).fetchall()
    self.assertEqual(
        len(rows),
        1,
        f"Every play should have one play_resolution row: {play_id} has {len(rows)}",
    )
    status = rows[0][1]
    # song by play_resolution.song_id
    pr_rows = conn.execute(
        "SELECT song_id, song_title FROM song WHERE song_id = ?", (rows[0][0],)
    ).fetchall()
    self.assertEqual(
        len(pr_rows),
        1,
        f"Every pr should have one song row: {rows[0][0]} has {len(pr_rows)}",
    )
    return status


class E2ETestCaseDJ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db_path = "test_e2e.sqlite3"
        cls.orig_db = utils.conn_db
        try:
            Path(db_path).unlink()
        except FileNotFoundError:
            pass

        def test_conn_db(path=""):
            return cls.orig_db(db_path)

        utils.conn_db = test_conn_db
        db_init.main()

    def test_1_dj(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_dj")
        with my_vcr.use_cassette("fixtures/e2e_dj.yml"):  # type: ignore
            deejay.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id = one_play_checks(self, conn)
            self.assertEqual(station_name, "deejay")
            self.assertEqual(title, "When I Come Around")
            self.assertEqual(performer, "GREEN DAY")
            self.assertEqual(db_acquisition_id, acquisition_id)

    def test_2_match(self):
        """Perform a match against Spotify and verify db"""
        with utils.conn_db() as conn:
            empty_songs_checks(self, conn)
            my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
            with my_vcr.use_cassette("fixtures/e2e_2b_match.yml", filter_headers=["Authorization"]):  # type: ignore
                smatcher.main()
            status = basic_match_checks(self, conn)
            self.assertEqual(status, "auto")

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
