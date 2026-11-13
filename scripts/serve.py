"""Local question browser. Bind to localhost only."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from catalog import ROOT
from transcribe import tidy_question, tidy_scheme

QUESTIONS = ROOT / "data" / "questions.json"
PHYSICS_QUESTIONS = ROOT / "data" / "physics" / "questions.json"
COVERAGE = ROOT / "data" / "coverage.json"
REVIEWS = ROOT / "data" / "reviews.json"
THUMBS = ROOT / "data" / "thumbs"
COVERS = ROOT / "data" / "covers"
PORT = 8765
CUT_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.png")
COVER_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*-[12]\.jpg")
HEADER = re.compile(
    r"(?m)^[#\s]*(\d+)\.\s*(?:\\\()?\s*\[Maximum marks?:\s*(\d+)\]\s*(?:\\\))?[ \t]*\n?"
)
SESSION_ORDER = {"November": 0, "May": 1, "Specimen": 2}
ECON_ROOT = ROOT / "papers" / "library" / "societies" / "economics"
ECON_NAME = re.compile(r"^p(\d+)(?:-(tz\d+))?\.pdf$", re.I)
ECON_MONTH = {"05": "May", "11": "November"}


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text())


def paper_value(paper: int | str) -> int | str:
    text = str(paper)
    if text.isdigit():
        return int(text)
    return text.upper()


def paper_rank(paper: int | str) -> tuple[int, str]:
    match = re.match(r"(\d+)([A-Za-z])?", str(paper))
    if not match:
        return (99, "")
    return (int(match.group(1)), (match.group(2) or "").upper())


def number_rank(number: int | str) -> tuple[str, int]:
    match = re.match(r"([A-Za-z]*)(\d+)$", str(number))
    if not match:
        return ("", 0)
    return (match.group(1), int(match.group(2)))


def question_bank(questions: list[dict], subject: str = "math") -> dict:
    """Shape questions.json into the {topics, qs} blob the browser reads."""
    topics: dict[str, list[str]] = {}
    out = []
    for question in questions:
        text = question["text"]
        number = question["number"]
        marks = None
        headers = list(HEADER.finditer(text))
        own = next((header for header in headers if int(header.group(1)) == number), None)
        if own:
            marks = int(own.group(2))
            end = next(
                (
                    header.start()
                    for header in headers
                    if header.start() > own.start() and int(header.group(1)) != number
                ),
                len(text),
            )
            text = text[own.end() : end]
        elif isinstance(number, int):
            nxt = next((header.start() for header in headers if int(header.group(1)) == number + 1), None)
            if nxt:
                text = text[:nxt]
        for topic in question["topics"]:
            topics[topic["code"]] = [topic["topic"], topic["area"]]
        scheme_md = ROOT / "data" / "schemes" / f"{question['id']}.md"
        scheme = tidy_scheme(scheme_md.read_text()) if scheme_md.is_file() else ""
        row = {
            "i": question["id"],
            "y": question["year"],
            "s": question["session"],
            "p": paper_value(question["paper"]),
            "z": question["tz"],
            "n": number,
            "m": marks,
            "t": text.strip(),
            "c": [topic["code"] for topic in question["topics"]],
            "v": question["status"] == "matched",
            "a": question["page_start"],
            "b": question["page_end"],
            "k": scheme_md.is_file() or (ROOT / "data" / "schemes" / f"{question['id']}.png").is_file(),
        }
        if question.get("level"):
            row["l"] = question["level"]
        if subject != "math":
            row["u"] = subject
        if scheme:
            row["e"] = scheme
        out.append(row)
    out.sort(
        key=lambda item: (
            -item["y"],
            SESSION_ORDER.get(item["s"], 9),
            paper_rank(item["p"]),
            item["z"] or "",
            number_rank(item["n"]),
        )
    )
    return {"topics": topics, "qs": out}


def economics_catalog(root: Path | None = None) -> tuple[list[dict], dict[str, Path]]:
    """English economics question papers. Markschemes and other languages stay out."""
    base = ECON_ROOT if root is None else root
    papers: list[dict] = []
    files: dict[str, Path] = {}
    if not base.is_dir():
        return papers, files
    for path in sorted(base.rglob("*.pdf")):
        if path.parent.name != "en":
            continue
        match = ECON_NAME.fullmatch(path.name)
        if match is None:
            continue
        rel = path.relative_to(base)
        if len(rel.parts) != 4:
            continue
        level, session, _lang, _name = rel.parts
        year_s, _, month = session.partition("-")
        session_name = ECON_MONTH.get(month)
        if not year_s.isdigit() or session_name is None:
            continue
        tz = (match.group(2) or "").upper()
        zone = f"-{tz.lower()}" if tz else ""
        pid = f"econ-{level}-{year_s}-{month}-p{match.group(1)}{zone}"
        if pid in files:
            continue
        files[pid] = path
        papers.append(
            {
                "i": pid,
                "y": int(year_s),
                "s": session_name,
                "p": int(match.group(1)),
                "z": tz,
                "l": level,
                "u": "econ",
            }
        )
    return papers, files


_econ_cache: tuple[list[dict], dict[str, Path]] | None = None


def load_economics() -> tuple[list[dict], dict[str, Path]]:
    global _econ_cache
    if _econ_cache is None:
        _econ_cache = economics_catalog()
    return _econ_cache


def physics_papers(payload: dict, counts: dict[str, int]) -> list[dict]:
    rows = []
    for paper in payload.get("papers", []):
        rows.append(
            {
                "i": paper["id"],
                "y": paper["year"],
                "s": paper["session"],
                "p": paper_value(paper["paper"]),
                "z": paper.get("tz") or "",
                "n": counts.get(paper["id"], 0),
                "l": paper["level"],
                "u": "phys",
            }
        )
    return rows


def bank_json() -> bytes:
    payload = load_json(QUESTIONS, {"questions": []})
    bank = question_bank(payload.get("questions", []))
    physics = load_json(PHYSICS_QUESTIONS, {"questions": [], "papers": []})
    phys = question_bank(physics.get("questions", []), subject="phys")
    bank["qs"].extend(phys["qs"])
    bank["pt"] = phys["topics"]
    counts: dict[str, int] = {}
    for question in physics.get("questions", []):
        counts[question["paper_id"]] = counts.get(question["paper_id"], 0) + 1
    if physics.get("papers"):
        bank["pp"] = physics_papers(physics, counts)
    papers, _files = load_economics()
    if papers:
        bank["ps"] = papers
    return json.dumps(bank, ensure_ascii=False, separators=(",", ":")).encode()


_PAGE_PNG: dict[tuple, bytes] = {}
_PAPER_FILES: dict[str, Path] | None = None
_PAPER_MTIME: float | None = None
_THUMB_LOCKS: dict[str, threading.Lock] = {}


def page_count(path: Path) -> int:
    import pymupdf

    document = pymupdf.open(path)
    try:
        return document.page_count
    finally:
        document.close()


def page_png(path: Path, page: int, dpi: int = 100) -> bytes | None:
    """One PDF page as a PNG. None when the page number is outside the file."""
    import pymupdf

    if page < 1:
        return None
    key = (str(path), path.stat().st_mtime_ns, page, dpi)
    cached = _PAGE_PNG.get(key)
    if cached is not None:
        return cached
    document = pymupdf.open(path)
    try:
        if page > document.page_count:
            return None
        data = document[page - 1].get_pixmap(dpi=dpi, alpha=False).tobytes("png")
    finally:
        document.close()
    if len(_PAGE_PNG) > 40:
        _PAGE_PNG.pop(next(iter(_PAGE_PNG)))
    _PAGE_PNG[key] = data
    return data


def _thumb_file(path: Path, page: int, stamp: int) -> Path:
    digest = hashlib.sha1(f"{path}:{stamp}:{page}".encode()).hexdigest()[:20]
    return THUMBS / f"{digest}.jpg"


def thumb_jpeg(path: Path, page: int) -> bytes | None:
    """Small JPEG of one page, cached on disk. Page 1 also writes page 2 while the file is open."""
    if page < 1:
        return None
    stamp = path.stat().st_mtime_ns
    dest = _thumb_file(path, page, stamp)
    if dest.is_file():
        return dest.read_bytes()
    lock = _THUMB_LOCKS.setdefault(str(path), threading.Lock())
    with lock:
        if dest.is_file():
            return dest.read_bytes()
        import pymupdf

        document = pymupdf.open(path)
        try:
            count = document.page_count
            if page > count:
                return None
            numbers = [page]
            if page == 1 and count > 1 and not _thumb_file(path, 2, stamp).is_file():
                numbers.append(2)
            THUMBS.mkdir(parents=True, exist_ok=True)
            written: dict[int, bytes] = {}
            for number in numbers:
                target = _thumb_file(path, number, stamp)
                sheet = document[number - 1]
                zoom = 320 / sheet.rect.width
                data = sheet.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).tobytes("jpeg", jpg_quality=50)
                target.write_bytes(data)
                written[number] = data
        finally:
            document.close()
        return written.get(page)


def subject_pdf(paper_id: str) -> Path | None:
    """English economics or physics question paper. Markschemes stay out."""
    if not paper_id.startswith(("econ-", "phy-")):
        return None
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", paper_id):
        return None
    path = paper_files().get(paper_id)
    if path is None or not path.is_file() or "markscheme" in path.name.lower():
        return None
    return path


def write_paper_covers(files: dict[str, Path] | None = None, dest: Path | None = None) -> None:
    """Page 1 and 2 JPEGs named by paper id. An empty page 2 means the PDF is one page."""
    folder = dest or COVERS
    folder.mkdir(parents=True, exist_ok=True)
    for paper_id, path in (paper_files() if files is None else files).items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", paper_id):
            continue
        targets = [folder / f"{paper_id}-{page}.jpg" for page in (1, 2)]
        pdf_mtime = path.stat().st_mtime
        if all(target.is_file() and target.stat().st_mtime >= pdf_mtime for target in targets):
            continue
        for page, target in enumerate(targets, start=1):
            data = thumb_jpeg(path, page)
            target.write_bytes(data or b"")


def _question_mtime() -> tuple[float, float]:
    def stamp(path: Path) -> float:
        return path.stat().st_mtime if path.exists() else 0

    return (stamp(QUESTIONS), stamp(PHYSICS_QUESTIONS))


def _remember_pdf(files: dict[str, Path], root: Path, paper_id: str | None, file: str | None) -> None:
    if not paper_id or not file or paper_id in files:
        return
    path = (ROOT / file).resolve()
    if root in path.parents and path.is_file():
        files[paper_id] = path


def paper_files() -> dict[str, Path]:
    """paper id to PDF path. Rebuilt when a question bank changes."""
    global _PAPER_FILES, _PAPER_MTIME
    mtime = _question_mtime()
    if _PAPER_FILES is not None and _PAPER_MTIME == mtime:
        return _PAPER_FILES
    files: dict[str, Path] = {}
    root = ROOT.resolve()
    for question in load_json(QUESTIONS, {"questions": []}).get("questions", []):
        _remember_pdf(files, root, question.get("paper_id"), question.get("file"))
    physics = load_json(PHYSICS_QUESTIONS, {"questions": [], "papers": []})
    for question in physics.get("questions", []):
        _remember_pdf(files, root, question.get("paper_id"), question.get("file"))
    for paper in physics.get("papers", []):
        _remember_pdf(files, root, paper.get("id"), paper.get("file"))
    _papers, econ = load_economics()
    files.update(econ)
    _PAPER_FILES = files
    _PAPER_MTIME = mtime
    return files


def pdf_for(question_id: str | None, paper_id: str | None) -> Path | None:
    if paper_id and not question_id:
        return paper_files().get(paper_id)
    root = ROOT.resolve()
    for path in (QUESTIONS, PHYSICS_QUESTIONS):
        for question in load_json(path, {"questions": []}).get("questions", []):
            if question_id and question["id"] != question_id:
                continue
            if paper_id and question.get("paper_id") != paper_id:
                continue
            file = (ROOT / question["file"]).resolve()
            if root not in file.parents or not file.is_file():
                return None
            return file
    if paper_id:
        return paper_files().get(paper_id)
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} {fmt % args}")

    def send(self, code: int, body: bytes, content_type: str, cache: str | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send(200, b"Question browser runs from the Vite dev server. In web/: npm run dev\n", "text/plain; charset=utf-8")
            return
        if parsed.path == "/questions.json":
            self.send(200, bank_json(), "application/json")
            return
        if parsed.path == "/api/questions":
            payload = load_json(QUESTIONS, {"questions": []})
            flags = load_json(REVIEWS, {})
            for question in payload.get("questions", []):
                question["flagged"] = bool(flags.get(question["id"]))
                cleaned = tidy_question(question.get("text") or "", question.get("number") or 0)
                if cleaned:
                    question["text"] = cleaned
            coverage = load_json(COVERAGE, {})
            payload["coverage"] = {
                "present": coverage.get("present", 0),
                "missing": coverage.get("missing", 0),
                "needs_ocr": coverage.get("needs_ocr", 0),
                "total": len(coverage.get("papers", [])),
            }
            self.send(200, json.dumps(payload).encode(), "application/json")
            return
        if parsed.path == "/api/coverage":
            self.send(200, json.dumps(load_json(COVERAGE, {})).encode(), "application/json")
            return
        image_kind = {"cut": "cuts", "fig": "figs", "scheme": "schemes"}.get(parsed.path.split("/")[1] if parsed.path.startswith("/") else "")
        if image_kind and parsed.path.count("/") >= 2:
            kind = image_kind
            name = parsed.path.split("/", 2)[2]
            path = (ROOT / "data" / kind / name).resolve()
            if not CUT_NAME.fullmatch(name) or path.parent != (ROOT / "data" / kind).resolve() or not path.is_file():
                self.send(404, b"image not on disk", "text/plain; charset=utf-8")
                return
            self.send(200, path.read_bytes(), "image/png")
            return
        if parsed.path.startswith("/doc/"):
            name = parsed.path.split("/", 2)[2]
            paper_id = name[:-4] if name.endswith(".pdf") else ""
            path = subject_pdf(paper_id)
            if path is None:
                self.send(404, b"PDF not on disk", "text/plain; charset=utf-8")
                return
            self.send(200, path.read_bytes(), "application/pdf")
            return
        if parsed.path.startswith("/paper/"):
            name = parsed.path.split("/", 2)[2]
            path = (COVERS / name).resolve()
            if not COVER_NAME.fullmatch(name) or path.parent != COVERS.resolve() or not path.is_file() or path.stat().st_size == 0:
                self.send(404, b"image not on disk", "text/plain; charset=utf-8")
                return
            self.send(200, path.read_bytes(), "image/jpeg", "public, max-age=86400")
            return
        if parsed.path == "/pdf":
            query = parse_qs(parsed.query)
            path = pdf_for(
                query.get("question", [None])[0],
                query.get("paper", [None])[0],
            )
            if path is None:
                self.send(404, b"PDF not on disk", "text/plain; charset=utf-8")
                return
            page = query.get("page", [None])[0]
            if page is not None:
                if not page.isdigit():
                    self.send(400, b"bad page", "text/plain; charset=utf-8")
                    return
                if query.get("thumb", [None])[0] == "1":
                    jpg = thumb_jpeg(path, int(page))
                    if jpg is None:
                        self.send(404, b"page not in PDF", "text/plain; charset=utf-8")
                        return
                    self.send(200, jpg, "image/jpeg", "private, max-age=86400")
                    return
                png = page_png(path, int(page))
                if png is None:
                    self.send(404, b"page not in PDF", "text/plain; charset=utf-8")
                    return
                self.send(200, png, "image/png", "private, max-age=86400")
                return
            if query.get("count", [None])[0] == "1":
                self.send(200, json.dumps({"n": page_count(path)}).encode(), "application/json")
                return
            self.send(200, path.read_bytes(), "application/pdf")
            return
        self.send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/reviews":
            self.send(404, b"not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        qid = body.get("id")
        if not qid:
            self.send(400, b"missing id", "text/plain; charset=utf-8")
            return
        flags = load_json(REVIEWS, {})
        if body.get("flagged"):
            flags[qid] = True
        else:
            flags.pop(qid, None)
        REVIEWS.write_text(json.dumps(flags, indent=2) + "\n")
        self.send(200, json.dumps({"ok": True, "flagged": bool(flags.get(qid))}).encode(), "application/json")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
