"""Fill question text with Markdown from the hosted PaddleOCR-VL-1.6 API.

PyMuPDF still decides the question and its PDF pages. This only rewrites the wording.
Scans stay as they are: a text-layer copy of the same paper is preferred.
shortcut: part marks such as [3] are sometimes dropped, keep the PDF page for those.
shortcut: a cache file of 20 bytes or less is sent again, so a short successful parse is billed twice.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from catalog import ROOT
from extract import markscheme_questions, markscheme_ranges

CACHE = ROOT / "data" / "vl"
API = "https://api.openparser.dev"
MODEL = "paddleocr-vl-1.6"
SOURCE = "paddleocr-vl-1.6"
NUMBER_LINE = re.compile(r"^(\d{1,2})\.$")
WORKERS = 8


def line_y(page, number: int) -> float | None:
    lines: dict[tuple, list] = {}
    for word in page.get_text("words"):
        lines.setdefault((word[5], word[6]), []).append(word)
    for key in sorted(lines):
        bits = lines[key]
        if NUMBER_LINE.fullmatch(bits[0][4]) and int(bits[0][4][:-1]) == number:
            return bits[0][1]
    return None


def bands(doc, question: dict, next_question: dict | None):
    """Yield (page, top, bottom) covering one question and not the next."""
    start, end = question["page_start"], question["page_end"]
    for page_no in range(start, end + 1):
        page = doc[page_no - 1]
        top = 56
        # Footer band holds the barcode and "Turn over", below the answer lines.
        bottom = page.rect.y1 - 72
        if page_no == start:
            found = line_y(page, question["number"])
            if found is not None:
                top = max(0, found - 6)
        if page_no == end:
            cut = bottom
            if next_question and next_question["page_start"] == page_no:
                nxt = line_y(page, next_question["number"])
                # The next question often starts just under the header. A wide gap
                # here kept the whole page, including that question.
                if nxt and nxt > top + 4:
                    cut = nxt - 6
            refs = page.search_for("References:")
            if refs and refs[0].y0 > top + 4:
                cut = min(cut, refs[0].y0 - 6)
            bottom = cut
        if bottom - top < 8:
            continue
        yield page, top, bottom


def clips(doc, question: dict, next_question: dict | None) -> list:
    import pymupdf

    return [
        page.get_pixmap(dpi=140, clip=pymupdf.Rect(0, top, page.rect.x1, bottom))
        for page, top, bottom in bands(doc, question, next_question)
    ]


def _join(rects: list) -> list:
    """Union rectangles that sit within DIAGRAM_GAP of each other."""
    parent = list(range(len(rects)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, left in enumerate(rects):
        for j in range(i + 1, len(rects)):
            right = rects[j]
            if (
                left.x1 + DIAGRAM_GAP < right.x0
                or right.x1 + DIAGRAM_GAP < left.x0
                or left.y1 + DIAGRAM_GAP < right.y0
                or right.y1 + DIAGRAM_GAP < left.y0
            ):
                continue
            parent[find(j)] = find(i)
    boxes: dict[int, object] = {}
    for i, rect in enumerate(rects):
        root = find(i)
        boxes[root] = rect if root not in boxes else boxes[root] | rect
    return list(boxes.values())


def diagram_rects(page, top: float, bottom: float) -> list:
    """Bounding boxes of vector diagrams in the question column.

    shortcut: a cluster that overlaps a line of body text is dropped, so a
    figure drawn inside a sentence is skipped. Delete data/figs after changing this.
    """
    import pymupdf

    rects = []
    limit = pymupdf.Rect(36, top, CONTENT_RIGHT, bottom)
    for drawing in page.get_drawings():
        rect = pymupdf.Rect(drawing["rect"]) & limit
        if rect.is_empty or rect.width < 1.2 or rect.height < 1.2:
            continue
        if min(rect.width, rect.height) < 1.2 and max(rect.width, rect.height) > 140:
            continue
        rects.append(rect)
    for info in page.get_image_info():
        rect = pymupdf.Rect(info["bbox"]) & pymupdf.Rect(36, top, page.rect.x1 - 36, bottom)
        if rect.width > 40 and rect.height > 40:
            rects.append(rect)
    found = []
    for rect in _join(rects):
        if rect.width * rect.height < 5000 or rect.height < 55 or rect.width < 55:
            continue
        overlap = 0.0
        for block in page.get_text("blocks"):
            if block[6] != 0:
                continue
            words = " ".join(block[4].split())
            if len(words) < 24:
                continue
            shared = rect & pymupdf.Rect(block[:4])
            if not shared.is_empty:
                overlap += shared.get_area()
        if overlap > 0.25 * rect.get_area():
            continue
        for block in page.get_text("blocks"):
            if block[6] != 0:
                continue
            words = " ".join(block[4].split())
            if len(words) > 16:
                continue
            label = pymupdf.Rect(block[:4])
            near = pymupdf.Rect(rect.x0 - 10, rect.y0 - 8, rect.x1 + 10, rect.y1 + 8)
            if label.intersects(near) and label.x1 < CONTENT_RIGHT + 24:
                rect |= label
        rect = pymupdf.Rect(rect.x0 - 4, rect.y0 - 4, rect.x1 + 4, rect.y1 + 4) & page.rect
        if rect.width > 20 and rect.height > 20:
            found.append(rect)
    # Labels can pull two halves of one figure into overlapping boxes.
    found = _join([pymupdf.Rect(rect) for rect in found])
    found.sort(key=lambda rect: (rect.y0, rect.x0))
    return found


def splice_figures(text: str, urls: list[str]) -> str:
    """Replace empty `[Figure:]` lines with diagram images, in reading order."""
    pending = list(urls)

    def repl(_match: re.Match) -> str:
        if not pending:
            return ""
        return f"![]({pending.pop(0)})"

    return FIGURE.sub(repl, text)


def splice_question(text: str, number: int, urls: list[str]) -> str:
    """Splice diagrams into this question only, leaving a following question untouched."""
    bounds = _question_bounds(text, number)
    if bounds is None:
        return splice_figures(text, urls)
    start, end = bounds
    return text[:start] + splice_figures(text[start:end], urls) + text[end:]


def figure_urls(key: str) -> list[str]:
    paths = sorted(FIGS.glob(f"{key}-*.png"), key=lambda path: int(path.stem.rsplit("-", 1)[-1]))
    return [f"/fig/{path.name}" for path in paths]


_WORD = re.compile(r"[A-Za-z]{4,}")
# A graph OCR turned into a markdown table sits directly under the figure sentence.
_READOUT = re.compile(
    r"\A(?:[ \t]*\n)+[ \t]*(?:diagram not to scale[ \t]*\n+)?(?:\|[^\n]*\n){2,}",
    re.I,
)


def _anchor_end(text: str, line: str, start: int) -> int | None:
    """End offset of the PDF line above a figure, once it shows up in the question."""
    words = _WORD.findall(line)[-4:]
    if len(words) < 3:
        return None
    pat = r"\b" + r"\b.{0,120}?\b".join(re.escape(word) for word in words) + r"\b"
    match = re.search(pat, text[start:], re.I | re.S)
    if match is None:
        return None
    return start + match.end()


def _insert_figure(text: str, pos: int, url: str) -> str:
    end = text.find("\n", pos)
    if end < 0:
        end = len(text)
    rest = text[end:]
    near = text[max(0, end - 300) : end]
    readout = _READOUT.match(rest)
    if readout and not re.search(r"\btable\b", near, re.I):
        rest = "\n" + rest[readout.end() :].lstrip("\n")
    return text[:end] + f"\n\n![]({url})\n" + rest


def place_figures(text: str, urls: list[str], anchors: list[str]) -> str:
    """Put back figures OCR never marked, using the PDF line printed above each one.

    shortcut: a figure is skipped when that line is not in this question's text,
    which also drops a drawing that belongs to the next question. Re-OCR to place it.
    """
    cursor = 0
    spots = []
    for url, line in zip(urls, anchors):
        if url in text:
            continue
        pos = _anchor_end(text, line, cursor)
        if pos is None:
            continue
        spots.append((pos, url))
        cursor = pos
    if not spots:
        return text
    for pos, url in reversed(spots):
        text = _insert_figure(text, pos, url)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _anchor_line(page, rect) -> str:
    rows: dict[tuple, list] = {}
    for word in page.get_text("words"):
        rows.setdefault((round(word[1]), word[5], word[6]), []).append(word)
    best = ""
    for key in sorted(rows):
        bits = sorted(rows[key], key=lambda word: word[0])
        y1 = max(bit[3] for bit in bits)
        x0 = min(bit[0] for bit in bits)
        if y1 > rect.y0 + 4 or x0 > CONTENT_RIGHT:
            continue
        line = " ".join(bit[4] for bit in bits)
        if len(_WORD.findall(line)) >= 3:
            best = line
    return best


def restore_figures(papers: list[dict]) -> tuple[int, int]:
    """Crop vector diagrams OCR replaced with text, and splice the image in."""
    import pymupdf

    FIGS.mkdir(parents=True, exist_ok=True)
    questions_fixed = figures = 0
    for paper in papers:
        questions = paper.get("questions") or []
        path = ROOT / paper.get("file", "")
        if not questions or not path.is_file():
            continue
        doc = pymupdf.open(path)
        try:
            for index, question in enumerate(questions):
                key = question.get("id") or _key(paper, question)
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
                    continue
                nxt = questions[index + 1] if index + 1 < len(questions) else None
                cursor = 0
                kept = []
                text = question.get("text") or ""
                for page, top, bottom in bands(doc, question, nxt):
                    for rect in diagram_rects(page, top, bottom):
                        line = _anchor_line(page, rect)
                        pos = _anchor_end(text, line, cursor)
                        if pos is None:
                            continue
                        kept.append((page, rect, line))
                        cursor = pos
                if not kept:
                    continue
                urls = [f"/fig/{key}-{nth}.png" for nth in range(1, len(kept) + 1)]
                if all(url in text for url in urls):
                    continue
                for nth, (page, rect, _line) in enumerate(kept, 1):
                    dest = FIGS / f"{key}-{nth}.png"
                    if not dest.is_file():
                        page.get_pixmap(dpi=140, clip=rect).save(dest)
                updated = place_figures(text, urls, [line for _page, _rect, line in kept])
                if updated != text:
                    question["text"] = updated
                    questions_fixed += 1
                    figures += sum(1 for url in urls if url in updated)
        finally:
            doc.close()
    return questions_fixed, figures


def render_figures(papers: list[dict]) -> None:
    """Write data/figs/<id>-<n>.png for each diagram under a `[Figure:]` placeholder.

    shortcut: a PNG newer than its PDF is kept even if the crop code changed.
    """
    import pymupdf

    FIGS.mkdir(parents=True, exist_ok=True)
    wanted: set[str] = set()
    for paper in papers:
        questions = paper.get("questions") or []
        path = ROOT / paper.get("file", "")
        if not questions or not path.is_file():
            continue
        doc = pymupdf.open(path)
        try:
            source_mtime = path.stat().st_mtime
            for index, question in enumerate(questions):
                key = _key(paper, question)
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
                    continue
                cache = CACHE / f"{key}.md"
                if not cache.is_file() or "[Figure:" not in _keep_question(cache.read_text(), question["number"]):
                    continue
                existing = list(FIGS.glob(f"{key}-*.png"))
                if existing and min(item.stat().st_mtime for item in existing) >= source_mtime:
                    wanted.update(item.name for item in existing)
                    continue
                nxt = questions[index + 1] if index + 1 < len(questions) else None
                nth = 0
                for page, top, bottom in bands(doc, question, nxt):
                    for rect in diagram_rects(page, top, bottom):
                        nth += 1
                        name = f"{key}-{nth}.png"
                        page.get_pixmap(dpi=140, clip=rect).save(FIGS / name)
                        wanted.add(name)
        finally:
            doc.close()
    for old in FIGS.glob("*.png"):
        if old.name not in wanted:
            old.unlink()


CUTS = ROOT / "data" / "cuts"
SCHEMES = ROOT / "data" / "schemes"
FIGS = ROOT / "data" / "figs"
FIGURE = re.compile(r"(?m)^[ \t]*\[Figure:.*?\][ \t]*$")
# Answer lines sit in the right margin. Diagrams stay in the question column.
CONTENT_RIGHT = 520
DIAGRAM_GAP = 22


def stitch(pages: list) -> bytes:
    """Stack page crops into one PNG. One page is returned as-is."""
    import pymupdf

    if len(pages) == 1:
        return pages[0].tobytes("png")
    gap = 16
    width = max(page.width for page in pages)
    height = sum(page.height for page in pages) + gap * (len(pages) - 1)
    out = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height))
    out.clear_with(255)
    y = 0
    for page in pages:
        page.set_origin(0, y)
        out.copy(page, pymupdf.IRect(0, y, page.width, y + page.height))
        y += page.height + gap
    return out.tobytes("png")


def write_cuts(questions: list[dict]) -> tuple[int, int]:
    """Write data/cuts/<id>.png for each question. Skip a file that is already newer than its PDF.

    shortcut: a newer PNG is kept even if the crop code changed, delete data/cuts to rebuild.
    """
    import pymupdf
    from collections import defaultdict

    CUTS.mkdir(parents=True, exist_ok=True)
    by_file: dict[str, list[dict]] = defaultdict(list)
    for question in questions:
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", question["id"]):
            by_file[question["file"]].append(question)
    written = skipped = 0
    for rel, group in by_file.items():
        path = ROOT / rel
        if not path.is_file():
            continue
        group.sort(key=lambda item: (item["page_start"], item["number"]))
        doc = pymupdf.open(path)
        try:
            source_mtime = path.stat().st_mtime
            for index, question in enumerate(group):
                dest = CUTS / f"{question['id']}.png"
                if dest.is_file() and dest.stat().st_mtime >= source_mtime:
                    skipped += 1
                    continue
                nxt = group[index + 1] if index + 1 < len(group) else None
                pages = clips(doc, question, nxt)
                if not pages:
                    continue
                dest.write_bytes(stitch(pages))
                written += 1
        finally:
            doc.close()
    wanted = {f"{question['id']}.png" for question in questions}
    for old in CUTS.glob("*.png"):
        if old.name not in wanted:
            old.unlink()
    return written, skipped


def scheme_clips(doc, span: dict) -> list:
    """Crop one markscheme question. `bottom` is the next question's top."""
    import pymupdf

    clips = []
    for page_no in range(span["page_start"], span["page_end"] + 1):
        page = doc[page_no - 1]
        top = 56
        bottom = page.rect.y1 - 72
        if page_no == span["page_start"]:
            top = max(0, span["top"] - 6)
        if page_no == span["page_end"] and span["bottom"] is not None:
            bottom = min(bottom, span["bottom"] - 6)
        if bottom - top < 8:
            continue
        clips.append(page.get_pixmap(dpi=140, clip=pymupdf.Rect(0, top, page.rect.x1, bottom)))
    return clips


