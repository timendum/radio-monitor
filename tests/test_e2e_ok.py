"""Test to check happy path deejay+spotify"""

import sqlite3
import unittest
from pathlib import Path

import vcr
from vcr.record_mode import RecordMode

from monitor import db_init, smatcher, utils
from monitor.radio import deejay


def sanity_check(self: unittest.TestCase, conn: sqlite3.Connection):
    """Sanity check - empty tables"""
    rows = conn.execute("SELECT artist_id FROM artist").fetchall()
    self.assertFalse(rows)
    rows = conn.execute("SELECT song_id, song_title FROM song").fetchall()
    self.assertEqual(len(rows), 1)
    self.assertEqual(rows[0][1], "TODO")
    rows = conn.execute("SELECT song_id FROM song_artist").fetchall()
    self.assertFalse(rows)
    rows = conn.execute("SELECT song_id, title FROM song_alias").fetchall()
    self.assertEqual(len(rows), 1)
    self.assertEqual(rows[0][1], "TODO")
    rows = conn.execute("SELECT song_id FROM match_candidate").fetchall()
    self.assertFalse(rows)
    rows = conn.execute("SELECT song_id FROM play_resolution").fetchall()
    self.assertFalse(rows)


class E2ETestCaseDJ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_e2e.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db():
            return sqlite3.Connection("test_e2e.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def test_1a_dj(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_dj")
        with my_vcr.use_cassette("fixtures/e2e_dj.yml"):  # type: ignore
            deejay.main(acquisition_id)
        with utils.conn_db() as conn:
            rows = conn.execute(
                "SELECT station_id, title_raw, performer_raw, acquisition_id FROM play"
            ).fetchall()
            self.assertTrue(rows)
            self.assertGreaterEqual(len(rows), 1)
            row = rows[0]
            # Check station id
            s_rows = conn.execute(
                "SELECT station_code, display_name, active FROM station WHERE station_id = ?",
                (row[0],),
            ).fetchone()
            self.assertTrue(s_rows)
            self.assertEqual(s_rows[1].lower(), "deejay")
            self.assertEqual(row[1], "When I Come Around")
            self.assertEqual(row[2], "GREEN DAY")
            self.assertEqual(row[3], acquisition_id)

    def test_1b_match(self):
        """Perform a match against Spotify and verify db"""
        with utils.conn_db() as conn:
            sanity_check(self, conn)
            # Play id from test_1a_dj
            p_rows = conn.execute("SELECT play_id, title_raw, performer_raw FROM play").fetchall()
            self.assertEqual(len(p_rows), 1)
            self.assertEqual(len(p_rows[0]), 3)
            play_id, ptitle, pperformer = p_rows[0]
            self.assertIsInstance(play_id, int)
            self.assertIsInstance(ptitle, str)
            self.assertIsInstance(pperformer, str)
            my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
            with my_vcr.use_cassette("fixtures/e2e_2b_match.yml", filter_headers=["Authorization"]):  # type: ignore
                smatcher.main()
            # artist
            rows = conn.execute("SELECT artist_id, artist_name FROM artist").fetchall()
            artist_ids = []
            for row in rows:
                artist_ids.append(row[0])
                # TEST: Every artist is similar enough
                self.assertGreaterEqual(utils.calc_score("title", row[1], "title", pperformer), 0.8)
            # song 1
            rows = conn.execute("SELECT song_id, song_title, song_key FROM song").fetchall()
            song_ids = []
            for row in rows:
                if row[1] != "TODO":
                    song_ids.append(row[0])
                    # TEST: Every song has a key
                    self.assertGreaterEqual(len(row[2]), 1)
                    # TEST: Every song title is similar enough
                    self.assertGreaterEqual(
                        utils.calc_score(row[1], "performer", ptitle, "performer"), 0.5
                    )
            # TEST: Every artist row has at least one song_artist row
            for artist_id in artist_ids:
                rows = conn.execute(
                    "SELECT artist_id FROM song_artist WHERE artist_id = ?", (artist_id,)
                ).fetchall()
                self.assertGreaterEqual(len(rows), 1)
            # TEST: Every song row has at least one song_artist row
            for song_id in song_ids:
                rows = conn.execute(
                    "SELECT artist_id FROM song_artist WHERE song_id = ?", (song_id,)
                ).fetchall()
                self.assertGreaterEqual(len(rows), 1, f"song_artist.song_id {song_id}")
            # TEST: Every song row has one song_artist row
            for song_id in song_ids:
                rows = conn.execute(
                    "SELECT song_id FROM song_alias WHERE song_id = ?", (song_id,)
                ).fetchall()
                self.assertEqual(len(rows), 1)
            # TEST: Every play row has at least one match_candidate row
            rows = conn.execute(
                "SELECT song_id FROM match_candidate WHERE play_id=?", (play_id,)
            ).fetchall()
            self.assertGreaterEqual(len(rows), 1)
            for row in rows:
                # TEST: Every match_candidate row its song row
                mc_rows = conn.execute(
                    "SELECT song_id, song_title FROM song WHERE song_id = ?", (row[0],)
                ).fetchall()
                self.assertEqual(len(mc_rows), 1)
            # TEST: Every play row has one play_resolution row
            rows = conn.execute(
                "SELECT song_id FROM play_resolution WHERE play_id=?", (play_id,)
            ).fetchall()
            self.assertEqual(len(rows), 1)
            # TEST: Every play_resolution row has its song row
            pr_rows = conn.execute(
                "SELECT song_id, song_title FROM song WHERE song_id = ?", (rows[0][0],)
            ).fetchall()
            self.assertEqual(len(pr_rows), 1)

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
