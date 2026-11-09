import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from catalog import build_catalog  # noqa: E402
from serve import economics_catalog, question_bank  # noqa: E402
from transcribe import (  # noqa: E402
    tidy_scheme,
    diagram_rects,
    job_id,
    line_y,
    markdown_from,
    place_figures,
    splice_figures,
    stitch,
    strip_page_furniture,
    tidy_question,
)
from extract import (  # noqa: E402
    apply_folder_session,
    clean_question,
    merge_signals,
    is_markscheme_cover,
    markscheme_questions,
    markscheme_ranges,
    page_kind,
    questions_from_pages,
    resolve_paper,
    signals_from_name,
    split_papers,
    text_layer_ok,
)
from fetch_missing import selected  # noqa: E402
from match import lacks_overlap  # noqa: E402
from sync_refs import parse_topic_page, robots_allows, topic_urls  # noqa: E402

PAGE = """
<h1>1.10 Counting &amp; binomial (HL only)</h1>
<h2>Questions on 1.10, by exam session</h2>
<p class="font-black">November 2025</p>
<span class="font-bold whitespace-nowrap">P2 TZ1</span><span class="truncate opacity-70">Q2</span>
<p class="font-black">November 2024</p>
<span class="font-bold whitespace-nowrap">P2</span><span>Q7</span>
Frequently asked
"""


class CatalogTest(unittest.TestCase):
    def test_sixty_three(self):
        papers = build_catalog()
        self.assertEqual(len(papers), 63)
        ids = [paper["id"] for paper in papers]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("2025-11-p2-tz1", ids)
        self.assertIn("specimen-2021-p1", ids)
        self.assertIn("2024-11-p2", ids)
        self.assertNotIn("2024-05-p1-tz3", ids)


class RefsTest(unittest.TestCase):
    def test_robots_allows_public_index(self):
        robots = "User-agent: *\nDisallow: /api/\nDisallow: /papers/\nDisallow: /*opengraph-image\n"
        self.assertTrue(robots_allows(robots, "/ib-math-aa/past-papers-hl"))
        self.assertFalse(robots_allows(robots, "/papers/secret"))
        self.assertFalse(robots_allows(robots, "/ib-math-aa/past-papers-hl/opengraph-image"))

    def test_parse_citations(self):
        url = "https://www.aimnova.app/ib-math-aa/past-papers-hl/unit-1-number-algebra/counting-binomial"
        refs = parse_topic_page(PAGE, url)
        self.assertEqual(
            [(ref["session"], ref["tz"], ref["question"]) for ref in refs],
            [("November", "TZ1", 2), ("November", None, 7)],
        )
        self.assertEqual(refs[0]["code"], "1.10")
        self.assertEqual(refs[0]["area"], "Number and algebra")

    def test_topic_urls_skip_unit_indexes(self):
        sitemap = """
        <loc>https://www.aimnova.app/ib-math-aa/past-papers-hl/unit-1-number-algebra</loc>
        <loc>https://www.aimnova.app/ib-math-aa/past-papers-hl/unit-1-number-algebra/counting-binomial</loc>
        <loc>https://www.aimnova.app/ib-math-aa/past-papers-hl/november-2025-tz1-paper-2</loc>
        """
        self.assertEqual(
            topic_urls(sitemap),
            ["https://www.aimnova.app/ib-math-aa/past-papers-hl/unit-1-number-algebra/counting-binomial"],
        )


