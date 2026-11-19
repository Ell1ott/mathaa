"""Cut each Physics question's markscheme into data/schemes.

Multiple-choice papers become one letter, `B`. Other papers are cropped from the
question row to the next question. A PDF with no text layer is skipped.

shortcut: a newer file is kept even if the crop changed, delete data/schemes/phy-* to rebuild.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from catalog import ROOT
from extract_physics import QUESTIONS_PATH
from transcribe import SCHEMES, scheme_clips, stitch

LETTER = re.compile(r"(\d{1,2})\s*\.\s*([A-D])\b")
NUMBER = re.compile(r"^(\d{1,2})\.?$")
LABEL = re.compile(r"^([A-J]\d{1,2})\.?$")
SUBPART = re.compile(r"^(?:[a-h]|i{1,3}|iv|v|vi{0,3}|ix|x)\.?$")


def _subpart(token: str) -> bool:
    return bool(SUBPART.match(token.strip("()")))


def _lines(page) -> list[list[tuple]]:
    import pymupdf

    buckets: dict[int, list[tuple]] = {}
    matrix = page.rotation_matrix
    for word in page.get_text("words"):
        rect = pymupdf.Rect(word[:4]) * matrix
        # "(a)" often sits a pixel below the question number. 4px still leaves real rows apart.
        buckets.setdefault(round(rect.y0 / 4) * 4, []).append((rect.x0, rect.y0, word[4]))
    return [sorted(buckets[key]) for key in sorted(buckets)]


def read_scheme(doc) -> tuple[dict[int, str] | None, dict]:
    """Return (answer letters, spans). A multiple-choice key has no spans."""
    letters: dict[int, str] = {}
    anchors: list[tuple] = []
    for page_no, page in enumerate(doc, 1):
        for match in LETTER.finditer(page.get_text("text")):
            letters[int(match.group(1))] = match.group(2)
        for bits in _lines(page):
            x, y, token = bits[0]
            if x > 90 or y < 60:
                continue
            label = LABEL.match(token)
            if label:
                anchors.append((page_no, y, label.group(1), True))
                continue
            number = NUMBER.match(token)
            nxt = bits[1][2] if len(bits) > 1 else ""
            if number and x <= 78:
                anchors.append((page_no, y, int(number.group(1)), _subpart(nxt)))
    spans = _spans(anchors)
    # A table of three or more questions wins over a stray "1. A" in the notes.
    if len(spans) >= 3:
        return None, spans
    keyed = {number: letter for number, letter in letters.items() if number <= 45}
    if len(keyed) >= 15 and 1 in keyed:
        return keyed, {}
    return None, spans


def _spans(anchors: list[tuple]) -> dict:
    labels = [item for item in anchors if isinstance(item[2], str)]
    numbers = [item for item in anchors if isinstance(item[2], int)]
    chosen = labels if len(labels) >= len(_sequence(numbers)) and labels else _sequence(numbers)
    spans = {}
    for index, item in enumerate(chosen):
        page, top, key = item[0], item[1], item[2]
        if index + 1 < len(chosen):
            page_end, bottom = chosen[index + 1][0], chosen[index + 1][1]
        else:
            page_end, bottom = None, None
        spans[key] = {"page_start": page, "page_end": page_end, "top": top, "bottom": bottom}
    return spans


def _sequence(anchors: list[tuple]) -> list[tuple]:
    """Question 1, then 2, then 3. The examiner list is also numbered, so question 1 is the 1. that leads into a real question 2."""
    start = None
    for index, item in enumerate(anchors):
        if item[2] != 1:
            continue
        nxt = next((later for later in anchors[index + 1 :] if later[2] == 2), None)
        if nxt and (item[3] or nxt[3]):
            start = index
            break
    if start is None:
        start = next((index for index, item in enumerate(anchors) if item[2] == 1 and item[3]), None)
    if start is None:
        return []
    chosen = [anchors[start]]
    for item in anchors[start + 1 :]:
        if item[2] == chosen[-1][2] + 1:
            chosen.append(item)
    return chosen


def _finish(spans: dict, page_count: int) -> dict:
    done = {}
    for key, span in spans.items():
        done[key] = {
            **span,
            "page_end": span["page_end"] or page_count,
        }
    return done


def scheme_pdf(question: dict) -> Path | None:
    paper = ROOT / question["file"]
    path = paper.with_name(paper.stem + "-markscheme.pdf")
    return path if path.is_file() else None


def _key(number) -> int | str:
    if isinstance(number, str) and number.isdigit():
        return int(number)
    return number


def write(questions: list[dict], dry_run: bool = False) -> dict:
    """Write data/schemes/<id>.md or .png. Returns counts."""
    import pymupdf

    SCHEMES.mkdir(parents=True, exist_ok=True)
    groups: dict[Path, list[dict]] = defaultdict(list)
    missing_pdf = 0
    for question in questions:
        path = scheme_pdf(question)
        if path is None:
            missing_pdf += 1
            continue
        groups[path].append(question)
    written = skipped = unmatched = 0
    kept: set[str] = set()
    for path, group in groups.items():
        doc = pymupdf.open(path)
        try:
            letters, spans = read_scheme(doc)
            spans = _finish(spans, doc.page_count)
            for question in group:
                key = _key(question["number"])
                if letters is not None:
                    letter = letters.get(key)
                    if not isinstance(key, int) or letter is None:
                        unmatched += 1
                        continue
                    dest = SCHEMES / f"{question['id']}.md"
                    kept.add(dest.name)
                    if dest.is_file() and dest.stat().st_mtime >= path.stat().st_mtime:
                        skipped += 1
                        continue
                    if not dry_run:
                        dest.write_text(letter + "\n")
                    written += 1
                    continue
                span = spans.get(key)
                if span is None:
                    unmatched += 1
                    continue
                dest = SCHEMES / f"{question['id']}.png"
                kept.add(dest.name)
                if dest.is_file() and dest.stat().st_mtime >= path.stat().st_mtime:
                    skipped += 1
                    continue
                if dry_run:
                    written += 1
                    continue
                pages = scheme_clips(doc, span)
                if not pages:
                    kept.discard(dest.name)
                    unmatched += 1
                    continue
                dest.write_bytes(stitch(pages))
                written += 1
        finally:
            doc.close()
    if not dry_run:
        for old in SCHEMES.glob("phy-*"):
            if old.suffix in {".png", ".md"} and old.name not in kept:
                old.unlink()
    return {
        "written": written,
        "skipped": skipped,
        "unmatched": unmatched,
        "missing_pdf": missing_pdf,
        "papers": len(groups),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    questions = json.loads(QUESTIONS_PATH.read_text()).get("questions", [])
    counts = write(questions, dry_run=args.dry_run)
    print(", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
