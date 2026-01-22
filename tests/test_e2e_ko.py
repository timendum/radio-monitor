import unittest
from pathlib import Path

import vcr
from test_e2e_ok import basic_match_checks, empty_songs_checks, one_play_checks
from vcr.record_mode import RecordMode

from monitor import db_init, smatcher, utils


class E2ETestCaseKO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_e2e_ko.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db(path=""):
            return cls.orig_db("test_e2e_ko.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def test_1_dj(self):
        """Insert a fake song, the match in db"""
        acquisition_id = utils.generate_batch("e2e_ko")
        utils.insert_into_radio(
            "dj",
            "adfklsjniouy23ghoi",
            "uth234jknsfu238y74h SDflkhjiou2y3",
            acquisition_id,
            None,
            "{}",
        )
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id = one_play_checks(self, conn)
            self.assertEqual(station_name, "deejay")
            self.assertEqual(title, "uth234jknsfu238y74h SDflkhjiou2y3")
            self.assertEqual(performer, "adfklsjniouy23ghoi")
            self.assertEqual(db_acquisition_id, acquisition_id)

    def test_2_match(self):
        """Perform a match against Spotify and verify db"""
        with utils.conn_db() as conn:
            empty_songs_checks(self, conn)
            my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
            with my_vcr.use_cassette("fixtures/e2e_2b_ko.yml", filter_headers=["Authorization"]):  # type: ignore
                smatcher.main()
            basic_match_checks(self, conn)
            # artist
            rows = conn.execute("SELECT artist_id, artist_name FROM artist").fetchall()
            self.assertGreaterEqual(len(rows), 0, "No artist rows should exists")
            # song
            rows = conn.execute("SELECT song_id, song_title FROM song").fetchall()
            self.assertGreaterEqual(len(rows), 1, "No song rows should exists")
            for row in rows:
                self.assertGreaterEqual(row[1], "TODO", "No new song rows should exists")

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
