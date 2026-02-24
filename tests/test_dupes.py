import unittest
from pathlib import Path

from monitor import db_init, utils
from monitor.dupes import (
    _FullSong,
    _SongCandidate,
    find_song_dupes,
    find_song_tocheck,
    save_work_review,
    sort_cand,
)


class DupesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db = utils.conn_db
        try:
            Path("test_dupes.sqlite3").unlink()
        except FileNotFoundError:
            pass

        def test_conn_db(path=""):
            return cls.orig_db("test_dupes.sqlite3")

        utils.conn_db = test_conn_db
        db_init.main()

    def get_work_rows(self, song_id: int) -> tuple[list[tuple], list[tuple]]:
        with utils.conn_db() as conn:
            song_work_review = conn.fetch_many(
                    tuple,
                    "SELECT * FROM song_work_review WHERE song_id_a = ? or song_id_b = ?",
                    song_id,
                    song_id,
                )
            song_work = conn.fetch_many(
                tuple,
                "SELECT * FROM song_work WHERE song_id = ? or master_song_id = ?",
                    song_id,
                    song_id,
            )
        return song_work_review, song_work

    def test_1_empty_insert(self):
        """Test inserting empty song and insert 1-10 songs"""
        with utils.conn_db() as conn:
            result = find_song_tocheck(-1, conn)
            self.assertIsNone(result)
            # Insert songs with play_resolution to appear in v_master_song
            for i in range(10):
                conn.exec(
                    "INSERT INTO song (song_key, song_title, song_performers) VALUES (?, ?, ?)",
                    f"k{i + 1}",
                    f"Song {i + 1}",
                    f"Artist {i + 1}",
                )
            for i in [1, 2, 3, 4, 5, 6]:
                conn.exec(
                    "INSERT INTO play_resolution (song_id, status) VALUES (?, ?)",
                    i,
                    "auto",
                )

    def test_2_find_song_tocheck(self):
        """Test finding next song to check with data"""
        with utils.conn_db() as conn:
            result = find_song_tocheck(-1, conn)
            self.assertIsNotNone(result)
            if result:
                self.assertEqual(result.song_id, 1)
                result = find_song_tocheck(result.song_id, conn)
                self.assertIsNotNone(result)
                if result:
                    self.assertEqual(result.song_id, 2)

    def test_2_save_work_review_same(self):
        """Test saving work review for same songs"""
        master_id = 2
        with utils.conn_db() as conn:
            save_work_review(master_id, [1, 10], True, conn) # this exclude song_id = 1
            song_work_review, song_work = self.get_work_rows(master_id)
            self.assertEqual(len(song_work_review), 2)
            self.assertEqual(len(song_work), 2)

    def test_3_save_work_review_different(self):
        """Test saving work review for different songs"""
        master_id = 3
        with utils.conn_db() as conn:
            save_work_review(master_id, [1, 10], False, conn)
            song_work_review, song_work = self.get_work_rows(master_id)
            self.assertEqual(len(song_work_review), 2)
            self.assertEqual(len(song_work), 0)

    def test_4_tocheck_after(self):
        with utils.conn_db() as conn:
            # 1 is child, skipped, 2 is master
            result = find_song_tocheck(-1, conn)
            self.assertIsNotNone(result)
            if not result:
                return
            self.assertEqual(result.song_id, 2)
            self.assertEqual(result.master_song_id, 10)
            result = find_song_dupes(result.song_id, result.master_song_id, conn)
            # 2 has no candidates because is matched until 10 (last song_id)
            self.assertFalse(result)
            result = find_song_tocheck(2, conn)
            self.assertIsNotNone(result)
            if not result:
                return
            self.assertEqual(result.song_id, 3)
            self.assertEqual(result.master_song_id, 10)
            # 3 has no candidates because is matched until 10 (last song_id)
            result = find_song_dupes(result.song_id, result.master_song_id, conn)
            self.assertFalse(result)
            result = find_song_tocheck(3, conn)
            self.assertIsNotNone(result)
            if not result:
                return
            self.assertEqual(result.song_id, 4)
            self.assertLess(result.master_song_id, 10)
            # 4 is ok, has dupes to check
            result = find_song_dupes(result.song_id, result.master_song_id, conn)
            self.assertTrue(result)

    def test_sort_cand_by_score(self):
        """Test sorting candidates by similarity score"""
        song = _FullSong(1, "Test Song", "Test Artist", None, None, 0, 0)
        candidates = [
            _SongCandidate(2, "Different", "Different", None, None, 0),
            _SongCandidate(3, "Test Song", "Test Artist", None, None, 0),
            _SongCandidate(4, "Test", "Test Artist", None, None, 0),
        ]
        sorted_candidates = sort_cand(candidates, song)
        self.assertEqual(sorted_candidates[0].song_id, 3)

    def test_sort_cand_empty(self):
        """Test sorting empty candidate list"""
        song = _FullSong(1, "Test", "Artist", None, None, 0, 0)
        result = sort_cand([], song)
        self.assertEqual(len(result), 0)

    @classmethod
    def tearDownClass(cls):
        utils.conn_db = cls.orig_db


if __name__ == "__main__":
    unittest.main()
