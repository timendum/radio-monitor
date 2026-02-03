"""Test to path virgin + musicbrainz"""

import unittest
import unittest.mock as mock
from pathlib import Path

import vcr
from test_e2e_ok import basic_match_checks, empty_songs_checks, one_play_checks
from vcr.record_mode import RecordMode

from monitor import db_init, smatcher, utils
from monitor.musicbrainz import find_releases as mb_find_releases
from monitor.radio import virgin


class E2ETestCaseMB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_e2e_mb.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db(path=""):
            return cls.orig_db("test_e2e_mb.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def test_1_virgin(self):
        """Insert a know song, the match in db"""
        acquisition_id = utils.generate_batch("e2e_virgin")
        with mock.patch("monitor.radio.virgin.parse", create=True) as mock_input:
            mock_input.side_effect = [("FLORENCE + THE MACHINE", "BUCKLE", "{mock:true}")]
            virgin.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "virgin")
            self.assertEqual(title, "BUCKLE")
            self.assertEqual(performer, "FLORENCE + THE MACHINE")
            self.assertEqual(db_acquisition_id, acquisition_id)

    def test_3_mb(self):
        """Perform a match against MusicBrainz and verify db"""
        with utils.conn_db() as conn:
            empty_songs_checks(self, conn)
            _, title, performer, _, play_id = one_play_checks(self, conn)
            my_vcr = vcr.VCR(record_mode=RecordMode.ONCE)
            with my_vcr.use_cassette("fixtures/e2e_virgin_musicbrainz.yml"):  # type: ignore
                releases = mb_find_releases(title, performer)
            self.assertTrue(releases, "MusicBrainz should return some releases")
            candidates = {
                play_id: [
                    smatcher.CandidateBySong(smatcher.Song.from_spotify(ss), ss.score, "mbrainz")
                    for ss in releases
                ]
            }
            smatcher.save_candidates(candidates, conn)
            res = smatcher.save_resolution(candidates, conn)
            self.assertIsNotNone(res, "A resolution should be present")
            status = basic_match_checks(self, conn)
            self.assertEqual(status, "auto")

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
