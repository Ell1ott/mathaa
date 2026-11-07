"""Split local PDFs into questions. Text layer only; scans are marked needs_ocr."""

from __future__ import annotations

import re
from pathlib import Path

from catalog import ROOT, load_catalog

OFFICIAL_NAME = "dp-mathematics-analysis-and-approaches-specimen-papers-en.pdf"
OFFICIAL_DIR = ROOT / "papers" / "official"
INBOX = ROOT / "papers" / "inbox"
QSTART = re.compile(r"(?m)^[ \t]*(\d{1,2})\.\s*(?:\n\s*)?\[?\s*Maximum marks?\s*:")
DROP_LINE = re.compile(
    r"^(?:turn over|please turn over|please do not write on this page\.?|"
    r"answers written on this page(?: will not be marked)?\.?|"
    r"will not be marked\.?|"
    r"do\b.*\bnot\b.*write solutions on this page\.?|"
    r"disclaimer:?|references:?|"
    r"©\s*international baccalaureate.*|"
    r"content used in ib assessments\b.*|"
    r"section [ab]|"
    r"answer all questions in the answer booklet provided\..*|"
    r"\d{2}ep\d+|specimen paper|continued|\d{4}\s*[–—-]\s*\d{4})$",
    re.I,
)


def signals_from_name(name: str) -> dict:
    stem = Path(name).stem.lower().replace("_", "-").replace(" ", "-")
    if "specimen" in stem:
        paper_m = re.search(r"(?:paper|p)-?([123])(?!\d)", stem)
        year_m = re.search(r"20\d\d", stem)
        return {
            "year": int(year_m.group(0)) if year_m else 2021,
            "session": "Specimen",
            "paper": int(paper_m.group(1)) if paper_m else None,
            "tz": None,
        }
    match = re.search(
        r"(20\d\d).*?(may|november|nov|0?5|0?11).*?(?:paper|p)-?([123])(?:.*?tz-?([123]))?",
        stem,
    )
    if not match:
        match = re.search(r"([mn])(\d{2}).*?(?:paper|p)-?([123])(?:.*?tz-?([123]))?", stem)
        if not match:
            paper_m = re.search(r"(?:paper|p)-?([123])(?!\d)", stem)
            tz_m = re.search(r"tz-?([123])", stem)
            year_m = re.search(r"(20\d\d)|(?:^|-)([mn])(\d{2})(?:-|$)", stem)
            year = session = None
            if year_m and year_m.group(1):
                year = int(year_m.group(1))
            elif year_m and year_m.group(2):
                year = 2000 + int(year_m.group(3))
                session = "May" if year_m.group(2) == "m" else "November"
            return {
                "year": year,
                "session": session,
                "paper": int(paper_m.group(1)) if paper_m else None,
                "tz": f"TZ{tz_m.group(1)}" if tz_m else None,
            }
        year = 2000 + int(match.group(2))
        session = "May" if match.group(1) == "m" else "November"
        return {
            "year": year,
            "session": session,
            "paper": int(match.group(3)),
            "tz": f"TZ{match.group(4)}" if match.group(4) else None,
        }
    month = match.group(2)
    session = "May" if month in {"may", "5", "05"} else "November"
    return {
        "year": int(match.group(1)),
        "session": session,
        "paper": int(match.group(3)),
        "tz": f"TZ{match.group(4)}" if match.group(4) else None,
    }


def signals_from_text(text: str) -> dict:
    head = text[:3000]
    specimen = bool(re.search(r"\bspecimen\b", head, re.I))
    paper_m = re.search(r"\bpaper\s+([123])\b", head, re.I)
    tz_m = re.search(r"\bTZ\s*([123])\b", head, re.I) or re.search(
        r"time\s+zone\s*([123])\b", head, re.I
    )
    dated = re.search(r"\b(\d{1,2}\s+)?(May|November)\s+(20\d\d)\b", head, re.I)
    year = int(dated.group(3)) if dated else None
    session = dated.group(2).title() if dated else None
    if specimen:
        session = "Specimen"
        year = year or 2021
    return {
        "year": year,
        "session": session,
        "paper": int(paper_m.group(1)) if paper_m else None,
        "tz": f"TZ{tz_m.group(1)}" if tz_m else None,
        "hl": bool(re.search(r"higher level", head, re.I)),
    }