def each_scheme(questions: list[dict]):
    """Yield (document, question, span, pdf) for every question with a markscheme."""
    import pymupdf
    from collections import defaultdict

    by_file: dict[str, list[dict]] = defaultdict(list)
    for question in questions:
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", question["id"]):
            by_file[question["file"]].append(question)
    for rel, group in by_file.items():
        question_pdf = ROOT / rel
        sibling = question_pdf.with_name(question_pdf.stem + "-markscheme.pdf")
        source = sibling if sibling.is_file() else question_pdf
        if not source.is_file():
            continue
        doc = pymupdf.open(source)
        try:
            ranges = markscheme_ranges([page.get_text("text") for page in doc])
            if sibling.is_file() and not ranges:
                ranges = [{"paper": None, "start": 1, "end": doc.page_count}]
            by_paper: dict[int | None, dict[int, dict]] = {}
            for item in ranges:
                by_paper[item["paper"]] = {
                    span["number"]: span
                    for span in markscheme_questions(doc, item["start"], item["end"])
                }
            for question in group:
                span = by_paper.get(question["paper"], {}).get(question["number"])
                if span is None:
                    span = by_paper.get(None, {}).get(question["number"])
                if span is not None:
                    yield doc, question, span, source
        finally:
            doc.close()


def write_schemes(questions: list[dict]) -> tuple[int, int]:
    """Write data/schemes/<id>.png from the markscheme paired with each paper.

    shortcut: a newer PNG is kept even if the crop changed, delete data/schemes to rebuild.
    """
    SCHEMES.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    kept: set[str] = set()
    for doc, question, span, source in each_scheme(questions):
        dest = SCHEMES / f"{question['id']}.png"
        kept.add(dest.name)
        if dest.is_file() and dest.stat().st_mtime >= source.stat().st_mtime:
            skipped += 1
            continue
        pages = scheme_clips(doc, span)
        if not pages:
            kept.discard(dest.name)
            continue
        dest.write_bytes(stitch(pages))
        written += 1
    for old in SCHEMES.glob("*.png"):
        if old.name not in kept:
            old.unlink()
    return written, skipped


