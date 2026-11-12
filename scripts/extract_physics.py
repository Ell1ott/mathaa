"""Split English Physics HL and SL papers into questions and attach Aimnova topics.

Aimnova cites Paper 1. From 2025 the library stores that sitting as p1a and p1b,
and both booklets start again at question 1. A citation is attached only when one
booklet contains that question number. When both do, the citation is left off.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from catalog import ROOT
from extract import clean_question, read_pdf, text_layer_ok
from match import lacks_overlap
from sync_refs import PHYSICS_REFS_PATH

LIBRARY = ROOT / "papers" / "library" / "sciences" / "physics"
QUESTIONS_PATH = ROOT / "data" / "physics" / "questions.json"
NAME = re.compile(r"^p(\d+)([ab])?(?:-tz(\d+))?\.pdf$", re.I)
QSTART = re.compile(r"(?m)^[ \t]*(\d{1,2})\.\s+\S")
LABELED = re.compile(r"(?m)^[ \t]*([A-G])(\d+)\.\s+\S")


def paper_code(match: re.Match[str]) -> str:
    return f"{match.group(1)}{(match.group(2) or '').upper()}"


def aim_paper(code: str) -> int:
    found = re.match(r"\d+", str(code))
    if not found:
        raise ValueError(code)
    return int(found.group())


def pdfs() -> list[tuple[str, Path]]:
    found = []
    for level in ("hl", "sl"):
        base = LIBRARY / level
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.pdf")):
            if path.parent.name != "en":
                continue
            if "markscheme" in path.name or "--" in path.name:
                continue
            if NAME.fullmatch(path.name):
                found.append((level, path))
    return found


def identity(level: str, path: Path) -> dict:
    match = NAME.fullmatch(path.name)
    if not match:
        raise ValueError(path.name)
    year_s, month = path.parent.parent.name.split("-")
    tz = f"TZ{match.group(3)}" if match.group(3) else None
    code = paper_code(match)
    stem = path.stem.lower()
    return {
        "id": f"phy-{level}-{year_s}-{month}-{stem}",
        "level": level,
        "year": int(year_s),
        "session": "May" if month == "05" else "November",
        "paper": code,
        "tz": tz,
        "file": str(path.relative_to(ROOT)),
    }


def keep_sequence(starts: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Keep 1, 2, 3, … and ignore a later 2. that belongs inside an earlier question."""
    first = next((index for index, item in enumerate(starts) if item[0] == 1), None)
    if first is None:
        return []
    kept = [starts[first]]
    cursor = first
    while True:
        want = kept[-1][0] + 1
        nxt = next((index for index in range(cursor + 1, len(starts)) if starts[index][0] == want), None)
        if nxt is None:
            break
        kept.append(starts[nxt])
        cursor = nxt
    return kept


def slice_questions(pages: list[tuple[int, str]], chosen: list[tuple]) -> list[dict]:
    questions = []
    for index, (number, page_index, pos, pdf_page) in enumerate(chosen):
        if index + 1 < len(chosen):
            end_index, end_pos = chosen[index + 1][1], chosen[index + 1][2]
        else:
            end_index, end_pos = len(pages) - 1, None
        chunks = []
        if page_index == end_index and end_pos is not None:
            chunks.append(pages[page_index][1][pos:end_pos])
            end_pdf = pages[page_index][0]
        else:
            chunks.append(pages[page_index][1][pos:])
            for mid in range(page_index + 1, end_index):
                chunks.append(pages[mid][1])
            if end_pos is not None and end_index != page_index:
                chunks.append(pages[end_index][1][:end_pos])
            end_pdf = pages[end_index][0]
        text = clean_question("\n".join(chunks))
        if text:
            questions.append(
                {"number": number, "text": text, "page_start": pdf_page, "page_end": end_pdf}
            )
    return questions


