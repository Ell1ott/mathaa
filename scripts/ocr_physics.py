"""OCR every Physics paper one full page at a time, then split into questions.

Papers whose questions are already paddleocr text are skipped. Each finished
page is written under data/vl/physics/<paper-id>/ before the next page starts,
and questions.json is replaced after every page. Stop the process whenever you
like: a page that is already on disk is not sent again.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from catalog import ROOT
from extract_physics import QUESTIONS_PATH, keep_labels, keep_sequence
from transcribe import (
    CONTENT_RIGHT,
    FIGS,
    _anchor_line,
    _join,
    api_key,
    bands,
    parse_image,
    place_figures,
    tidy_question,
)

CACHE = ROOT / "data" / "vl" / "physics"
QSTART = re.compile(r"(?m)^(?:#{1,6}[ \t]+|\*\*)*(\d{1,2})\.(?:\*\*)?(?=\s|$)")
LSTART = re.compile(r"(?m)^(?:#{1,6}[ \t]+|\*\*)*([A-J]\d{1,2})\.(?:\*\*)?(?=\s|$)")
PAGE_NOISE = re.compile(r"^(?:\d{1,2}|\d{2}EP\d{2}|\d{4}[-–]\d{4}|[–\-]\s*\d{1,2}\s*[–\-])$")


def all_papers(payload: dict) -> list[dict]:
    by_id: dict[str, list[dict]] = defaultdict(list)
    for question in payload.get("questions", []):
        by_id[question["paper_id"]].append(question)
    papers = []
    for paper_id, questions in by_id.items():
        questions.sort(key=lambda item: item["number"] if isinstance(item["number"], int) else 0)
        pages = sorted({page for question in questions for page in range(question["page_start"], question["page_end"] + 1)})
        papers.append(
            {
                "id": paper_id,
                "file": questions[0]["file"],
                "pages": pages,
                "questions": questions,
            }
        )
    papers.sort(key=lambda paper: paper["id"])
    return papers


def _already_scanned(paper: dict) -> bool:
    return bool(paper["questions"]) and all(
        question.get("text_source") == "paddleocr-vl-1.6" for question in paper["questions"]
    )


def page_path(paper_id: str, page: int) -> Path:
    return CACHE / paper_id / f"p{page:03d}.md"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def render_page(pdf: Path, page: int, dest: Path) -> None:
    import pymupdf

    dest.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(pdf)
    try:
        sheet = document[page - 1]
        sheet.get_pixmap(dpi=140, alpha=False).save(dest)
    finally:
        document.close()


def ocr_page(pdf: Path, page: int, dest: Path, key: str) -> str:
    if dest.is_file() and dest.stat().st_size > 0:
        return "cached"
    image = dest.with_suffix(".png")
    render_page(pdf, page, image)
    try:
        text = parse_image(image, key)
    finally:
        image.unlink(missing_ok=True)
    write_text(dest, text.strip() + ("\n" if text.strip() else ""))
    return "fetched"


def drop_page_noise(text: str) -> str:
    kept = [line for line in text.splitlines() if not PAGE_NOISE.match(line.strip())]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def _opening_words(line: str) -> list[str]:
    body = re.sub(r"^\d{1,2}\.\s*", "", line.strip())
    return re.findall(r"[A-Za-z]+", body)[:16]


def _find_opening(text: str, words: list[str], start: int, end: int) -> int | None:
    """Where this question's wording begins, even if the scan ate the first letters."""
    if len(words) < 3 or end - start < 20:
        return None
    region = text[start:end]
    shortest = 5 if len(words) >= 5 else len(words)
    for length in range(min(8, len(words)), shortest - 1, -1):
        for offset in range(0, len(words) - length + 1):
            chunk = words[offset : offset + length]
            pattern = r"\b" + r"\b\W{0,25}\b".join(re.escape(word) for word in chunk) + r"\b"
            match = re.search(pattern, region, re.I)
            if match is None:
                continue
            pos = start + match.start()
            line_start = text.rfind("\n", start, pos) + 1
            if pos - line_start < 12:
                pos = line_start
            return pos
    return None


def _bridge_gaps(text: str, chosen: list[tuple], starts: list[tuple], openings: dict[int, str]) -> list[tuple]:
    """Keep going after a missing 5. by finding that question's wording, then the next 6."""
    if not chosen or not openings:
        return chosen
    for _ in range(48):
        last_number, _page_index, last_pos, _pdf_page = chosen[-1]
        expect = last_number + 1
        words = _opening_words(openings.get(expect, ""))
        later = [item for item in starts if item[2] > last_pos + 30 and item[0] > last_number]
        exact = [item for item in later if item[0] == expect]
        if exact:
            chosen.append(min(exact, key=lambda item: item[2]))
            continue
        limit = min((item[2] for item in later if item[0] > expect), default=len(text))
        pos = _find_opening(text, words, last_pos + 30, limit) if len(words) >= 3 else None
        if pos is None:
            # One eaten question should not throw away the numbered questions after it.
            following = min((item for item in later if item[0] == expect + 1), default=None, key=lambda item: item[2])
            if following is None:
                break
            chosen.append(following)
            continue
        chosen.append((expect, 0, pos, 0))
    return chosen