def _key(paper: dict, question: dict) -> str:
    if paper.get("id"):
        base = paper["id"]
    else:
        base = Path(paper["file"]).as_posix().replace("/", "-").removesuffix(".pdf")
    return f"{base}-q{question['number']}"


def api_key() -> str:
    found = os.environ.get("OPENPARSER_API_KEY", "").strip()
    if found:
        return found
    path = ROOT / ".env"
    if not path.is_file():
        return ""
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == "OPENPARSER_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def markdown_from(body: dict) -> str:
    result = body.get("result") if isinstance(body.get("result"), dict) else body
    return (result.get("markdown") or result.get("text") or "").strip()


HEADER = re.compile(
    r"(?m)^(?:#{1,6}[ \t]*)*(\d{1,2})\.\s*\\?\(?\s*\[Maximum marks?\s*:",
    re.I,
)
BOILER = re.compile(
    r"^(?:turn over|please turn over|please do not write on this page\.?|"
    r"answers written on this page(?: will not be marked)?\.?|"
    r"will not be marked\.?|"
    r"do\b.*\bnot\b.*write solutions on this page\.?|"
    r"disclaimer:?|references:?|"
    r"©\s*international baccalaureate.*|"
    r"content used in ib assessments\b.*|"
    r"section [ab]|"
    r"answer all questions in the answer booklet provided\..*|"
    r"\(this question continues on the following page\)|"
    r"\(question\s+\d+\s+continued\)|"
    r"\[figure:.*\])$",
    re.I,
)
TABLE = re.compile(r"<table\b[^>]*>.*?</table>", re.I | re.S)
ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
CELL = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.I | re.S)
TAG = re.compile(r"<[^>]+>")