class ExtractTest(unittest.TestCase):
    def test_pymupdf_text_layer_roundtrip(self):
        import pymupdf

        from catalog import ROOT
        from extract import extract_file

        path = ROOT / "papers" / "inbox" / "specimen-2021-p1.pdf"
        document = pymupdf.open()
        first = document.new_page()
        first.insert_text(
            (72, 72),
            "Higher level\nPaper 1\nSpecimen paper\nInstructions to candidates\n"
            + ("working " * 20)
            + "\n1. [Maximum mark: 5]\nFind the mean.\n",
            fontsize=11,
        )
        second = document.new_page()
        second.insert_text(
            (72, 72),
            "(b) The rest continues on this page.\n\n2. [Maximum mark: 4]\nNext question only.\n",
            fontsize=11,
        )
        document.save(path)
        document.close()
        try:
            papers, report = extract_file(path, build_catalog())
        finally:
            path.unlink(missing_ok=True)
        self.assertTrue(report["text_layer"])
        self.assertEqual(report["status"], "present")
        self.assertEqual(papers[0]["id"], "specimen-2021-p1")
        self.assertEqual([q["number"] for q in papers[0]["questions"]], [1, 2])
        self.assertEqual(papers[0]["questions"][0]["page_end"], 2)
        self.assertIn("continues on this page", papers[0]["questions"][0]["text"])

    def test_scan_is_needs_ocr(self):
        import pymupdf

        from catalog import ROOT
        from extract import extract_file

        path = ROOT / "papers" / "inbox" / "2024-11-p2.pdf"
        document = pymupdf.open()
        document.new_page()
        document.save(path)
        document.close()
        try:
            papers, report = extract_file(path, build_catalog())
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(report["status"], "needs_ocr")
        self.assertEqual(papers[0]["id"], "2024-11-p2")
        self.assertEqual(papers[0]["questions"], [])

    def test_filenames(self):
        self.assertEqual(
            signals_from_name("2025-11-p2-tz1.pdf"),
            {"year": 2025, "session": "November", "paper": 2, "tz": "TZ1"},
        )
        self.assertEqual(signals_from_name("n25-p2-tz1.pdf")["year"], 2025)
        named = signals_from_name("Mathematics_analysis_and_approaches_paper_2_TZ1_HL.pdf")
        self.assertEqual(named["paper"], 2)
        self.assertEqual(named["tz"], "TZ1")
        self.assertIsNone(named["year"])
        november = selected(2025, "November")
        self.assertEqual(
            [(row[2], row[3]) for row in november],
            [(1, 1), (1, 3), (2, 1), (2, 3), (3, 1), (3, 3)],
        )

    def test_split_and_span(self):
        pages = [
            "Mathematics\nHigher level\nPaper 1\nSpecimen\nInstructions to candidates\n",
            "1. [Maximum mark: 5]\nFind the mean.\n",
            "(b) The rest of the question continues here.\n\n2. [Maximum mark: 4]\nNext question.\n",
            "Markscheme\nInstructions to examiners\n",
            "Standard level\nPaper 1\nInstructions to candidates\n",
        ]
        chunks = split_papers(pages)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(page_kind(pages[0]), "cover")
        self.assertEqual(page_kind(pages[3]), "ms")
        questions = questions_from_pages(chunks[0]["pages"])
        self.assertEqual([q["number"] for q in questions], [1, 2])
        self.assertIn("continues here", questions[0]["text"])
        self.assertEqual(questions[0]["page_start"], 2)
        self.assertEqual(questions[0]["page_end"], 3)
        self.assertNotIn("Next question", questions[0]["text"])
        self.assertEqual(clean_question("Turn over\n16EP02\nFind x."), "Find x.")
        plural = questions_from_pages([(4, "1.\n[Maximum marks: 28]\nExplore polynomials.\n")])
        self.assertEqual(plural[0]["number"], 1)
        self.assertIn("Explore polynomials", plural[0]["text"])

    def test_markscheme_range_skips_contents(self):
        pages = [
            "CONTENTS\nMathematics higher level\npaper 1 markscheme\n",
            "Markscheme\nHigher level\nPaper 1\n",
            "Instructions to examiners\nAbbreviations\n",
            "Section A\n1.\nTotal [5 marks]\n",
            "Higher level\nPaper 2\nInstructions to candidates\n",
        ]
        self.assertFalse(is_markscheme_cover(pages[0]))
        self.assertTrue(is_markscheme_cover(pages[1]))
        ranges = markscheme_ranges(pages)
        self.assertEqual(ranges, [{"paper": 1, "start": 2, "end": 4}])

    def test_markscheme_questions_ignore_the_worked_examples(self):
        import pymupdf

        document = pymupdf.open()
        cover = document.new_page()
        cover.insert_text((72, 80), "Markscheme")
        cover.insert_text((72, 110), "Higher level")
        cover.insert_text((72, 140), "Paper 1")
        cover.insert_text((48, 700), "1.")
        cover.insert_text((48, 740), "2.")
        notes = document.new_page()
        notes.insert_text((42, 120), "10.")
        notes.insert_text((70, 120), "Presentation of candidate work")
        body = document.new_page()
        body.insert_text((42, 140), "1.")
        body.insert_text((42, 400), "Total [5 marks]")
        body.insert_text((42, 500), "2")
        last = document.new_page()
        last.insert_text((42, 100), "Total [4 marks]")
        last.insert_text((42, 160), "3.")
        ranges = markscheme_ranges([page.get_text("text") for page in document])
        spans = markscheme_questions(document, ranges[0]["start"], ranges[0]["end"])
        document.close()
        self.assertEqual([span["number"] for span in spans], [1, 2, 3])
        self.assertEqual(spans[0]["page_start"], 3)
        self.assertEqual(spans[0]["page_end"], 3)
        self.assertEqual(spans[1]["page_start"], 3)
        self.assertEqual(spans[0]["bottom"], spans[1]["top"])
        self.assertEqual(spans[2]["page_end"], 4)
        self.assertIsNone(spans[2]["bottom"])

    def test_resolve(self):
        catalog = build_catalog()
        signals, conflicts = merge_signals(
            "dp-mathematics-analysis-and-approaches-specimen-papers-en.pdf",
            "Higher level\nPaper 2\nSpecimen\nInstructions to candidates\n",
        )
        resolved = resolve_paper(signals, conflicts, catalog)
        self.assertEqual(resolved["id"], "specimen-2021-p2")
        missing_tz, conflicts = merge_signals("2025-05-p1.pdf", "Higher level\nPaper 1\nMay 2025\n")
        self.assertTrue(resolve_paper({**missing_tz, "hl": True}, conflicts, catalog)["ambiguous"])
        sitting, conflicts = merge_signals(
            "p1-tz1.pdf",
            "Higher level\nPaper 1\n30 October 2023\nZone A afternoon\nZone B afternoon\nZone C afternoon\n"
            "Instructions to candidates\n",
        )
        sitting, conflicts = apply_folder_session(
            Path("hl/2023-11/en/p1-tz1.pdf"), sitting, conflicts
        )
        self.assertEqual(conflicts, [])
        self.assertEqual(resolve_paper({**sitting, "hl": True}, conflicts, catalog)["id"], "2023-11-p1")
        may, conflicts = merge_signals(
            "p1-tz1.pdf",
            "Higher level\nPaper 1\nMay 2023\nZone A afternoon\nZone B afternoon\nZone C afternoon\n"
            "Instructions to candidates\n",
        )
        self.assertEqual(may["tz"], "TZ1")
        self.assertEqual(resolve_paper({**may, "hl": True}, conflicts, catalog)["id"], "2023-05-p1-tz1")

    def test_question_line(self):
        import pymupdf

        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 200), "12.")
        page.insert_text((72, 220), "[Maximum mark: 20]")
        page.insert_text((72, 480), "13.")
        self.assertLess(line_y(page, 12), line_y(page, 13))
        self.assertIsNone(line_y(page, 4))
        document.close()

    def test_text_layer(self):
        self.assertFalse(text_layer_ok(["", "hi"]))
        self.assertTrue(text_layer_ok(["word " * 40]))

    def test_overlap_flag(self):
        self.assertTrue(lacks_overlap("Counting & binomial", "Find the derivative of x squared."))
        self.assertFalse(lacks_overlap("Counting & binomial", "Use the binomial theorem."))