def split_pages(pages: dict[int, str], openings: dict[int, str] | None = None, *, labels: bool | None = None) -> dict:
    """Split concatenated page markdown into 1. 2. 3. or A1. B1. E3. questions."""
    chunks = []
    for page in sorted(pages):
        chunks.append(pages[page].strip())
    text = "\n\n".join(chunks)
    starts = [(int(match.group(1)), 0, match.start(), 0) for match in QSTART.finditer(text)]
    labeled = [(match.group(1), 0, match.start(), 0) for match in LSTART.finditer(text)]
    if labels is None:
        labels = len(keep_labels(labeled)) > len(keep_sequence(starts))
    if labels:
        chosen = keep_labels(labeled)
    else:
        chosen = _bridge_gaps(text, keep_sequence(starts), starts, openings or {})
    questions = {}
    for index, (number, _page_index, pos, _pdf_page) in enumerate(chosen):
        end = chosen[index + 1][2] if index + 1 < len(chosen) else len(text)
        piece = drop_page_noise(tidy_question(text[pos:end].strip(), number if isinstance(number, int) else 0))
        piece = re.sub(rf"^(?!{re.escape(str(number))}\.)\d{{1,2}}\.\s+", "", piece)
        if piece:
            questions[number] = piece
    return questions


def _opening_body(lines: list[str], index: int, first: str) -> str:
    parts = [first]
    for line in lines[index + 1 : index + 4]:
        stripped = line.strip()
        if not stripped or re.match(r"^[A-D]\.\s", stripped) or re.fullmatch(r"\d{1,2}\.", stripped):
            break
        parts.append(stripped)
        if len(" ".join(parts)) > 180:
            break
    return " ".join(parts)[:240]


def pdf_openings(paper: dict) -> dict[int, str]:
    """First line of each question in the PDF, used when the scan dropped the number."""
    cached = paper.get("openings")
    if cached is not None:
        return cached
    import pymupdf

    pdf = ROOT / paper["file"]
    openings: dict[int, str] = {}
    if not pdf.is_file():
        paper["openings"] = openings
        return openings
    document = pymupdf.open(pdf)
    try:
        for question in paper["questions"]:
            number = question["number"]
            if not isinstance(number, int):
                continue
            page = document[question["page_start"] - 1]
            lines = page.get_text().splitlines()
            for index, line in enumerate(lines):
                stripped = line.strip()
                same_line = re.match(rf"{number}\.\s+(\S.*)", stripped)
                if same_line:
                    openings[number] = _opening_body(lines, index, same_line.group(1))
                    break
                if re.fullmatch(rf"{number}\.", stripped):
                    nxt = next((item.strip() for item in lines[index + 1 : index + 3] if item.strip()), "")
                    if nxt:
                        openings[number] = _opening_body(lines, index + 1, nxt)
                    break
    finally:
        document.close()
    paper["openings"] = openings
    return openings


def _pages_ready(question: dict, pages: dict[int, str]) -> bool:
    return all(page in pages for page in range(question["page_start"], question["page_end"] + 1))


def apply_split(payload: dict, paper: dict, pages: dict[int, str]) -> int:
    use_labels = any(isinstance(question["number"], str) for question in paper["questions"])
    found = split_pages(pages, None if use_labels else pdf_openings(paper), labels=use_labels)
    updated = 0
    by_number = {question["number"]: question for question in paper["questions"]}
    for number, text in found.items():
        question = by_number.get(number)
        # A half-scanned question would replace the PDF text with its first page only.
        if question is None or not text or not _pages_ready(question, pages):
            continue
        if question.get("text") == text and question.get("text_source") == "paddleocr-vl-1.6":
            continue
        question["text"] = text
        question["text_source"] = "paddleocr-vl-1.6"
        updated += 1
    return updated


def diagram_boxes(page, top: float, bottom: float) -> list:
    """Vector drawings in the question column, including a plate diagram made of thin lines."""
    import pymupdf

    limit = pymupdf.Rect(36, top, CONTENT_RIGHT, bottom)
    rects = []
    for drawing in page.get_drawings():
        rect = pymupdf.Rect(drawing["rect"])
        if max(rect.width, rect.height) < 0.4:
            continue
        # A full-width rule is an answer box or a page edge, not part of the drawing.
        if rect.width > 460 and rect.height < 3:
            continue
        if rect.x0 < 20:
            continue
        # Plate lines and plus signs are stored as zero-width strokes.
        if rect.width < 0.8:
            rect.x0 -= 0.4
            rect.x1 += 0.4
        if rect.height < 0.8:
            rect.y0 -= 0.4
            rect.y1 += 0.4
        if rect.x0 > CONTENT_RIGHT or not rect.intersects(limit):
            continue
        rects.append(rect)
    found = []
    for rect in _join(rects):
        if rect.height < 40 or rect.width < 36 or rect.width > 460:
            continue
        if rect.width * rect.height < 3500:
            continue
        for block in page.get_text("blocks"):
            if block[6] != 0:
                continue
            words = " ".join(block[4].split())
            if not words or len(words) > 16:
                continue
            label = pymupdf.Rect(block[:4])
            near = pymupdf.Rect(rect.x0 - 16, rect.y0 - 8, rect.x1 + 16, rect.y1 + 8)
            if label.intersects(near) and label.x1 < CONTENT_RIGHT + 24:
                rect |= label
        rect = pymupdf.Rect(rect.x0 - 4, rect.y0 - 4, rect.x1 + 4, rect.y1 + 4) & page.rect
        if rect.width > 20 and rect.height > 20:
            found.append(rect)
    for info in page.get_image_info():
        rect = pymupdf.Rect(info["bbox"]) & limit
        if rect.width < 36 or rect.height < 40 or rect.width * rect.height < 3500:
            continue
        if any((rect & box).get_area() > 0.5 * rect.get_area() for box in found):
            continue
        found.append(rect)
    found = _join([pymupdf.Rect(rect) for rect in found])
    found.sort(key=lambda rect: (rect.y0, rect.x0))
    return found


