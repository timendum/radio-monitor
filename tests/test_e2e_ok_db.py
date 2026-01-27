"""Test to check happy path deejay+db"""

import unittest
from pathlib import Path

import vcr
from test_e2e_ok import basic_match_checks, empty_songs_checks, one_play_checks
from vcr.record_mode import RecordMode

from monitor import db_init, smatcher, utils
from monitor.radio import deejay


class E2ETestCaseDJ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_e2e_ok_db.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db(path=""):
            return cls.orig_db("test_e2e_ok_db.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def test_1_dj(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_dj")
        with my_vcr.use_cassette("fixtures/e2e_dj.yml"):  # type: ignore
            deejay.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "deejay")
            self.assertEqual(title, "When I Come Around")
            self.assertEqual(performer, "GREEN DAY")
            self.assertEqual(db_acquisition_id, acquisition_id)

    def test_2_insert_song_db(self):
        with utils.conn_db() as conn:
            empty_songs_checks(self, conn)
            _, _, _, _, play_id = one_play_checks(self, conn)
            candidates = {
                play_id: [
                    smatcher.CandidateBySong(
                        smatcher.Song(
                            "When I Come Around",
                            "Green Day",
                            ("Green Day",),
                            "USRE19900154",
                            1994,
                            "US",
                            178,
                        ),
                        1,
                        "test",
                    )
                ]
            }
            smatcher.save_candidates(candidates, conn)
            smatcher.save_resolution(candidates, conn, "human")
            status = basic_match_checks(self, conn)
            self.assertEqual(status, "human")
            conn.exec("DELETE FROM match_candidate")
            conn.exec("DELETE FROM play_resolution")
            # artist
            rows = conn.fetch_many(tuple[int, str], "SELECT artist_id, artist_name FROM artist")
            self.assertGreaterEqual(len(rows), 1, "Artist rows should persist")
            # song
            rows = conn.fetch_many(
                tuple[int, str, str], "SELECT song_id, song_title, song_key FROM song"
            )
            self.assertGreaterEqual(len(rows), 1, "Song rows should persist")
            # song_artist
            rows = conn.fetch_many(int, "SELECT artist_id FROM song_artist")
            self.assertGreaterEqual(len(rows), 1, "song_artist rows should persist")
            # song_alias
            rows = conn.fetch_many(int, "SELECT song_id FROM song_alias")
            self.assertGreaterEqual(len(rows), 1, "song_alias rows should persist")

    def test_3_match(self):
        """Perform a match against Spotify and verify db"""
        with utils.conn_db() as conn:
            my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
            with my_vcr.use_cassette(
                "fixtures/e2e_smatcher_no_call.yml", filter_headers=["Authorization"]
            ):  # type: ignore
                smatcher.main()
            status = basic_match_checks(self, conn)
            self.assertEqual(status, "auto")

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