class OpenParserTest(unittest.TestCase):
    def test_tidy_scheme_drops_page_furniture(self):
        cleaned = tidy_scheme(
            "– 8 –\n1. (a) \\(d=-6\\) (M1)\nQuestion 1 continued.\ncontinued…\nTurn over\nTotal [6 marks]\n"
        )
        self.assertIn(r"\(d=-6\)", cleaned)
        self.assertIn("Total [6 marks]", cleaned)
        self.assertNotIn("continued", cleaned.lower())
        self.assertNotIn("Turn over", cleaned)
        self.assertNotIn("glce", tidy_scheme("glce\nEITHER\nA1\n"))
        self.assertIn("EITHER", tidy_scheme("glce\nEITHER\nA1\n"))

    def test_tidy_keeps_one_question(self):
        raw = Path("/Users/elliottfriedrich/github/mathaa/data/vl/2026-05-p2-tz1-q1.md").read_text()
        cleaned = tidy_question(raw, 1)
        self.assertIn("Maximum mark: 7", cleaned)
        self.assertNotIn("Maximum mark: 4", cleaned)
        self.assertNotIn("<table", cleaned)
        self.assertNotIn("Turn over", cleaned)
        self.assertIn("155 ≤ h < 160", cleaned)
        self.assertNotIn("&lt;", cleaned)
        self.assertNotIn("100000", cleaned)
        self.assertEqual(tidy_question(cleaned, 1), cleaned)

    def test_tidy_splits_when_the_mark_is_wrapped(self):
        raw = "3. \\([Maximum mark: 5]\\)\nSolve.\n\n4. [Maximum mark: 7]\nNext question.\n"
        cleaned = tidy_question(raw, 3)
        self.assertIn("Solve.", cleaned)
        self.assertNotIn("Next question", cleaned)

    def test_strip_blank_page_notices_anywhere(self):
        raw = (
            "10. [Maximum mark: 15]\n"
            "Find q.\n\n"
            "Do not write solutions on this page.\n\n"
            "(Question 10 continued)\n\n"
            "(c) Find q - p.\n\n"
            "Please do not write on this page.\n"
            "Answers written on this page\n"
            "will not be marked.\n\n"
            "1\n\n"
            "Please do not write on this page.\n"
            "Answers written on this page will not be marked.\n"
        )
        cleaned = strip_page_furniture(raw)
        self.assertIn("Find q.\n\n(c) Find q - p.", cleaned)
        self.assertIn("(c) Find q - p.", cleaned)
        self.assertNotIn("do not write", cleaned.lower())
        self.assertNotIn("will not be marked", cleaned.lower())
        self.assertNotIn("\n1\n", f"\n{cleaned}\n")
        self.assertEqual(strip_page_furniture(cleaned), cleaned)

    def test_tidy_keeps_a_paper_3_continuation(self):
        raw = Path("/Users/elliottfriedrich/github/mathaa/data/vl/2025-05-p3-tz2-q1.md").read_text()
        cleaned = tidy_question(raw, 1)
        self.assertIn("homogeneous differential", cleaned)
        self.assertIn("partial fractions", cleaned)
        self.assertNotIn("Maximum mark: 27", cleaned)
        self.assertNotIn("Turn over", cleaned)

    def test_markdown_and_job_id(self):
        self.assertEqual(markdown_from({"markdown": " # Q \n"}), "# Q")
        self.assertEqual(markdown_from({"result": {"text": "Hello"}}), "Hello")
        self.assertEqual(job_id({"id": "opj_1"}, None), "opj_1")
        self.assertEqual(job_id({}, "https://api.openparser.dev/jobs/opj_2"), "opj_2")


