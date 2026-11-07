"""Move local IB PDFs into papers/library/{group}/{subject}/{level}/{year-session}/{lang}/."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from collections import Counter
from pathlib import Path

from catalog import ROOT

SOURCE = ROOT / "papers" / "ib"
LIBRARY = ROOT / "papers" / "library"

GROUPS = (
    ("mathematics", "mathematics"),
    ("group 5", "mathematics"),
    ("maths", "mathematics"),
    ("experimental science", "sciences"),
    ("group 4", "sciences"),
    ("individuals and societ", "societies"),
    ("group 3", "societies"),
    ("language acquisition", "language-acquisition"),
    ("group 2", "language-acquisition"),
    ("language and literature", "language-literature"),
    ("studies in language", "language-literature"),
    ("group 1", "language-literature"),
    ("the arts", "arts"),
    ("group 6", "arts"),
)
SCIENCES = {"physics", "chemistry", "biology", "computer-science", "design-technology", "sports-exercise-and-health-science", "environmental-systems-and-societies", "nature-of-science"}
SOCIETIES = {"economics", "history", "geography", "psychology", "business-management", "global-politics", "philosophy", "social-and-cultural-anthropology", "digital-society", "world-religions"}
LANGS = (
    ("simplified chinese", "zh-hans"),
    ("traditional chinese", "zh-hant"),
    ("spanish", "es"),
    ("french", "fr"),
    ("german", "de"),
    ("chinese", "zh"),
    ("japanese", "ja"),
    ("arabic", "ar"),
    ("korean", "ko"),
    ("dutch", "nl"),
    ("swedish", "sv"),
    ("italian", "it"),
    ("portuguese", "pt"),
    ("indonesian", "id"),
    ("mandarin", "zh"),
)
ALIASES = {
    "bio": "biology",
    "chem": "chemistry",
    "phys": "physics",
    "econ": "economics",
    "compsci": "computer-science",
    "comp-sci": "computer-science",
    "math": "mathematics",
    "maths": "mathematics",
    "maths-aa": "mathematics-analysis-and-approaches",
    "phy": "physics",
    "geog": "geography",
    "bm": "business-management",
}
COURSES = {
    "aa": "analysis-and-approaches",
    "ai": "applications-and-interpretation",
}


def slug(text: str) -> str:
    text = text.lower().replace("_", "-").replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def session_of(path: str, stem: str) -> tuple[int | None, str | None]:
    match = re.search(r"(May|November)\s+(20\d\d)", path)
    if match:
        return int(match.group(2)), match.group(1)
    match = re.search(r"DONATED PAPERS\s+([MN])(\d{2})", path, re.I)
    if not match:
        match = re.search(r"(?:^|[_\s-])([MN])(\d{2})(?:$|[_\s.-])", stem)
    if match:
        return 2000 + int(match.group(2)), "May" if match.group(1).upper() == "M" else "November"
    return None, None


def group_of(path: str, subject: str) -> str:
    low = path.lower()
    for needle, group in GROUPS:
        if needle in low:
            return group
    if subject.startswith("mathematics") or subject.startswith("mathematical") or subject.startswith("further-mathematics"):
        return "mathematics"
    head = subject.split("-")[0]
    if head in SCIENCES or subject in SCIENCES:
        return "sciences"
    if head in SOCIETIES or subject in SOCIETIES:
        return "societies"
    if subject.endswith("-b") or "ab-initio" in subject or subject.endswith("-a"):
        return "language-acquisition"
    if "language-and-literature" in subject or subject.endswith("-a-literature"):
        return "language-literature"
    return "other"


def parse_stem(stem: str) -> dict:
    raw = stem.replace("[", " ").replace("]", " ")
    role = "markscheme" if re.search(r"markscheme|(?<![A-Za-z])MS(?![A-Za-z])", raw, re.I) else "paper"
    preset = None
    code = re.match(r"(?i)^(?:math[_\s-]*)?(aa|ai)(hl|sl)(?![a-z])", raw)
    if code:
        preset = "mathematics-" + COURSES[code.group(1).lower()]
        raw = ("hl" if code.group(2).lower() == "hl" else "sl") + " " + raw[code.end() :]
    work = re.sub(r"[_\s-]*markscheme", " ", raw, flags=re.I)
    work = re.sub(r"(?<![A-Za-z])MS(?![A-Za-z])", " ", work)
    lang = "en"
    for word, code in LANGS:
        if raw.lower().startswith(word):
            work = re.sub(rf"[_\s-]{re.escape(word)}(?![A-Za-z])", " ", work, count=1, flags=re.I)
            continue
        found = re.search(rf"[_\s-]{re.escape(word)}(?![A-Za-z])", work, re.I)
        if found and found.start() > 0:
            lang = code
            work = work[: found.start()] + " " + work[found.end() :]
            break
    level = "na"
    if re.search(r"HLSL|SLHL", work, re.I):
        level = "hlsl"
        work = re.sub(r"HLSL|SLHL", " ", work, flags=re.I)
    elif re.search(r"(?<![A-Za-z])HL(?![A-Za-z])", work, re.I):
        level = "hl"
        work = re.sub(r"(?<![A-Za-z])HL(?![A-Za-z])", " ", work, flags=re.I)
    elif re.search(r"(?<![A-Za-z])SL(?![A-Za-z])", work, re.I):
        level = "sl"
        work = re.sub(r"(?<![A-Za-z])SL(?![A-Za-z])", " ", work, flags=re.I)
    tz = None
    zone = re.search(r"(?:Zone|TZ)\s*([ABC])(?:\s*&\s*([ABC]))?", work, re.I)
    numbered = re.search(r"TZ\s*([123])", work, re.I)
    if zone:
        letters = {"A": "1", "B": "2", "C": "3"}
        tz = "tz" + letters[zone.group(1).upper()]
        if zone.group(2):
            tz += "-tz" + letters[zone.group(2).upper()]
        work = work[: zone.start()] + " " + work[zone.end() :]
    elif numbered:
        tz = "tz" + numbered.group(1)
        work = work[: numbered.start()] + " " + work[numbered.end() :]
    paper = None
    paper_m = re.search(r"paper[_\s-]*(\d+[a-z]?)", work, re.I) or re.search(
        r"(?<![A-Za-z])P[_\s-]*(\d+[a-z]?)(?![A-Za-z])", work, re.I
    )
    if paper_m:
        paper = paper_m.group(1).lower()
        work = work[: paper_m.start()] + " " + work[paper_m.end() :]
    kind = "doc"
    if re.search(r"listening", work, re.I):
        kind = "listening"
        work = re.sub(r"[_\s-]*listening(?:[_\s-]*comprehension)?", " ", work, flags=re.I)
    elif re.search(r"score", work, re.I) and re.search(r"booklet", work, re.I):
        kind = "score-booklet"
        work = re.sub(r"[_\s-]*score[_\s-]*booklet", " ", work, flags=re.I)
    elif paper:
        kind = "p" + paper
    work = re.sub(r"(?:^|[_\s-])[MN]\d{2}(?:$|[_\s-])", " ", work)
    subject = preset or ALIASES.get(slug(work), slug(work))
    if subject.endswith("-paper"):
        subject = subject[: -len("-paper")]
    short = re.match(r"^(?:math-)?(aa|ai)$", subject or "")
    if short:
        subject = "mathematics-" + COURSES[short.group(1)]
    return {"subject": subject or "unknown", "level": level, "lang": lang, "kind": kind, "tz": tz, "role": role}


def dest_for(path: Path) -> Path | None:
    year, session = session_of(str(path.parent), path.stem)
    parsed = parse_stem(path.stem)
    if year is None or session is None or parsed["subject"] == "unknown":
        return None
    month = "05" if session == "May" else "11"
    group = group_of(str(path.parent), parsed["subject"])
    name = parsed["kind"]
    if parsed["tz"]:
        name += "-" + parsed["tz"]
    if parsed["role"] == "markscheme":
        name += "-markscheme"
    return LIBRARY / group / parsed["subject"] / parsed["level"] / f"{year}-{month}" / parsed["lang"] / f"{name}.pdf"


def same_file(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    def digest(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    return digest(left) == digest(right)


def unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    number = 2
    while True:
        candidate = dest.with_name(f"{stem}--{number}{suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def pdfs() -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(SOURCE):
        dirnames[:] = [name for name in dirnames if name != "library"]
        for name in filenames:
            if name.lower().endswith(".pdf"):
                found.append(Path(dirpath) / name)
    return found


def sort_all(apply: bool) -> Counter:
    counts: Counter = Counter()
    subjects: Counter = Counter()
    planned: dict[Path, int] = {}
    for index, src in enumerate(pdfs(), 1):
        if index % 2000 == 0:
            print(f"{index}...", flush=True)
        dest = dest_for(src)
        size = src.stat().st_size
        if dest is None:
            counts["unplaced"] += 1
            if apply:
                kept = unique_dest(LIBRARY / "_unplaced" / src.name)
                kept.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(src, kept)
            continue
        subjects[str(Path(dest.relative_to(LIBRARY).parts[0]) / dest.relative_to(LIBRARY).parts[1])] += 1
        taken = dest.exists() or dest in planned
        same_size = (planned.get(dest) == size) or (dest.exists() and dest.stat().st_size == size)
        if taken and same_size and (not apply or same_file(src, dest)):
            counts["duplicate"] += 1
            if apply:
                src.unlink()
            continue
        if taken:
            dest = unique_dest(dest)
            while dest in planned:
                dest = unique_dest(dest)
            counts["variant"] += 1
        else:
            counts["moved"] += 1
        planned[dest] = size
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dest)
    if apply:
        for dirpath, dirnames, filenames in os.walk(SOURCE, topdown=False):
            if not dirnames and not filenames:
                os.rmdir(dirpath)
    counts["subjects"] = len(subjects)
    return counts


def main() -> None:
    import sys

    apply = "--apply" in sys.argv
    counts = sort_all(apply)
    print(("moved" if apply else "would move"), dict(counts))


if __name__ == "__main__":
    main()
