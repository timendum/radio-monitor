import sqlite3
import unittest
from pathlib import Path

import vcr
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

        def test_conn_db():
            return sqlite3.Connection("test_radio.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()
        cls.conn = utils.conn_db()

    def test_0_db(self):
        # STATION table
        rows = self.conn.execute(
            "SELECT station_code, display_name, active FROM station"
        ).fetchall()
        self.assertTrue(rows)
        self.assertGreater(len(rows), 1)
        self.assertEqual(len([r for r in rows if "deejay" in r[1].lower()]), 1)
        # COUNTRY table
        rows = self.conn.execute("SELECT country_code, name FROM country").fetchall()
        self.assertTrue(rows)
        self.assertGreater(len(rows), 1)
        self.assertEqual(len([r for r in rows if "italy" == r[1].lower()]), 1)
        # TODO song
        rows = self.conn.execute("SELECT song_title, song_performers FROM song").fetchall()
        self.assertTrue(rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], ("TODO", "TODO"))

    def test_capital(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id=utils.generate_batch("e2e_capital")
        with my_vcr.use_cassette("fixtures/e2e_capital.yml"):  # type: ignore
            capital.main(acquisition_id)
        conn = utils.conn_db()
        rows = conn.execute(
            "SELECT station_id, title_raw, performer_raw, acquisition_id FROM play"
        ).fetchall()
        self.assertTrue(rows)
        self.assertGreaterEqual(len(rows), 1)
        row = rows[0]
        # Check station id
        s_rows = self.conn.execute(
            "SELECT station_code, display_name, active FROM station WHERE station_id = ?", (row[0],)
        ).fetchone()
        self.assertTrue(s_rows)
        self.assertEqual(s_rows[1].lower(), "capital")
        self.assertEqual(row[1], "Catching Bodies")
        self.assertEqual(row[2], "SEKOU")
        self.assertEqual(row[3], acquisition_id)
        # Clean up
        conn.execute("DELETE FROM play")
        conn.commit()

    def test_m2o(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id=utils.generate_batch("e2e_m2o")
        with my_vcr.use_cassette("fixtures/e2e_m2o.yml"):  # type: ignore
            m2o.main(acquisition_id)
        conn = utils.conn_db()
        rows = conn.execute(
            "SELECT station_id, title_raw, performer_raw, acquisition_id FROM play"
        ).fetchall()
        self.assertTrue(rows)
        self.assertGreaterEqual(len(rows), 1)
        row = rows[0]
        # Check station id
        s_rows = self.conn.execute(
            "SELECT station_code, display_name, active FROM station WHERE station_id = ?", (row[0],)
        ).fetchone()
        self.assertTrue(s_rows)
        self.assertEqual(s_rows[1].lower(), "m2o")
        self.assertEqual(row[1], "The Fate of Ophelia")
        self.assertEqual(row[2], "TAYLOR SWIFT")
        self.assertEqual(row[3], acquisition_id)
        # Clean up
        conn.execute("DELETE FROM play")
        conn.commit()

    def test_r101(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id=utils.generate_batch("e2e_r101")
        with my_vcr.use_cassette("fixtures/e2e_r101.yml"):  # type: ignore
            r101.main(acquisition_id)
        conn = utils.conn_db()
        rows = conn.execute(
            "SELECT station_id, title_raw, performer_raw, acquisition_id FROM play"
        ).fetchall()
        self.assertTrue(rows)
        self.assertGreaterEqual(len(rows), 1)
        row = rows[0]
        # Check station id
        s_rows = self.conn.execute(
            "SELECT station_code, display_name, active FROM station WHERE station_id = ?", (row[0],)
        ).fetchone()
        self.assertTrue(s_rows)
        self.assertEqual(s_rows[1].lower(), "r101")
        self.assertEqual(row[1], "SNAP")
        self.assertEqual(row[2], "ROSA LINN")
        self.assertEqual(row[3], acquisition_id)
        # Clean up
        conn.execute("DELETE FROM play")
        conn.commit()

    def test_r105(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id=utils.generate_batch("e2e_r105")
        with my_vcr.use_cassette("fixtures/e2e_r105.yml"):  # type: ignore
            r105.main(acquisition_id)
        conn = utils.conn_db()
        rows = conn.execute(
            "SELECT station_id, title_raw, performer_raw, acquisition_id FROM play"
        ).fetchall()
        self.assertTrue(rows)
        self.assertGreaterEqual(len(rows), 1)
        row = rows[0]
        # Check station id
        s_rows = self.conn.execute(
            "SELECT station_code, display_name, active FROM station WHERE station_id = ?", (row[0],)
        ).fetchone()
        self.assertTrue(s_rows)
        self.assertEqual(s_rows[1].lower(), "r105")
        self.assertEqual(row[1], "NO CAP (Radio Edit)")
        self.assertEqual(row[2], "DISCLOSURE & ANDERSON .PAAK")
        self.assertEqual(row[3], acquisition_id)
        # Clean up
        conn.execute("DELETE FROM play")
        conn.commit()

    def test_rds(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id=utils.generate_batch("e2e_rds")
        with my_vcr.use_cassette("fixtures/e2e_rds.yml"):  # type: ignore
            rds.main(acquisition_id)
        conn = utils.conn_db()
        rows = conn.execute(
            "SELECT station_id, title_raw, performer_raw, acquisition_id FROM play"
        ).fetchall()
        self.assertTrue(rows)
        self.assertGreaterEqual(len(rows), 1)
        row = rows[0]
        # Check station id
        s_rows = self.conn.execute(
            "SELECT station_code, display_name, active FROM station WHERE station_id = ?", (row[0],)
        ).fetchone()
        self.assertTrue(s_rows)
        self.assertEqual(s_rows[1].lower(), "rds")
        self.assertEqual(row[1], "Camera")
        self.assertEqual(row[2], "Ed Sheeran")
        self.assertEqual(row[3], acquisition_id)
        # Clean up
        conn.execute("DELETE FROM play")
        conn.commit()

    def test_dj(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id=utils.generate_batch("e2e_dj")
        with my_vcr.use_cassette("fixtures/e2e_dj.yml"):  # type: ignore
            deejay.main(acquisition_id)
        conn = utils.conn_db()
        rows = conn.execute(
            "SELECT station_id, title_raw, performer_raw, acquisition_id FROM play"
        ).fetchall()
        self.assertTrue(rows)
        self.assertGreaterEqual(len(rows), 1)
        row = rows[0]
        # Check station id
        s_rows = self.conn.execute(
            "SELECT station_code, display_name, active FROM station WHERE station_id = ?", (row[0],)
        ).fetchone()
        self.assertTrue(s_rows)
        self.assertEqual(s_rows[1].lower(), "deejay")
        self.assertEqual(row[1], "When I Come Around")
        self.assertEqual(row[2], "GREEN DAY")
        self.assertEqual(row[3], acquisition_id)
        # Clean up
        conn.execute("DELETE FROM play")
        conn.commit()

    def test_virgin(self):
        """Insert a know song, the match in db"""
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        acquisition_id=utils.generate_batch("e2e_virgin")
        with my_vcr.use_cassette("fixtures/e2e_virgin.yml"):  # type: ignore
            virgin.main(acquisition_id)
        conn = utils.conn_db()
        rows = conn.execute(
            "SELECT station_id, title_raw, performer_raw, acquisition_id FROM play"
        ).fetchall()
        self.assertTrue(rows)
        self.assertGreaterEqual(len(rows), 1)
        row = rows[0]
        # Check station id
        s_rows = self.conn.execute(
            "SELECT station_code, display_name, active FROM station WHERE station_id = ?", (row[0],)
        ).fetchone()
        self.assertTrue(s_rows)
        self.assertEqual(s_rows[1].lower(), "virgin")
        self.assertEqual(row[1], "BUCKLE")
        self.assertEqual(row[2], "FLORENCE + THE MACHINE")
        self.assertEqual(row[3], acquisition_id)
        # Clean up
        conn.execute("DELETE FROM play")
        conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
