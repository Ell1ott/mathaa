import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sort_papers import dest_for, parse_stem  # noqa: E402


class SortTest(unittest.TestCase):
    def test_math_aa_hl(self):
        path = Path(
            "papers/ib/IB PAST PAPERS - YEAR 2/2025 Examination Session/"
            "May 2025 Examination Session/files and resources/Mathematics/"
            "Mathematics_analysis_and_approaches_paper_2_TZ1_HL.pdf"
        )
        dest = dest_for(path)
        self.assertTrue(str(dest).endswith(
            "papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p2-tz1.pdf"
        ))

    def test_markscheme_translation_and_donated_code(self):
        path = Path(
            "papers/ib/IB PAST PAPERS - YEAR 2/2023 Examination Session/DONATED PAPERS M23/"
            "AAHL P1 Zone A.pdf"
        )
        dest = dest_for(path)
        self.assertIn("/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p1-tz1.pdf", str(dest))
        parsed = parse_stem("Biology_paper_2__HL_Spanish_markscheme")
        self.assertEqual(parsed["subject"], "biology")
        self.assertEqual(parsed["level"], "hl")
        self.assertEqual(parsed["lang"], "es")
        self.assertEqual(parsed["role"], "markscheme")

    def test_listening_keeps_course_language(self):
        parsed = parse_stem("Spanish_B_listening_comprehension__HL_Spanish")
        self.assertEqual(parsed["subject"], "spanish-b")
        self.assertEqual(parsed["lang"], "en")
        self.assertEqual(parsed["kind"], "listening")
        self.assertEqual(parsed["level"], "hl")


if __name__ == "__main__":
    unittest.main()