def questions_from_physics(pages: list[tuple[int, str]]) -> list[dict]:
    starts = []
    for index, (pdf_page, text) in enumerate(pages):
        for match in QSTART.finditer(text):
            starts.append((int(match.group(1)), index, match.start(), pdf_page))
    numbered = slice_questions(pages, keep_sequence(starts))
    if numbered:
        return numbered
    labeled = []
    for index, (pdf_page, text) in enumerate(pages):
        for match in LABELED.finditer(text):
            labeled.append((match.group(1) + match.group(2), index, match.start(), pdf_page))
    return slice_questions(pages, labeled)


def load_refs() -> list[dict]:
    if not PHYSICS_REFS_PATH.is_file():
        return []
    return json.loads(PHYSICS_REFS_PATH.read_text()).get("refs", [])


def match_physics(papers: list[dict], refs: list[dict]) -> list[dict]:
    groups: dict[tuple, list[tuple[dict, dict]]] = defaultdict(list)
    for paper in papers:
        for question in paper["questions"]:
            key = (
                paper["level"],
                paper["year"],
                paper["session"],
                aim_paper(paper["paper"]),
                paper["tz"],
                question["number"],
            )
            groups[key].append((paper, question))
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for ref in refs:
        by_key[(ref["level"], ref["year"], ref["session"], ref["paper"], ref["tz"], ref["question"])].append(ref)
    questions = []
    for paper in papers:
        label = f"{paper['level'].upper()} {paper['session']} {paper['year']} Paper {paper['paper']}"
        if paper["tz"]:
            label += f" {paper['tz']}"
        for question in paper["questions"]:
            key = (
                paper["level"],
                paper["year"],
                paper["session"],
                aim_paper(paper["paper"]),
                paper["tz"],
                question["number"],
            )
            use = len(groups[key]) == 1
            packed = []
            if use:
                seen = set()
                for topic in by_key.get(key, []):
                    ident = (topic["code"], topic["topic"])
                    if ident in seen:
                        continue
                    seen.add(ident)
                    packed.append({"code": topic["code"], "topic": topic["topic"], "area": topic["area"]})
            reasons = []
            if use and packed and any(lacks_overlap(topic["topic"], question["text"]) for topic in packed):
                reasons.append("topic words not in question")
            status = "review" if reasons else ("matched" if packed else "untagged")
            questions.append(
                {
                    "id": f"{paper['id']}-q{question['number']}",
                    "paper_id": paper["id"],
                    "label": label,
                    "level": paper["level"],
                    "year": paper["year"],
                    "session": paper["session"],
                    "paper": paper["paper"],
                    "tz": paper["tz"],
                    "number": question["number"],
                    "page_start": question["page_start"],
                    "page_end": question["page_end"],
                    "file": paper["file"],
                    "text": question["text"],
                    "text_source": "pymupdf",
                    "topics": packed,
                    "status": status,
                    "reasons": reasons,
                }
            )
    return questions


def extract_all() -> dict:
    papers = []
    meta = []
    for index, (level, path) in enumerate(pdfs(), 1):
        info = identity(level, path)
        pages = read_pdf(path)
        numbered = list(enumerate(pages, 1))
        if not text_layer_ok(pages):
            info["status"] = "needs_ocr"
            info["questions"] = []
        else:
            info["questions"] = questions_from_physics(numbered)
            info["status"] = "present" if info["questions"] else "empty"
        meta.append({key: info[key] for key in ("id", "level", "year", "session", "paper", "tz", "file", "status")})
        if info["questions"]:
            papers.append(info)
        if index % 40 == 0:
            print(f"read {index} papers")
    questions = match_physics(papers, load_refs())
    counts: dict[str, int] = defaultdict(int)
    for paper in meta:
        counts[paper["status"]] += 1
    for question in questions:
        counts[question["status"]] += 1
    print(
        f"{len(meta)} papers, {len(questions)} questions, "
        + ", ".join(f"{key}={counts[key]}" for key in ("present", "needs_ocr", "empty", "matched", "review", "untagged") if counts[key])
    )
    return {
        "built": date.today().isoformat(),
        "questions": questions,
        "papers": meta,
    }


def write() -> dict:
    payload = extract_all()
    QUESTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUESTIONS_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {QUESTIONS_PATH}")
    return payload


if __name__ == "__main__":
    write()