class FigureTest(unittest.TestCase):
    def test_splice_replaces_placeholders_in_order(self):
        raw = "See.\n\n[Figure: <div></div>]\n\nThen.\n\n[Figure: ]\n\n[Figure: ]\n"
        got = splice_figures(raw, ["/fig/q-1.png", "/fig/q-2.png"])
        self.assertEqual(got, "See.\n\n![](/fig/q-1.png)\n\nThen.\n\n![](/fig/q-2.png)\n\n\n")
        cleaned = tidy_question("6. [Maximum mark: 4]\n" + got, 6)
        self.assertIn("![](/fig/q-1.png)", cleaned)
        self.assertIn("![](/fig/q-2.png)", cleaned)
        self.assertNotIn("[Figure:", cleaned)

    def test_place_puts_a_graph_back_and_drops_its_readout(self):
        text = (
            "The curve passes through the top right corner of each rectangle.\n\n"
            "| x | y |\n| --- | --- |\n| 0 | 0 |\n\n"
            "(i) Write down an expression.\n"
        )
        got = place_figures(
            text,
            ["/fig/q-1.png"],
            ["The curve passes through the top right corner of each rectangle."],
        )
        self.assertIn("![](/fig/q-1.png)", got)
        self.assertNotIn("| x | y |", got)
        self.assertIn("(i) Write down", got)
        again = place_figures(got, ["/fig/q-1.png"], ["The curve passes through the top right corner of each rectangle."])
        self.assertEqual(again.count("![]("), 1)

    def test_place_skips_a_drawing_from_the_next_question(self):
        text = "Prove by contradiction that the inequality holds."
        got = place_figures(text, ["/fig/q-1.png"], ["The following diagram shows parallelogram with"])
        self.assertNotIn("![](", got)

    def test_diagram_rect_ignores_a_hairline(self):
        import pymupdf

        document = pymupdf.open()
        page = document.new_page()
        page.draw_circle((200, 220), 70, color=(0, 0, 0), width=1.2)
        page.draw_line((40, 700), (500, 700), width=0.4)
        found = diagram_rects(page, 50, 780)
        document.close()
        self.assertEqual(len(found), 1)
        self.assertGreater(found[0].height, 55)


