import unittest
from pathlib import Path

import vcr
from test_e2e_ok import one_play_checks
from vcr.record_mode import RecordMode

from monitor import db_init, utils
from monitor.radio import capital, deejay, m2o, r101, r105, rds, virgin


class RadiosTestCaseDJ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_radio.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db(path=""):
            return cls.orig_db("test_radio.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def test_0_db(self):
        # STATION table
        with utils.conn_db() as conn:
            rows = conn.fetch_many(
                tuple[str, str, bool], "SELECT station_code, display_name, active FROM station"
            )
            self.assertTrue(rows, "Station table is empty")
            self.assertGreater(len(rows), 1, "Station table should have more than one row")
            self.assertEqual(
                len([r for r in rows if "deejay" in r[1].lower()]), 1, "Deejay station not found"
            )
            # COUNTRY table
            rows = conn.fetch_many(tuple[str, str], "SELECT country_code, name FROM country")
            self.assertTrue(rows, "Country table is empty")
            self.assertGreater(len(rows), 1, "Country table should have more than one row")
            self.assertEqual(
                len([r for r in rows if "italy" == r[1].lower()]), 1, "Italy country not found"
            )
            # TODO song
            rows = conn.fetch_many(tuple[str, str], "SELECT song_title, song_performers FROM song")
            self.assertTrue(rows, "Song table is empty")
            self.assertEqual(len(rows), 1, "Song table should have one row")
            self.assertEqual(rows[0], ("TODO", "TODO"), "TODO song not found")

    def test_capital(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_capital")
        with my_vcr.use_cassette("fixtures/e2e_capital.yml"):  # type: ignore
            capital.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "capital")
            self.assertEqual(title, "Catching Bodies")
            self.assertEqual(performer, "SEKOU")
            self.assertEqual(db_acquisition_id, acquisition_id)
            # Clean up
            conn.exec("DELETE FROM play")

    def test_m2o(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_m2o")
        with my_vcr.use_cassette("fixtures/e2e_m2o.yml"):  # type: ignore
            m2o.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "m2o")
            self.assertEqual(title, "The Fate of Ophelia")
            self.assertEqual(performer, "TAYLOR SWIFT")
            self.assertEqual(db_acquisition_id, acquisition_id)
            # Clean up
            conn.exec("DELETE FROM play")

    def test_r101(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_r101")
        with my_vcr.use_cassette("fixtures/e2e_r101.yml"):  # type: ignore
            r101.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "r101")
            self.assertEqual(title, "SNAP")
            self.assertEqual(performer, "ROSA LINN")
            self.assertEqual(db_acquisition_id, acquisition_id)
            # Clean up
            conn.exec("DELETE FROM play")

    def test_r105(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_r105")
        with my_vcr.use_cassette("fixtures/e2e_r105.yml"):  # type: ignore
            r105.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "r105")
            self.assertEqual(title, "NO CAP (Radio Edit)")
            self.assertEqual(performer, "DISCLOSURE & ANDERSON .PAAK")
            self.assertEqual(db_acquisition_id, acquisition_id)
            # Clean up
            conn.exec("DELETE FROM play")

    def test_rds(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_rds")
        with my_vcr.use_cassette("fixtures/e2e_rds.yml"):  # type: ignore
            rds.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "rds")
            self.assertEqual(title, "Camera")
            self.assertEqual(performer, "Ed Sheeran")
            self.assertEqual(db_acquisition_id, acquisition_id)
            # Clean up
            conn.exec("DELETE FROM play")

    def test_dj(self):
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
            # Clean up
            conn.exec("DELETE FROM play")

    def test_virgin(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id = utils.generate_batch("e2e_virgin")
        with my_vcr.use_cassette("fixtures/e2e_virgin.yml"):  # type: ignore
            virgin.main(acquisition_id)
        with utils.conn_db() as conn:
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            self.assertEqual(station_name, "virgin")
            self.assertEqual(title, "BUCKLE")
            self.assertEqual(performer, "FLORENCE + THE MACHINE")
            self.assertEqual(db_acquisition_id, acquisition_id)
            # Clean up
            conn.exec("DELETE FROM play")

    def test_double_dj(self):
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
        with my_vcr.use_cassette("fixtures/e2e_dj.yml"):  # type: ignore
            deejay.main(acquisition_id)
        with utils.conn_db() as conn:
            # no double insert
            station_name, title, performer, db_acquisition_id, _ = one_play_checks(self, conn)
            # Clean up
            conn.exec("DELETE FROM play")

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