def _question_bounds(text: str, number: int) -> tuple[int, int] | None:
    hits = list(HEADER.finditer(text))
    if not hits or not number:
        return None
    start = next((hit.start() for hit in hits if int(hit.group(1)) == number), None)
    if start is None:
        return None
    end = next(
        (hit.start() for hit in hits if hit.start() > start and int(hit.group(1)) != number),
        len(text),
    )
    return start, end


def _keep_question(text: str, number: int) -> str:
    bounds = _question_bounds(text, number)
    if bounds is None:
        return text
    start, end = bounds
    return text[start:end]


def _cell_text(raw: str) -> str:
    text = html.unescape(TAG.sub("", raw))
    return re.sub(r"\s+", " ", text).strip()


def _table(raw: str) -> str:
    rows = [[_cell_text(cell) for cell in CELL.findall(row)] for row in ROW.findall(raw)]
    rows = [row for row in rows if any(row)]
    flat = [cell for row in rows for cell in row]
    blob = " ".join(flat)
    years = sum(1 for cell in flat if re.fullmatch(r"(?:19|20)\d{2}", cell))
    filled = [cell for cell in flat if cell]
    heads = " ".join(rows[0]).lower() if rows else ""
    answer_grid = any(re.fullmatch(r"[01]{8,}", cell) for cell in filled)
    invented = bool(re.search(r"\b(category|element)\b", heads) and re.search(r"\bvalue\b", heads))
    if not flat or re.search(r"\d{30,}", blob) or years >= 8 or answer_grid or invented:
        return ""
    if not any(re.search(r"[A-Za-z0-9]", cell) for cell in flat):
        return ""
    width = max(len(row) for row in rows)
    lines = []
    for index, row in enumerate(rows):
        padded = row + [""] * (width - len(row))
        lines.append("| " + " | ".join(cell.replace("|", "/") for cell in padded) + " |")
        if index == 0:
            lines.append("| " + " | ".join("---" for _ in padded) + " |")
    return "\n" + "\n".join(lines) + "\n"


