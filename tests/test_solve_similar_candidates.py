import unittest

from monitor.check_song import solve_similar_candidates


class SolveSimilarCandidatesTestCase(unittest.TestCase):
    def _make_candidate(self, title, performers, year=None, song_id=1, nuses=0):
        """Helper to create mock candidate tuples"""
        return type(
            "Candidate",
            (),
            {
                "title": title,
                "performers": performers,
                "isrc": None,
                "year": year,
                "country": None,
                "duration": None,
                "song_id": song_id,
                "nuses": nuses,
            },
        )()

    def test_single_perfect_match(self):
        """Test with one perfect match"""
        rows = [self._make_candidate("Test Song", "Test Artist", 2020, 1)]
        result = solve_similar_candidates(1, "Test Song", "Test Artist", rows)
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.song_id, 1)

    def test_multiple_same_title_performer_returns_oldest(self):
        """Test with multiple candidates having same title/performer, returns oldest"""
        rows = [
            self._make_candidate("Song", "Artist", 2020, 1),
            self._make_candidate("Song", "Artist", 2015, 2),
            self._make_candidate("Song", "Artist", 2018, 3),
        ]
        result = solve_similar_candidates(1, "Song", "Artist", rows)
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.song_id, 2)

    def test_perfect_match_with_no_year(self):
        """Test perfect match without year information"""
        rows = [self._make_candidate("Song", "Artist", None, 1)]
        result = solve_similar_candidates(1, "Song", "Artist", rows)
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.song_id, 1)

    def test_similar_candidates_high_score(self):
        """Test with similar candidates having same normalized title/performer"""
        rows = [
            self._make_candidate("Song (Remix)", "Artist feat. Other", 2020, 1),
            self._make_candidate("Song - Live", "Artist & Other", 2015, 2),
        ]
        result = solve_similar_candidates(1, "Song", "Artist", rows)
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.song_id, 2)

    def test_no_match_returns_none(self):
        """Test with no matching candidates"""
        rows = [self._make_candidate("Different Song", "Different Artist", 2020, 1)]
        result = solve_similar_candidates(1, "Test Song", "Test Artist", rows)
        self.assertIsNone(result)

    def test_empty_rows(self):
        """Test with empty candidate list"""
        result = solve_similar_candidates(1, "Song", "Artist", [])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
