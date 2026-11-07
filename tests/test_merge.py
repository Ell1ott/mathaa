import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from merge_subjects import plan, tagged_name  # noqa: E402


class MergeTest(unittest.TestCase):
    def test_nicknames_and_booklets(self):
        self.assertEqual(
            plan("mathematics", "math-aahl")[:2],
            ("mathematics", "mathematics-analysis-and-approaches"),
        )
        self.assertEqual(plan("mathematics", "math-aahl")[3], "hl")
        self.assertEqual(
            plan("language-acquisition", "english-b-question-booklet"),
            ("language-acquisition", "english-b", "question-booklet", None),
        )
        self.assertEqual(
            plan("language-literature", "afrikaans-a1")[1],
            "afrikaans-a-literature",
        )
        self.assertEqual(plan("sciences", "biology-tz-b")[2], "tz2")
        self.assertIsNone(plan("mathematics", "mathematics-calculus"))
        self.assertEqual(tagged_name("p2.pdf", "question-booklet"), "p2-question-booklet.pdf")
        self.assertEqual(tagged_name("p1.pdf", "tz2"), "p1-tz2.pdf")


if __name__ == "__main__":
    unittest.main()
