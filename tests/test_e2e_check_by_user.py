import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import vcr
from test_e2e_multiple_save import candidate_eqgr, check_one_tocheck, check_zero_tocheck
from test_e2e_ok import basic_match_checks, empty_songs_checks, one_play_checks
from test_e2e_solution import check_alias_created
from vcr.record_mode import RecordMode

from monitor import check_song, db_init, smatcher, utils
from monitor.radio import m2o


@contextmanager
def mock_input_print() -> Iterator[MagicMock]:
    try:
        with patch("monitor.check_song.input", create=True) as mock_input:
            with patch("sys.stdout", new_callable=StringIO) as _:
                yield mock_input
    finally:
        pass


class E2ETestCaseCheckByUser(unittest.TestCase):
    match_candidate_count = 0

    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_e2e_check.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db(path=""):
            return cls.orig_db("test_e2e_check.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def test_1_m2o(self):
        """Insert a song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_m2o")
        with my_vcr.use_cassette("fixtures/e2e_pending_m2o.yml"):  # type: ignore
            m2o.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "m2o")
            self.assertEqual(title, "Waterfalls (Not Existing Remix)")
            self.assertEqual(performer, "JAMES HYPE")
            self.assertEqual(db_acquisition_id, acquisition_id)

    def test_2_match(self):
        """Perform a match against Spotify and verify db"""
        with utils.conn_db() as conn:
            empty_songs_checks(self, conn)
            one_play_checks(self, conn)
            my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
            with my_vcr.use_cassette(
                "fixtures/e2e_m2o_spotify.yml", filter_headers=["Authorization"]
            ):  # type: ignore
                smatcher.main()
            status = basic_match_checks(self, conn)
            self.assertEqual(status, "pending", "Status should be pending")
            # match_candidate count
            self.match_candidate_count = candidate_eqgr(self, conn, self.match_candidate_count)
            check_one_tocheck(self, conn)

    def test_3_edit_song(self):
        """Edit a song detail"""
        with utils.conn_db() as conn:
            check_one_tocheck(self, conn)
            s_rows = conn.fetch_many(int, "SELECT song_id FROM song WHERE song_title != 'TODO'")
            self.assertGreaterEqual(len(s_rows), 1, "At least one song should be saved")
            song_id = s_rows[0]
            with mock_input_print() as mock_input:
                mock_input.side_effect = ["!", "1901", "XX"]
                check_song.edit_song(conn, song_id)
            s_rows = conn.fetch_one(
                tuple[int, str], "SELECT year, country FROM song WHERE song_id = ?", song_id
            )
            self.assertEqual(s_rows[0], 1901, "Year should be changed")
            self.assertEqual(s_rows[1], "XX", "Country should be changed")

    def test_4_ask_user(self):
        """Solve by asking user"""
        with utils.conn_db() as conn:
            check_one_tocheck(self, conn)
            _, _, _, _, song_id = one_play_checks(self, conn)
            with mock_input_print() as mock_input:
                mock_input.side_effect = ["CTitle", "CArtist", "1902", "ZZ"]
                check_song.ask_user(song_id, conn)
            status = basic_match_checks(self, conn)
            self.assertEqual(status, "human", "Status should be pending")
            check_alias_created(self, conn)
            check_zero_tocheck(self, conn)

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
