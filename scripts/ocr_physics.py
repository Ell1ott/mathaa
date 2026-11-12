"""OCR categorized Physics papers one full page at a time, then split into questions.

Only papers that already have an Aimnova topic are sent. Each finished page is
written under data/vl/physics/<paper-id>/ before the next page starts, and
questions.json is replaced after every page. Stop the process whenever you like:
a page that is already on disk is not sent again.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from catalog import ROOT
from extract_physics import QUESTIONS_PATH, keep_sequence
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
QSTART = re.compile(r"(?m)^(?:#{1,6}[ \t]+|\*\*)?(\d{1,2})\.(?:\*\*)?(?=\s|$)")
PAGE_NOISE = re.compile(r"^(?:\d{1,2}|\d{2}EP\d{2}|\d{4}[-–]\d{4}|[–\-]\s*\d{1,2}\s*[–\-])$")


def categorized_papers(payload: dict) -> list[dict]:
    by_id: dict[str, list[dict]] = defaultdict(list)
    for question in payload.get("questions", []):
        by_id[question["paper_id"]].append(question)
    papers = []
    for paper_id, questions in by_id.items():
        if not any(question.get("topics") for question in questions):
            continue
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


def split_pages(pages: dict[int, str]) -> dict[int, str]:
    """Split concatenated page markdown on 1. 2. 3. …, ignoring a later restart."""
    chunks = []
    offsets = []
    cursor = 0
    for page in sorted(pages):
        offsets.append((page, cursor))
        chunks.append(pages[page].strip())
        cursor += len(chunks[-1]) + 2
    text = "\n\n".join(chunks)
    starts = []
    for match in QSTART.finditer(text):
        starts.append((int(match.group(1)), 0, match.start(), 0))
    chosen = keep_sequence(starts)
    questions = {}
    for index, (number, _page_index, pos, _pdf_page) in enumerate(chosen):
        end = chosen[index + 1][2] if index + 1 < len(chosen) else len(text)
        piece = drop_page_noise(tidy_question(text[pos:end].strip(), number))
        if piece:
            questions[number] = piece
    return questions


def apply_split(payload: dict, paper: dict, pages: dict[int, str]) -> int:
    found = split_pages(pages)
    updated = 0
    by_number = {question["number"]: question for question in paper["questions"]}
    for number, text in found.items():
        question = by_number.get(number)
        if question is None or not text:
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
    papers = categorized_papers(payload)
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
    papers = categorized_papers(payload)
    total_pages = sum(len(paper["pages"]) for paper in papers)
    print(f"{len(papers)} categorized papers, {total_pages} pages", flush=True)
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