def _plain_line(line: str) -> str:
    stripped = re.sub(r"^(?:#{1,6}\s*)+", "", line.strip())
    stripped = re.sub(r"</?div\b[^>]*>", "", stripped, flags=re.I)
    return re.sub(r"[ \t]+", " ", stripped).strip()


def _furniture_mask(lines: list[str]) -> list[bool]:
    drop = [bool(line and (BOILER.match(line) or re.fullmatch(r"[0-9 ]{40,}", line))) for line in lines]

    def neighbor(index: int, step: int) -> int:
        cursor = index + step
        while 0 <= cursor < len(lines) and not lines[cursor]:
            cursor += step
        return cursor

    for index, line in enumerate(lines):
        if not re.fullmatch(r"\d{1,2}", line):
            continue
        prev, nxt = neighbor(index, -1), neighbor(index, 1)
        prev_hit = prev >= 0 and drop[prev]
        next_hit = nxt < len(lines) and drop[nxt]
        if (prev_hit and (next_hit or nxt >= len(lines))) or (next_hit and prev < 0):
            drop[index] = True
    return drop


def strip_page_furniture(text: str) -> str:
    """Drop blank-page notices wherever they sit, keeping the question lines as written."""
    raw = text.splitlines()
    drop = _furniture_mask([_plain_line(line) for line in raw])
    if not any(drop):
        return text
    kept = [line for line, gone in zip(raw, drop) if not gone]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