def attach_diagrams(paper: dict) -> int:
    """Crop PDF drawings into the question text where the scan left them out."""
    import pymupdf

    pdf = ROOT / paper["file"]
    if not pdf.is_file():
        return 0
    FIGS.mkdir(parents=True, exist_ok=True)
    changed = 0
    document = pymupdf.open(pdf)
    try:
        questions = paper["questions"]
        for index, question in enumerate(questions):
            if question.get("text_source") != "paddleocr-vl-1.6":
                continue
            nxt = questions[index + 1] if index + 1 < len(questions) else None
            kept = []
            for page, top, bottom in bands(document, question, nxt):
                for rect in diagram_boxes(page, top, bottom):
                    line = _anchor_line(page, rect)
                    if line:
                        kept.append((page, rect, line))
            if not kept:
                continue
            urls = []
            anchors = []
            for nth, (page, rect, line) in enumerate(kept, 1):
                dest = FIGS / f"{question['id']}-{nth}.png"
                if not dest.is_file():
                    page.get_pixmap(dpi=140, clip=rect).save(dest)
                urls.append(f"/fig/{dest.name}")
                anchors.append(line)
            updated = place_figures(question.get("text") or "", urls, anchors)
            if updated != question.get("text"):
                question["text"] = updated
                changed += 1
    finally:
        document.close()
    return changed


def refresh_saved() -> None:
    """Re-split cached pages and put diagrams back. Does not call the OCR service."""
    payload = json.loads(QUESTIONS_PATH.read_text())
    papers = all_papers(payload)
    for paper in papers:
        held = {}
        for page in paper["pages"]:
            dest = page_path(paper["id"], page)
            if dest.is_file() and dest.stat().st_size > 0:
                held[page] = dest.read_text()
        if not held:
            continue
        changed = apply_split(payload, paper, held)
        drawn = attach_diagrams(paper)
        save_questions(payload)
        print(f"{paper['id']}  text {changed}  diagrams {drawn}", flush=True)


def save_questions(payload: dict) -> None:
    write_text(QUESTIONS_PATH, json.dumps(payload, indent=2) + "\n")


def main() -> None:
    key = api_key()
    if not key:
        raise SystemExit("Set OPENPARSER_API_KEY. Nothing was sent.")
    payload = json.loads(QUESTIONS_PATH.read_text())
    papers = [paper for paper in all_papers(payload) if not _already_scanned(paper)]
    total_pages = sum(len(paper["pages"]) for paper in papers)
    print(f"{len(papers)} papers still to scan, {total_pages} pages", flush=True)
    print("Stop whenever you like. A page already saved is not sent again.", flush=True)
    done = 0
    for paper in papers:
        pdf = ROOT / paper["file"]
        if not pdf.is_file():
            print(f"missing {paper['file']}", flush=True)
            continue
        held: dict[int, str] = {}
        for page in paper["pages"]:
            dest = page_path(paper["id"], page)
            if dest.is_file() and dest.stat().st_size > 0:
                state = "cached"
            else:
                state = None
                error = None
                for attempt in range(3):
                    try:
                        state = ocr_page(pdf, page, dest, key)
                        break
                    except Exception as caught:  # noqa: BLE001 - pages already stored stay on disk
                        error = caught
                        print(f"retry {attempt + 1}/3 {paper['id']} p{page}: {error}", flush=True)
                if state is None:
                    print(f"FAILED {paper['id']} p{page}: {error}", flush=True)
                    print("stopped on this page. Run the script again to continue.", flush=True)
                    return
            held[page] = dest.read_text()
            done += 1
            changed = apply_split(payload, paper, held)
            save_questions(payload)
            print(f"{done}/{total_pages} {state} {paper['id']} p{page}  questions updated {changed}", flush=True)
        drawn = attach_diagrams(paper)
        if drawn:
            save_questions(payload)
            print(f"diagrams {paper['id']} {drawn}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    import sys

    if "--saved" in sys.argv:
        refresh_saved()
    else:
        main()
