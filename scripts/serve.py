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
LIBRARY = ROOT / "papers" / "library"
ECON_ROOT = LIBRARY / "societies" / "economics"
ECON_NAME = re.compile(r"^p(\d+)(?:-(tz\d+))?\.pdf$", re.I)
ECON_MONTH = {"05": "May", "11": "November"}
# Physics and Economics already have their own banks. Math AA HL stays on the question bank.
LIBRARY_SKIP = {("sciences", "physics"), ("societies", "economics")}
MATH_AA = ("mathematics", "mathematics-analysis-and-approaches")
LIBRARY_GROUPS = (
    ("mathematics", "Mathematics"),
    ("sciences", "Sciences"),
    ("societies", "Individuals and societies"),
    ("language-acquisition", "Language acquisition"),
    ("language-literature", "Studies in language and literature"),
    ("arts", "Arts"),
)
_LABEL_SMALL = {"ab", "and", "of", "the", "in", "initio"}
_PAPER_STEM = re.compile(r"^p(\d+)([ab])?(?:-(tz\d+))?(?:-(.+))?$", re.I)
_LISTEN_STEM = re.compile(r"^listening(?:-(tz\d+))?(?:-(.+))?$", re.I)
_ID_PART = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IB_AUDIO = ROOT / "papers" / "ib"
# m242abspaslispatz0xxl: May 2024, language B Spanish, SL, no time zone.
_AUDIO_NAME = re.compile(r"^([mn])(\d{2})\d([a-z]{2})([a-z]{3})(hl|sl)i[a-z]{3}tz(\d)([a-z]{2})l$", re.I)
_AUDIO_LANG = {
    "spa": "spanish",
    "eng": "english",
    "fre": "french",
    "ger": "german",
    "jpn": "japanese",
    "ind": "indonesian",
    "ita": "italian",
    "ara": "arabic",
    "kor": "korean",
    "swe": "swedish",
    "rus": "russian",
    "nor": "norwegian",
    "fin": "finnish",
    "dan": "danish",
    "dut": "dutch",
    "hin": "hindi",
    "por": "portuguese",
    "heb": "hebrew",
    "tam": "tamil",
    "mal": "malay",
}


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


def subject_label(slug: str) -> str:
    words = []
    for index, word in enumerate(slug.split("-")):
        if len(word) == 1:
            words.append(word.upper())
        elif index and word in _LABEL_SMALL:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def parse_library_name(name: str) -> tuple[str, int | str, str, str] | None:
    """Return (id fragment, paper, tz, component). None skips markschemes and odd names."""
    if not name.lower().endswith(".pdf") or "markscheme" in name.lower() or "--" in name:
        return None
    stem = name[:-4]
    heard = _LISTEN_STEM.fullmatch(stem)
    numbered = _PAPER_STEM.fullmatch(stem)
    if heard:
        tz = (heard.group(1) or "").lower()
        component = (heard.group(2) or "").lower()
        paper: int | str = "Listening"
        fragment = "listening"
    elif numbered:
        tz = (numbered.group(3) or "").lower()
        component = (numbered.group(4) or "").lower()
        letter = (numbered.group(2) or "").lower()
        fragment = f"p{numbered.group(1)}{letter}"
        paper = f"{numbered.group(1)}{letter.upper()}" if letter else int(numbered.group(1))
    else:
        return None
    if component and not _ID_PART.fullmatch(component):
        return None
    if tz:
        fragment += f"-{tz}"
    if component:
        fragment += f"-{component}"
    if not _ID_PART.fullmatch(fragment):
        return None
    return fragment, paper, tz, component


def audio_subjects(kind: str, lang: str, variant: str) -> list[str]:
    """IB audio codes use ab for language B and an for ab initio."""
    if kind == "ab" and lang == "chi" and variant == "ca":
        return ["chinese-b-cantonese"]
    if kind == "ab" and lang == "chi":
        return ["chinese-b"]
    if (kind == "an" and lang == "man") or (kind == "ab" and lang == "cma"):
        return ["mandarin-ab-initio"]
    if kind == "ab" and lang == "cca":
        return ["chinese-b-cantonese"]
    if lang == "swa":
        tail = "b" if kind == "ab" else "ab-initio"
        return [f"swahili-{tail}", f"kiswahili-{tail}"]
    name = _AUDIO_LANG.get(lang)
    if not name or kind not in {"ab", "an"}:
        return []
    return [f"{name}-b" if kind == "ab" else f"{name}-ab-initio"]


def _prefer_audio(old: Path | None, new: Path) -> Path:
    if old is None or ("HTML" in old.parts and "HTML" not in new.parts):
        return new
    return old


def listening_audio(root: Path | None = None) -> dict[tuple, Path]:
    """Map (subject, level, year, session, time zone) to one mp3."""
    base = IB_AUDIO if root is None else root
    found: dict[tuple, Path] = {}
    if not base.is_dir():
        return found
    for path in base.rglob("*.mp3"):
        match = _AUDIO_NAME.match(path.stem)
        if match is None:
            continue
        session, yy, kind, lang, level, tz, variant = (part.lower() for part in match.groups())
        tail = (
            level,
            2000 + int(yy),
            "May" if session == "m" else "November",
            "" if tz == "0" else f"TZ{tz}",
        )
        for subject in audio_subjects(kind, lang, variant):
            key = (subject, *tail)
            found[key] = _prefer_audio(found.get(key), path)
    return found