SCHEME_DROP = re.compile(
    r"^(?:[–—-]\s*\d+\s*[–—-]|question\s+\d+\s+continued\.?|continued(?:…|\.{3})?)$",
    re.I,
)


SCHEME_WORD = {
    "ag",
    "and",
    "as",
    "either",
    "ft",
    "hence",
    "if",
    "let",
    "note",
    "or",
    "show",
    "so",
    "then",
    "to",
}


def tidy_scheme(text: str) -> str:
    """Markscheme markdown without page numbers and continuation lines."""
    kept = []
    for line in text.splitlines():
        plain = _plain_line(line)
        if not plain or SCHEME_DROP.match(plain) or BOILER.match(plain):
            continue
        # A short letter-only line is usually a misread header, not a mark.
        if re.fullmatch(r"[A-Za-z]{1,8}", plain) and plain.lower() not in SCHEME_WORD:
            continue
        kept.append(plain)
    return "\n".join(kept).strip()


def tidy_question(text: str, number: int) -> str:
    """One question, without the next question, answer grids, or page furniture."""
    text = _keep_question(text, number)
    text = TABLE.sub(lambda match: _table(match.group(0)), text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = html.unescape(TAG.sub("", text))
    lines = [_plain_line(line) for line in text.splitlines()]
    kept = []
    blank = False
    for line, gone in zip(lines, _furniture_mask(lines)):
        if gone:
            if kept and not blank:
                kept.append("")
                blank = True
            continue
        kept.append(line)
        blank = False
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def job_id(body: dict, location: str | None) -> str:
    for name in ("id", "job_id"):
        if isinstance(body.get(name), str):
            return body[name]
    job = body.get("job")
    if isinstance(job, dict) and isinstance(job.get("id"), str):
        return job["id"]
    if location:
        return location.rstrip("/").rsplit("/", 1)[-1]
    raise RuntimeError("parse was accepted without a job id")


def _request(method: str, url: str, key: str, data: bytes | None = None, headers: dict | None = None) -> tuple[int, dict, str | None]:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            raw = response.read()
            location = response.headers.get("Location")
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read()
        location = error.headers.get("Location")
        status = error.code
        if status == 429 or status >= 500:
            wait = error.headers.get("Retry-After")
            raise _Retry(status, float(wait) if wait and wait.isdigit() else 2)
    if not raw:
        return status, {}, location
    return status, json.loads(raw), location


class _Retry(Exception):
    def __init__(self, status: int, wait: float) -> None:
        self.status = status
        self.wait = wait


def _call(method: str, url: str, key: str, data: bytes | None = None, headers: dict | None = None) -> tuple[int, dict, str | None]:
    for attempt in range(6):
        try:
            return _request(method, url, key, data, headers)
        except _Retry as retry:
            if attempt == 5:
                raise RuntimeError(f"OpenParser returned {retry.status}") from None
            time.sleep(retry.wait)
    raise RuntimeError("OpenParser request failed")


def parse_image(path: Path, key: str) -> str:
    boundary = uuid.uuid4().hex
    request = json.dumps({"ocr_model": MODEL, "output_format": "openparser@1"}).encode()
    file_bytes = path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="request"\r\n',
            b"Content-Type: application/json\r\n\r\n",
            request,
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
            b"Content-Type: image/png\r\n\r\n",
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    status, payload, location = _call(
        "POST",
        f"{API}/parse",
        key,
        body,
        {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Idempotency-Key": uuid.uuid4().hex,
        },
    )
    if status == 202:
        payload = _wait(job_id(payload, location), key)
    elif status != 200:
        raise RuntimeError(f"OpenParser parse failed ({status})")
    return markdown_from(payload)


def _wait(job: str, key: str) -> dict:
    for _ in range(90):
        status, payload, _ = _call("GET", f"{API}/jobs/{job}", key)
        if status != 200:
            raise RuntimeError(f"OpenParser job {job} failed ({status})")
        state = payload.get("status")
        if state == "succeeded":
            return payload
        if state in {"failed", "indeterminate"}:
            raise RuntimeError(f"OpenParser job {job} {state}")
        time.sleep(2)
    raise RuntimeError(f"OpenParser job {job} timed out")


def _one(images: list[Path], dest: Path, key: str) -> str:
    try:
        parts = [parse_image(image, key) for image in images]
    except Exception as error:
        raise RuntimeError(f"{dest.stem}: {error}") from error
    dest.write_text("\n\n".join(part for part in parts if part) + "\n")
    return dest.stem


def _apply_cache(papers: list[dict]) -> None:
    render_figures(papers)
    for paper in papers:
        for question in paper.get("questions") or []:
            dest = CACHE / f"{_key(paper, question)}.md"
            if dest.is_file() and dest.stat().st_size > 20:
                urls = figure_urls(_key(paper, question))
                question["text"] = tidy_question(
                    splice_question(dest.read_text(), question["number"], urls), question["number"]
                )
                question["text_source"] = SOURCE


def transcribe(papers: list[dict]) -> None:
    key = api_key()
    CACHE.mkdir(parents=True, exist_ok=True)
    if not key:
        print("skipping formula text; set OPENPARSER_API_KEY")
        _apply_cache(papers)
        _report_figures(papers)
        return
    pending = []
    for paper in papers:
        if not paper.get("questions"):
            continue
        path = ROOT / paper["file"]
        if not path.is_file():
            continue
        import pymupdf

        doc = pymupdf.open(path)
        try:
            questions = paper["questions"]
            for index, question in enumerate(questions):
                dest = CACHE / f"{_key(paper, question)}.md"
                if dest.is_file() and dest.stat().st_size > 20:
                    continue
                nxt = questions[index + 1] if index + 1 < len(questions) else None
                pages = clips(doc, question, nxt)
                if not pages:
                    continue
                folder = CACHE / "crops" / _key(paper, question)
                folder.mkdir(parents=True, exist_ok=True)
                names = []
                for nth, pix in enumerate(pages, 1):
                    image = folder / f"{nth}.png"
                    pix.save(image)
                    names.append(image)
                pending.append((names, dest))
        finally:
            doc.close()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_one, images, dest, key) for images, dest in pending]
        for nth, future in enumerate(as_completed(futures), 1):
            print(f"{nth}/{len(pending)} {future.result()}", flush=True)
    _apply_cache(papers)
    _report_figures(papers)


