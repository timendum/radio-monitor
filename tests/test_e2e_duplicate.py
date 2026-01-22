"""Test to check against duplicate title+performer from spotify"""

import unittest
from pathlib import Path

import vcr
from test_e2e_ok import basic_match_checks, empty_songs_checks
from vcr.record_mode import RecordMode

from monitor import db_init, smatcher, utils


class E2ETestCaseDuplicate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_e2e_dupe.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db(path=""):
            return cls.orig_db("test_e2e_dupe.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def test_1_vasco(self):
        """Perform a match against Spotify and verify db"""
        with utils.conn_db() as conn:
            empty_songs_checks(self, conn)
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
            play_id = p_rows[0][0]
            self.assertIsInstance(play_id, int)
            my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
            with my_vcr.use_cassette(
                "fixtures/e2e_dupe_vasco.yml", filter_headers=["Authorization"]
            ):  # type: ignore
                smatcher.main()
            basic_match_checks(self, conn)
            # artist
            rows = conn.execute("SELECT artist_id, artist_name FROM artist").fetchall()
            artists = {row[1] for row in rows}
            self.assertEqual(len(rows), len(artists), "Duplicate artists found in artist table")
            rows = conn.execute(
                "SELECT song_id, song_key, song_title, song_performers FROM song"
            ).fetchall()
            song_keys = {row[1] for row in rows}
            self.assertEqual(len(rows), len(song_keys), "Duplicate song keys found in song table")
            songs = {(row[2] + row[3]).strip().lower() for row in rows}
            self.assertEqual(len(rows), len(songs), "Duplicate songs found in song table")

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