_TRACK_NAME = re.compile(r"^track (\d+)$", re.I)
_TRACK_SESSION = re.compile(r"(May|November) (20\d\d)")


def music_tracks(root: Path | None = None) -> dict[tuple[int, str], list[Path]]:
    """Session tracks named Track 1.mp3 and so on, shared by the music listening papers."""
    base = IB_AUDIO if root is None else root
    found: dict[tuple[int, str], dict[int, Path]] = {}
    if not base.is_dir():
        return {}
    for path in base.rglob("*.mp3"):
        match = _TRACK_NAME.match(path.stem)
        where = _TRACK_SESSION.search(str(path))
        if match is None or where is None:
            continue
        key = (int(where.group(2)), where.group(1))
        slot = found.setdefault(key, {})
        number = int(match.group(1))
        slot[number] = _prefer_audio(slot.get(number), path)
    return {key: [slot[number] for number in sorted(slot)] for key, slot in found.items()}


def library_catalog(
    root: Path | None = None, audio: dict[tuple, Path] | None = None
) -> tuple[list[dict], dict[str, Path], list[list[str]], dict[str, list[Path]]]:
    """English question papers for every course that is not already its own bank."""
    base = LIBRARY if root is None else root
    papers: list[dict] = []
    files: dict[str, Path] = {}
    heard: dict[str, list[Path]] = {}
    found: dict[str, list[str]] = {}
    clips = audio if audio is not None else (listening_audio() if root is None else {})
    tracks = music_tracks() if root is None and audio is None else {}
    if not base.is_dir():
        return papers, files, [], heard
    for path in sorted(base.rglob("*.pdf")):
        if path.parent.name != "en":
            continue
        rel = path.relative_to(base)
        if len(rel.parts) != 6:
            continue
        group, subject, level, session, _lang, name = rel.parts
        if (group, subject) in LIBRARY_SKIP:
            continue
        parsed = parse_library_name(name)
        if parsed is None:
            continue
        year_s, _, month = session.partition("-")
        session_name = ECON_MONTH.get(month)
        if not year_s.isdigit() or session_name is None or not _ID_PART.fullmatch(level):
            continue
        if (group, subject) == MATH_AA:
            if level != "sl":
                continue
            sid, label = "math-aa-sl", "Math AA SL"
        else:
            if not _ID_PART.fullmatch(subject):
                continue
            sid, label = subject, subject_label(subject)
        fragment, paper, tz, component = parsed
        pid = f"{sid}-{level}-{year_s}-{month}-{fragment}"
        if not _ID_PART.fullmatch(pid) or pid in files:
            continue
        files[pid] = path
        row = {
            "i": pid,
            "y": int(year_s),
            "s": session_name,
            "p": paper,
            "z": tz.upper() if tz else "",
            "l": level,
            "u": sid,
        }
        if component:
            row["k"] = component
        if row["p"] == "Listening" and sid == "music":
            pieces = tracks.get((int(year_s), session_name))
            if pieces:
                row["au"] = len(pieces)
                heard[pid] = pieces
        elif row["p"] == "Listening":
            clip = clips.get((sid, level, int(year_s), session_name, row["z"]))
            if clip is not None:
                row["au"] = 1
                heard[pid] = [clip]
        papers.append(row)
        found.setdefault(sid, [label, dict(LIBRARY_GROUPS).get(group, "Other")])
    group_order = {name: index for index, (_key, name) in enumerate(LIBRARY_GROUPS)}
    subs = [[sid, label, group] for sid, (label, group) in found.items()]
    subs.sort(key=lambda row: (group_order.get(row[2], 9), row[1].lower()))
    return papers, files, subs, heard


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


_library_cache: tuple[list[dict], dict[str, Path], list[list[str]]] | None = None


def load_library() -> tuple[list[dict], dict[str, Path], list[list[str]], dict[str, list[Path]]]:
    global _library_cache
    if _library_cache is None:
        _library_cache = library_catalog()
    return _library_cache


def shipped_paper_files() -> dict[str, Path]:
    """Math, Physics, and Economics only. The rest of the library stays on this machine."""
    files = dict(paper_files())
    for paper_id in load_library()[1]:
        files.pop(paper_id, None)
    return files


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
    econ_papers, _files = load_economics()
    library_papers, _lib_files, subs, _audio = load_library()
    papers = econ_papers + library_papers
    if papers:
        bank["ps"] = papers
    if subs:
        bank["subs"] = subs
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


def listening_audio_file(paper_id: str, index: int = 0) -> Path | None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", paper_id) or index < 0:
        return None
    group = load_library()[3].get(paper_id) or []
    if index >= len(group):
        return None
    path = group[index]
    if not path.is_file() or path.suffix.lower() != ".mp3":
        return None
    resolved = path.resolve()
    if ROOT.resolve() not in resolved.parents:
        return None
    return resolved


def subject_pdf(paper_id: str) -> Path | None:
    """Question paper for any subject. Markschemes stay out."""
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
    _library, library, _subs, _audio = load_library()
    files.update(library)
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
        if parsed.path.startswith("/audio/"):
            rest = parsed.path[len("/audio/") :]
            paper_id, _, index_s = rest.partition("/")
            if index_s and not index_s.isdigit():
                self.send(404, b"audio not on disk", "text/plain; charset=utf-8")
                return
            path = listening_audio_file(paper_id, int(index_s) if index_s else 0)
            if path is None:
                self.send(404, b"audio not on disk", "text/plain; charset=utf-8")
                return
            self.send(200, path.read_bytes(), "audio/mpeg")
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