class CutTest(unittest.TestCase):
    def test_stitch_stacks_pages(self):
        import pymupdf

        top = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 4, 2))
        top.clear_with(0)
        bottom = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 4, 3))
        bottom.clear_with(255)
        raw = stitch([top, bottom])
        self.assertTrue(raw.startswith(b"\x89PNG"))
        got = pymupdf.Pixmap(raw)
        self.assertEqual((got.width, got.height), (4, 21))
        self.assertEqual(got.pixel(0, 0), (0, 0, 0))
        self.assertEqual(got.pixel(0, 20), (255, 255, 255))


class BankTest(unittest.TestCase):
    def test_slices_sorts_and_maps_topics(self):
        bank = question_bank(
            [
                {
                    "id": "2024-11-p1-q1",
                    "text": "1. [Maximum mark: 5]\nFind it.\n\n2. [Maximum mark: 6]\nNext.\n",
                    "number": 1,
                    "year": 2024,
                    "session": "November",
                    "paper": 1,
                    "tz": None,
                    "topics": [{"code": "5.5", "topic": "Integration", "area": "Calculus"}],
                    "status": "matched",
                    "page_start": 3,
                    "page_end": 3,
                },
                {
                    "id": "2025-05-p2-tz1-q2",
                    "text": "2. [Maximum marks: 8]\nLater.\n",
                    "number": 2,
                    "year": 2025,
                    "session": "May",
                    "paper": 2,
                    "tz": "TZ1",
                    "topics": [{"code": "1.6", "topic": "Proof", "area": "Number and algebra"}],
                    "status": "review",
                    "page_start": 4,
                    "page_end": 5,
                },
            ]
        )
        self.assertEqual([item["i"] for item in bank["qs"]], ["2025-05-p2-tz1-q2", "2024-11-p1-q1"])
        older = bank["qs"][1]
        self.assertEqual(older["t"], "Find it.")
        self.assertEqual(older["m"], 5)
        self.assertTrue(older["v"])
        self.assertFalse(bank["qs"][0]["v"])
        self.assertEqual(bank["qs"][0]["m"], 8)
        self.assertEqual(bank["topics"]["5.5"], ["Integration", "Calculus"])

    def test_page_png_renders_the_asked_page(self):
        import tempfile

        import pymupdf
        from serve import page_count, page_png

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "two.pdf"
            document = pymupdf.open()
            for word in ("one", "two"):
                document.new_page().insert_text((72, 72), word)
            document.save(path)
            document.close()
            self.assertEqual(page_count(path), 2)
            png = page_png(path, 1)
            self.assertTrue(png.startswith(b"\x89PNG"))
            self.assertIsNone(page_png(path, 0))
            self.assertIsNone(page_png(path, 3))
            from serve import thumb_jpeg

            jpg = thumb_jpeg(path, 1)
            self.assertTrue(jpg.startswith(b"\xff\xd8"))
            self.assertLess(len(jpg), len(png))
            self.assertEqual(thumb_jpeg(path, 1), jpg)
            self.assertIsNone(thumb_jpeg(path, 3))

    def test_economics_papers_skip_markschemes_and_other_languages(self):
        root = Path(__file__).resolve().parents[1] / "papers" / "library" / "societies" / "economics"
        if not any(root.rglob("*.pdf")):
            self.skipTest("economics library is not on disk")
        papers, files = economics_catalog(root)
        self.assertGreater(len(papers), 100)
        self.assertEqual(len(papers), len({paper["i"] for paper in papers}))
        self.assertEqual(len(papers), len(files))
        self.assertTrue(all(paper["u"] == "econ" and paper["l"] for paper in papers))
        self.assertNotIn("markscheme", " ".join(path.name for path in files.values()))
        self.assertTrue(all(path.parent.name == "en" for path in files.values()))
        sample = next(paper for paper in papers if paper["l"] == "hl" and paper["z"] == "TZ1")
        self.assertTrue(sample["i"].startswith("econ-hl-"))
        self.assertIn("-p", sample["i"])

    def test_browser_keeps_economics_out_of_math(self):
        script = r"""
import { prepare, matchesPaper } from './web/src/bank.js'
const bank = prepare({ qs: [], ps: [{ i: 'econ-hl-2024-05-p1-tz1', y: 2024, s: 'May', p: 1, z: 'TZ1', l: 'hl' }] })
if (bank.questions.length || bank.papers.length !== 1 || bank.papers[0].u !== 'econ' || bank.papers[0].n !== 0) process.exit(1)
const S = { sub: 'math', p: new Set(), y: new Set(), s: new Set(), l: new Set() }
if (matchesPaper(bank.papers[0], S, null, '')) process.exit(2)
S.sub = 'econ'
if (!matchesPaper(bank.papers[0], S, null, 'hl 2024')) process.exit(3)
S.l.add('sl')
if (matchesPaper(bank.papers[0], S, null, '')) process.exit(4)
"""
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run(["node", "--input-type=module", "-e", script], cwd=root, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr or run.stdout)


