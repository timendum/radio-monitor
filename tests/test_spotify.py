import unittest

import vcr
from vcr.record_mode import RecordMode

from monitor import spotify


class SpotifyTestCase(unittest.TestCase):
    def test_find_releases(self):
        my_vcr = vcr.VCR(record_mode=RecordMode.NONE)
        with my_vcr.use_cassette("fixtures/sp_fd_police.yml", filter_headers=["Authorization"]):  # type: ignore
            token = spotify.get_token()
            releases = spotify.find_releases("Synchronicity II", "The Police", token)
        self.assertGreaterEqual(len(releases), 1)
        release = releases[0]
        self.assertEqual(release.title, "Synchronicity II")
        self.assertEqual(release.s_performers, "The Police")
        self.assertGreaterEqual(len(release.l_performers), 1)
        self.assertEqual(release.s_performers, release.l_performers[0])
        self.assertEqual(release.country, "GB")
        self.assertEqual(release.year, 1983)
        self.assertAlmostEqual(release.score, 1)
        self.assertEqual(release.duration, 300)


if __name__ == "__main__":
    unittest.main()
