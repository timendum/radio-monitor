import secrets
import string
import unittest

from monitor import utils


def _random_ascii_alnum(length: int) -> str:
    alphabet = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return "".join(secrets.choice(alphabet) for _ in range(length))


class UtilTestCase(unittest.TestCase):
    def test_generate_batch(self):
        self.assertTrue("_" in utils.generate_batch())
        self.assertTrue(utils.generate_batch("aabbcc").startswith("aabbcc"))

    def test_clear_artist(self):
        self.assertEqual(utils.clear_artist("Abba"), "abba")
        self.assertEqual(utils.clear_artist("The Police"), "the police")
        self.assertEqual(utils.clear_artist("Abba, Beetles"), "abba")
        self.assertEqual(utils.clear_artist("Abba & Beetles"), "abba")
        self.assertEqual(utils.clear_artist("Abba and Beetles"), "abba")
        self.assertEqual(utils.clear_artist("Abba feat Beetles"), "abba")

    def test_clear_title(self):
        self.assertEqual(utils.clear_title("Synchronicity II"), "Synchronicity II")
        self.assertEqual(utils.clear_title("Anxiety"), "Anxiety")
        self.assertEqual(utils.clear_title("Anxiety (2025 version)"), "Anxiety")
        self.assertEqual(utils.clear_title("Anxiety - Remix"), "Anxiety")

    def test_calc_score(self):
        title = _random_ascii_alnum(15)
        performer = _random_ascii_alnum(10)
        self.assertEqual(utils.calc_score(title, performer, title, performer), 1)
        self.assertEqual(utils.calc_score(title + "  ", performer, title, performer), 1)
        self.assertEqual(utils.calc_score(title, performer, title.lower(), performer.lower()), 1)
        self.assertEqual(utils.calc_score(title, performer, title.upper(), performer.upper()), 1)
        self.assertGreaterEqual(utils.calc_score(title, performer, title[3:], performer), 0.9)
        self.assertGreaterEqual(utils.calc_score(title, performer, title, performer[2:]), 0.9)
        self.assertAlmostEqual(utils.calc_score(title, "aaa", title, "bbb"), 0.5)
        self.assertAlmostEqual(utils.calc_score("111111", performer, "9999999", performer), 0.5)


if __name__ == "__main__":
    unittest.main()