class TemplateTableTest(unittest.TestCase):
    def test_pipe_tables_become_html(self):
        script = r"""
import { fmt } from './web/src/format.js'
const spaced = "| x | y |\n\n| --- | --- |\n\n| 0 | 4 |\n\n| π | 3.2 |\n\n| 2π | 2 |";
const html = fmt(spaced);
if (!html.includes("<th>x</th>") || !html.includes("<th>y</th>")) process.exit(1);
if (!html.includes("<td>π</td>") || !html.includes("<td>2π</td>") || !html.includes("<td>3.2</td>")) process.exit(2);
if ((html.match(/<table>/g) || []).length !== 1) process.exit(3);
const math = fmt("| eq | roots |\n| --- | --- |\n| \\(x^2 + 1 = 0\\) | \\(\\{1, 0, 1\\}\\) |\n\nNext line.");
if (!math.includes("<td>\\(x^2 + 1 = 0\\)</td>")) process.exit(4);
if (!math.includes("<p>Next line.</p>")) process.exit(5);
const open = fmt("| Score | Frequency\n| --- | ---\n| 1 | 1 |");
if (!open.includes("<th>Frequency</th>") || !open.includes("<td>1</td>")) process.exit(6);
if (fmt("Use |x| here.\n\nNot a table.").includes("<table>")) process.exit(7);
"""
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run(["node", "--input-type=module", "-e", script], cwd=root, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr or run.stdout)

    def test_filters_roundtrip_in_the_url(self):
        script = r"""
import { filtersFrom, filtersTo } from './web/src/filters.js'
import { chunk, orderPapers, orderQuestions, paperBucket, questionBucket } from './web/src/bank.js'
const search = "?p=1,3&y=2024&s=May,November&m=0,3&a=Calculus,Functions&t=1.1,5.5&saved=1&ver=1&q=Hello+World&sort=mh";
const F = filtersFrom(search);
const back = filtersTo(F, F.q, F.sort, "/");
const again = filtersFrom(back.slice(back.indexOf("?")));
for (const key of ["p", "y", "s", "m", "a", "t"]) {
  const left = [...F[key]].join(",");
  const right = [...again[key]].join(",");
  if (left !== right) { console.error(key, left, right); process.exit(1); }
}
if (again.q !== "Hello World" || again.sort !== "mh" || !again.saved || !again.ver || again.sub !== "math") process.exit(2);
if (filtersTo({p:new Set(),y:new Set(),s:new Set(),m:new Set(),a:new Set(),t:new Set(),saved:false,ver:false}, "", "new", "/") !== "/") process.exit(3);
const econ = filtersFrom("?sub=econ&l=hl,sl&browse=questions&sort=mh");
if (econ.sub !== "econ" || econ.browse !== "papers" || econ.sort !== "mh") process.exit(8);
if ([...econ.l].join(",") !== "hl,sl") process.exit(9);
const econUrl = filtersTo(econ, "", econ.sort, "/");
if (!econUrl.includes("sub=econ") || !econUrl.includes("l=hl")) process.exit(10);
if (filtersFrom("?sort=nope&m=no&saved=0").sort !== "new") process.exit(4);
if (filtersFrom("?sort=nope&m=no&saved=0").m.size) process.exit(5);
if (filtersFrom("").group !== "sub") process.exit(11);
if (filtersFrom("?browse=papers").group !== "year") process.exit(12);
if (filtersFrom("?g=nope").group !== "sub") process.exit(13);
if (filtersTo(filtersFrom(""), "", "new", "/") !== "/") process.exit(14);
const grouped = filtersFrom("?g=year");
if (grouped.group !== "year" || !filtersTo(grouped, "", grouped.sort, "/").includes("g=year")) process.exit(15);
const econLevel = filtersFrom("?sub=econ&g=level");
if (econLevel.group !== "level" || econLevel.browse !== "papers") process.exit(16);
const topics = { '1.2': ['Exponents', 'Number and algebra'], '1.10': ['Binomial', 'Number and algebra'], '5.10': ['Integration', 'Calculus'] }
const qs = [
  { c: ['5.10'], ar: ['Calculus'], y: 2024, p: 1, s: 'May', ord: 0, m: 5 },
  { c: ['1.10'], ar: ['Number and algebra'], y: 2025, p: 2, s: 'November', ord: 1, m: 8 },
  { c: ['1.2'], ar: ['Number and algebra'], y: 2023, p: 1, s: 'May', ord: 2, m: 3 },
  { c: [], ar: [], y: 2022, p: 1, s: 'May', ord: 3, m: 1 },
]
const ordered = orderQuestions(qs, 'sub', 'new', topics)
if (ordered.map(q => q.c[0] || '').join(',') !== '1.2,1.10,5.10,') process.exit(18);
const buckets = chunk(ordered, q => questionBucket(q, 'sub', topics))
if (buckets[0].label !== 'Exponents' || buckets[0].code !== '1.2' || buckets[3].label !== 'Other') process.exit(19);
if (orderQuestions(qs, 'year', 'old', topics).map(q => q.y).join(',') !== '2022,2023,2024,2025') process.exit(20);
const papers = orderPapers([
  { y: 2024, s: 'November', p: 2, z: '', l: 'sl' },
  { y: 2025, s: 'May', p: 1, z: '', l: 'hl' },
  { y: 2025, s: 'May', p: 2, z: 'TZ1', l: 'hl' },
], 'year', 'new', 'math')
if (papers.map(p => p.y + '-' + p.p).join(',') !== '2025-1,2025-2,2024-2') process.exit(21);
const yearGroups = chunk(papers, p => paperBucket(p, 'year'))
if (yearGroups.length !== 2 || yearGroups[0].label !== '2025' || yearGroups[0].rows.length !== 2) process.exit(22);
"""
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run(["node", "--input-type=module", "-e", script], cwd=root, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr or run.stdout)


if __name__ == "__main__":
    unittest.main()