def transcribe_schemes(questions: list[dict]) -> None:
    """Write data/schemes/<id>.md from the same OCR pass the question text uses.

    shortcut: a markdown file newer than the PDF is kept, delete it to redo that question.
    """
    key = api_key()
    SCHEMES.mkdir(parents=True, exist_ok=True)
    if not key:
        print("skipping markscheme text; set OPENPARSER_API_KEY")
        return
    pending = []
    for doc, question, span, source in each_scheme(questions):
        dest = SCHEMES / f"{question['id']}.md"
        if dest.is_file() and dest.stat().st_size > 20 and dest.stat().st_mtime >= source.stat().st_mtime:
            continue
        pages = scheme_clips(doc, span)
        if not pages:
            continue
        folder = CACHE / "scheme-crops" / question["id"]
        folder.mkdir(parents=True, exist_ok=True)
        names = []
        for nth, pix in enumerate(pages, 1):
            image = folder / f"{nth}.png"
            pix.save(image)
            names.append(image)
        pending.append((names, dest))
    if not pending:
        print("markscheme text: already current")
        return
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_one, images, dest, key) for images, dest in pending]
        for nth, future in enumerate(as_completed(futures), 1):
            try:
                print(f"scheme {nth}/{len(pending)} {future.result()}", flush=True)
            except Exception as error:
                print(f"scheme {nth}/{len(pending)} failed: {error}", flush=True)


def _report_figures(papers: list[dict]) -> None:
    fixed, figures = restore_figures(papers)
    if fixed:
        print(f"restored {figures} figures in {fixed} questions")
