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

    def test_calc_score_rnd(self):
        title = _random_ascii_alnum(15)
        performer = _random_ascii_alnum(10)
        self.assertEqual(utils.calc_score(title, performer, title, performer), 1, "same string")
        self.assertEqual(
            utils.calc_score(title + "  ", performer, title, performer), 1, "with more space"
        )
        self.assertEqual(
            utils.calc_score(title, performer, title.upper(), performer.upper()), 1, "uppercase"
        )
        self.assertEqual(
            utils.calc_score(title, performer, title.lower(), performer.lower()), 1, "lowercase"
        )
        self.assertGreaterEqual(
            utils.calc_score(_random_ascii_alnum(3) + " " + title, performer, title, performer),
            0.9,
            "almost the same title",
        )
        self.assertGreaterEqual(
            utils.calc_score(title, performer, title, performer + " " + _random_ascii_alnum(3)),
            0.9,
            "almost the same performer",
        )
        self.assertAlmostEqual(
            utils.calc_score(title, "aaaaaaaaaaaa", title, "bbbbbbbbb"),
            0.5,
            0,
            "different performer",
        )
        self.assertAlmostEqual(
            utils.calc_score("111111111", performer, "9999999999", performer),
            0.5,
            0,
            "different title",
        )
        self.assertGreater(
            utils.calc_score(
                title,
                performer[5:] + " " + performer[:5],
                title + " " + performer[:5],
                performer[5:],
            ),
            0.7,
            "performed splitted",
        )

    def test_calc_score_man(self):
        self.assertEqual(
            utils.calc_score("Bonnie and Clyde", "Beyoncé", "Bonnie and Clyde", "Beyonce"),
            1,
            "Ascii normalization",
        )
        self.assertGreater(
            utils.calc_score("Bonnie and Clyde", "JAY-Z", "Bonnie & Clyde", "JAY-Z"),
            0.9,
            "and to &",
        )
        self.assertGreater(
            utils.calc_score(
                "Bonnie and Clyde (feat. Beyonce)", "JAY-Z", "Bonnie and Clyde", "JAY-Z, Beyonce"
            ),
            0.7,
            "Bonnie and Clyde - JAY-Z, Beyonce",
        )
        self.assertLess(
            utils.calc_score("Waterfall", "James Hype", "Waterfall", "TLC"),
            0.6,
            "Waterfall",
        )
        self.assertGreater(
            utils.calc_score(
                "Waterfalls (feat. Sam Harper & Bobby Harvey)",
                "James Hype",
                "Waterfall",
                "James Hype, Sam Harper, Bobby Harvey",
            ),
            0.5,
            "Waterfall",
        )


if __name__ == "__main__":
    unittest.main()