def apply_folder_session(path: Path, signals: dict, conflicts: list[str]) -> tuple[dict, list[str]]:
    folder = re.search(r"(20\d\d)-(05|11)", path.as_posix())
    if not folder:
        return signals, conflicts
    from_folder = {
        "year": int(folder.group(1)),
        "session": "May" if folder.group(2) == "05" else "November",
    }
    for key, value in from_folder.items():
        if signals.get(key) is None:
            signals[key] = value
        elif signals[key] != value:
            conflicts.append(key)
    return signals, conflicts


def merge_signals(filename: str, cover: str) -> tuple[dict, list[str]]:
    from_name = signals_from_name(filename)
    from_text = signals_from_text(cover)
    merged = {}
    conflicts = []
    for key in ("year", "session", "paper", "tz"):
        named, printed = from_name.get(key), from_text.get(key)
        if named and printed and named != printed:
            conflicts.append(key)
        merged[key] = printed or named
    merged["hl"] = from_text.get("hl", False)
    return merged, conflicts


def resolve_paper(signals: dict, conflicts: list[str], catalog: list[dict]) -> dict:
    if conflicts or not signals.get("hl"):
        return {"id": None, "ambiguous": True, "reason": "paper identity conflicts" if conflicts else "not HL"}
    if not all(signals.get(key) for key in ("year", "session", "paper")):
        return {"id": None, "ambiguous": True, "reason": "paper identity incomplete"}
    same = [
        paper
        for paper in catalog
        if paper["year"] == signals["year"]
        and paper["session"] == signals["session"]
        and paper["paper"] == signals["paper"]
    ]
    if signals.get("tz"):
        zoned = [paper for paper in same if paper["tz"] == signals["tz"]]
        # A filename tz on an unzoned paper came from "Zone A" on a sitting-time cover.
        if zoned or not same or any(paper["tz"] for paper in same):
            same = zoned
    if len(same) == 1:
        return {"id": same[0]["id"], "ambiguous": False, "reason": "", "meta": same[0]}
    if len(same) > 1:
        return {"id": None, "ambiguous": True, "reason": "timezone missing", "candidates": [p["id"] for p in same]}
    return {"id": None, "ambiguous": True, "reason": "no catalog paper"}


def page_kind(text: str) -> str:
    head = text[:1500].lower()
    if "standard level" in head and "higher level" not in head:
        return "sl"
    if "markscheme" in head or "instructions to examiners" in head:
        return "ms"
    if (
        "higher level" in head
        and re.search(r"paper\s+[123]", head)
        and ("instructions to candidates" in head or "instructions to students" in head)
    ):
        return "cover"
    return "body"


def split_papers(pages: list[str]) -> list[dict]:
    """pages are 1-based PDF page texts. A cover starts an HL paper; markscheme or SL ends it."""
    found = []
    current = None
    for number, text in enumerate(pages, 1):
        kind = page_kind(text)
        if kind == "cover":
            if current:
                found.append(current)
            current = {"page_start": number, "pages": [(number, text)]}
        elif kind in {"ms", "sl"}:
            if current:
                found.append(current)
                current = None
        elif current:
            current["pages"].append((number, text))
    if current:
        found.append(current)
    if found:
        return found
    body = [(number, text) for number, text in enumerate(pages, 1) if page_kind(text) == "body"]
    if body and signals_from_text(pages[0]).get("hl"):
        return [{"page_start": body[0][0], "pages": body}]
    return []


