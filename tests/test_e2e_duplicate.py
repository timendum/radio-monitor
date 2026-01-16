"""Test to check against duplicate title+performer from spotify"""

import sqlite3
import unittest
from pathlib import Path

import vcr
from vcr.record_mode import RecordMode

from monitor import db_init, smatcher, utils


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


class E2ETestCaseDuplicate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_e2e_dupe.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db():
            return sqlite3.Connection("test_e2e_dupe.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def test_1_vasco(self):
        """Perform a match against Spotify and verify db"""
        with utils.conn_db() as conn:
            sanity_check(self, conn)
            conn.execute(
                """INSERT INTO play (
                station_id,
                observed_at,
                title_raw,
                performer_raw,
                acquisition_id,
                source_payload
            ) VALUES (
                (SELECT station_id FROM station WHERE station_code = ?),
                ?,
                ?,
                ?,
                ?,
                ?)""",
                (
                    "m2o",
                    "2026-01-01T01:02:03Z",
                    "Eh...Già",
                    "Vasco Rossi",
                    "E2ETestCaseDuplicate",
                    "{}",
                ),
            )
            conn.commit()
            # Play id from test_1a_dj
            p_rows = conn.execute("SELECT play_id, title_raw, performer_raw FROM play").fetchall()
            self.assertEqual(len(p_rows), 1)
            self.assertEqual(len(p_rows[0]), 3)
            play_id, _, _ = p_rows[0]
            my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
            with my_vcr.use_cassette(
                "fixtures/e2e_dupe_vasco.yml", filter_headers=["Authorization"]
            ):  # type: ignore
                smatcher.main()
            # artist
            rows = conn.execute("SELECT artist_id, artist_name FROM artist").fetchall()
            self.assertGreaterEqual(len(rows), 1)
            # song
            rows = conn.execute(
                "SELECT song_id, song_title FROM song WHERE song_title != 'TODO'"
            ).fetchall()
            self.assertGreaterEqual(len(rows), 2)
            # song_artist
            rows = conn.execute("SELECT artist_id FROM song_artist ").fetchall()
            self.assertGreaterEqual(len(rows), 2)
            # match_candidate
            rows = conn.execute(
                "SELECT song_id FROM match_candidate WHERE play_id=?", (play_id,)
            ).fetchall()
            rows = conn.execute(
                "SELECT song_id, song_title FROM song WHERE song_id = ?", (rows[0][0],)
            ).fetchall()
            self.assertGreaterEqual(len(rows), 1)

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
