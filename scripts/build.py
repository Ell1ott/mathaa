"""Download the official specimen if ibo.org returns the PDF, then rebuild the local index."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from catalog import ROOT, load_catalog, write_catalog
from extract import OFFICIAL_DIR, OFFICIAL_NAME, extract_all
from match import REFS_PATH, match_questions

SPECIMEN_URL = (
    "https://www.ibo.org/globalassets/new-structure/university-admission/"
    "pdfs/dp-mathematics-analysis-and-approaches-specimen-papers-en.pdf"
)
SAMPLE_PAGE = "https://www.ibo.org/programmes/diploma-programme/assessment-and-exams/sample-exam-papers/"
QUESTIONS_PATH = ROOT / "data" / "questions.json"
COVERAGE_PATH = ROOT / "data" / "coverage.json"
README = ROOT / "README.md"


def fetch_specimen() -> str:
    dest = OFFICIAL_DIR / OFFICIAL_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100_000 and dest.read_bytes()[:4] == b"%PDF":
        return "present"
    request = urllib.request.Request(SPECIMEN_URL, headers={"User-Agent": "mathaa-local-index/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        note = f"HTTP {error.code}"
        if error.code == 403:
            note += " Cloudflare challenge, not the PDF"
        _write_fetch_note(note)
        print(f"specimen download failed: {note}")
        print(f"save the PDF from {SAMPLE_PAGE}")
        print(f"into {dest}")
        return "missing"
    except urllib.error.URLError as error:
        _write_fetch_note(str(error.reason))
        print(f"specimen download failed: {error.reason}")
        return "missing"
    if data[:4] != b"%PDF":
        _write_fetch_note("response was not a PDF")
        print("specimen download failed: response was not a PDF")
        print(f"save the PDF from {SAMPLE_PAGE}")
        print(f"into {dest}")
        return "missing"
    dest.write_bytes(data)
    print(f"saved {dest} ({len(data)} bytes)")
    return "downloaded"


def _write_fetch_note(note: str) -> None:
    path = ROOT / "data" / "specimen_fetch.json"
    path.write_text(
        json.dumps(
            {"url": SPECIMEN_URL, "sample_page": SAMPLE_PAGE, "result": note, "checked": date.today().isoformat()},
            indent=2,
        )
        + "\n"
    )


def coverage(catalog: list[dict], papers: list[dict], reports: list[dict]) -> dict:
    by_id = {paper["id"]: paper for paper in papers if paper.get("id")}
    rows = []
    for expected in catalog:
        got = by_id.get(expected["id"])
        if not got:
            status, detail = "missing", ""
            chars = questions = None
            file = None
        else:
            file_report = next((item for item in reports if item["file"] == got["file"]), {})
            status = "needs_ocr" if file_report.get("status") == "needs_ocr" else "present"
            chars = file_report.get("chars")
            questions = len(got["questions"])
            file = got["file"]
            detail = "text layer" if file_report.get("text_layer") else "no text layer"
        rows.append(
            {
                **expected,
                "status": status,
                "file": file,
                "questions": questions,
                "chars": chars,
                "detail": detail,
            }
        )
    return {
        "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "papers": rows,
        "files": reports,
        "present": sum(1 for row in rows if row["status"] == "present"),
        "missing": sum(1 for row in rows if row["status"] == "missing"),
        "needs_ocr": sum(1 for row in rows if row["status"] == "needs_ocr"),
    }


def write_readme_table(report: dict) -> None:
    lines = [
        "| Paper | Status | Questions | File |",
        "| --- | --- | --- | --- |",
    ]
    for row in report["papers"]:
        questions = "" if row["questions"] is None else str(row["questions"])
        lines.append(f"| {row['label']} | {row['status']} | {questions} | {row['file'] or ''} |")
    notes = [
        item["file"] + " (" + item["status"] + ")"
        for item in report["files"]
        if item.get("status") in {"needs_ocr", "unrecognized", "ambiguous"}
    ]
    if notes:
        lines.append("")
        lines.append("Files that did not map cleanly: " + "; ".join(notes) + ".")
    block = "\n".join(lines)
    text = README.read_text()
    start, end = "<!-- coverage:start -->", "<!-- coverage:end -->"
    if start not in text or end not in text:
        raise SystemExit("README is missing coverage markers")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    README.write_text(f"{before}{start}\n{block}\n{end}{after}")


def main() -> None:
    write_catalog()
    fetch_specimen()
    if "--refs" in sys.argv or not REFS_PATH.exists():
        from sync_refs import sync

        sync()
    papers, reports = extract_all()
    from transcribe import transcribe

    transcribe(papers)
    questions = match_questions(papers)
    QUESTIONS_PATH.write_text(
        json.dumps({"built": date.today().isoformat(), "questions": questions}, indent=2) + "\n"
    )
    from transcribe import write_cuts

    written, skipped = write_cuts(questions)
    print(f"question cuts: {written} written, {skipped} already current")
    report = coverage(load_catalog(), papers, reports)
    COVERAGE_PATH.write_text(json.dumps(report, indent=2) + "\n")
    write_readme_table(report)
    print(
        f"{report['present']} present, {report['missing']} missing, {report['needs_ocr']} need OCR, "
        f"{len(questions)} questions"
    )
    for item in reports:
        print(f"  {item['status']:12} {item['file']}  chars={item['chars']} text={item['text_layer']}")


if __name__ == "__main__":
    main()