def clean_question(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or DROP_LINE.match(stripped):
            continue
        if re.fullmatch(r"[-–—\s\d]+", stripped) and len(stripped) < 8:
            continue
        if not re.search(r"[A-Za-z0-9]", stripped):
            continue
        if re.match(r"(?:references:|©\s*international baccalaureate)", stripped, re.I):
            break
        lines.append(stripped)
    return "\n".join(lines).strip()


def questions_from_pages(pages: list[tuple[int, str]]) -> list[dict]:
    starts = []
    for index, (pdf_page, text) in enumerate(pages):
        for match in QSTART.finditer(text):
            starts.append((int(match.group(1)), index, match.start(), pdf_page))
    questions = []
    for index, (number, page_index, pos, pdf_page) in enumerate(starts):
        if index + 1 < len(starts):
            end_index, end_pos = starts[index + 1][1], starts[index + 1][2]
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


def text_layer_ok(pages: list[str]) -> bool:
    if not pages:
        return False
    lengths = [len(page.strip()) for page in pages]
    return (sum(lengths) / len(lengths)) >= 80 and sum(1 for n in lengths if n >= 40) >= max(1, len(pages) // 5)


def read_pdf(path: Path) -> list[str]:
    import pymupdf

    document = pymupdf.open(path)
    try:
        return [page.get_text("text") for page in document]
    finally:
        document.close()


def extract_file(path: Path, catalog: list[dict]) -> tuple[list[dict], dict]:
    pages = read_pdf(path)
    rel = str(path.relative_to(ROOT))
    chars = sum(len(page) for page in pages)
    report = {
        "file": rel,
        "pages": len(pages),
        "chars": chars,
        "text_layer": text_layer_ok(pages),
    }
    if not report["text_layer"]:
        report["status"] = "needs_ocr"
        signals, conflicts = merge_signals(path.name, pages[0] if pages else "")
        signals, conflicts = apply_folder_session(path, signals, conflicts)
        signals["hl"] = True
        resolved = resolve_paper(signals, conflicts, catalog)
        if not resolved.get("id"):
            return [], report
        return [
            {
                "id": resolved["id"],
                "file": rel,
                "page_start": 1,
                "page_end": len(pages),
                "ambiguous": False,
                "reason": "",
                "candidates": [],
                "signals": {key: signals.get(key) for key in ("year", "session", "paper", "tz")},
                "questions": [],
            }
        ], report
    slices = split_papers(pages)
    if not slices:
        report["status"] = "unrecognized"
        return [], report
    papers = []
    ambiguous = False
    for chunk in slices:
        cover = chunk["pages"][0][1]
        signals, conflicts = merge_signals(path.name, cover)
        signals, conflicts = apply_folder_session(path, signals, conflicts)
        resolved = resolve_paper(signals, conflicts, catalog)
        if resolved.get("reason") == "not HL":
            continue
        questions = questions_from_pages(chunk["pages"])
        paper = {
            "id": resolved.get("id"),
            "file": rel,
            "page_start": chunk["pages"][0][0],
            "page_end": chunk["pages"][-1][0],
            "ambiguous": resolved.get("ambiguous", False),
            "reason": resolved.get("reason", ""),
            "candidates": resolved.get("candidates", []),
            "signals": {key: signals.get(key) for key in ("year", "session", "paper", "tz")},
            "questions": questions,
        }
        if paper["ambiguous"]:
            ambiguous = True
        papers.append(paper)
    report["status"] = "ambiguous" if ambiguous and not any(p["id"] for p in papers) else "present"
    report["papers"] = [p["id"] or p["reason"] for p in papers]
    return papers, report


def pdfs() -> list[Path]:
    found = []
    official = OFFICIAL_DIR / OFFICIAL_NAME
    if official.exists():
        found.append(official)
    if INBOX.exists():
        found.extend(sorted(path for path in INBOX.iterdir() if path.suffix.lower() == ".pdf"))
    aa = ROOT / "papers" / "library" / "mathematics" / "mathematics-analysis-and-approaches" / "hl"
    if aa.exists():
        found.extend(
            sorted(
                path
                for path in aa.rglob("*.pdf")
                if "/en/" in path.as_posix() and "markscheme" not in path.name and "--" not in path.name
            )
        )
    return found


def extract_all() -> tuple[list[dict], list[dict]]:
    catalog = load_catalog()
    papers: list[dict] = []
    reports: list[dict] = []
    by_id: dict[str, int] = {}
    for path in pdfs():
        extracted, report = extract_file(path, catalog)
        for paper in extracted:
            pid = paper.get("id")
            if not pid:
                papers.append(paper)
                continue
            previous = by_id.get(pid)
            if previous is None:
                by_id[pid] = len(papers)
                papers.append(paper)
                continue
            if len(paper["questions"]) > len(papers[previous]["questions"]):
                papers[previous] = paper
                report.setdefault("replaced", []).append(pid)
            else:
                report.setdefault("duplicates", []).append(pid)
        reports.append(report)
    return papers, reports
