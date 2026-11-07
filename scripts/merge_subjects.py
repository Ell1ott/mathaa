"""Fold nickname and booklet folders into the subject they actually belong to."""

from __future__ import annotations

import shutil
from pathlib import Path

from catalog import ROOT

LIBRARY = ROOT / "papers" / "library"
COMPONENTS = (
    "reading-comprehension-question-booklet",
    "reading-comprehension-text-booklet",
    "reading-comprehension",
    "pre-released-statement",
    "question-booklet",
    "text-booklet",
    "resource-booklet",
    "resources-booklet",
    "source-booklet",
    "case-study",
)


def plan(group: str, subject: str) -> tuple[str, str, str | None, str | None] | None:
    """Return (group, subject, filename tag, forced level), or None to leave it."""
    aliases = {
        ("mathematics", "math-aahl"): ("mathematics", "mathematics-analysis-and-approaches", None, "hl"),
        ("mathematics", "mathematics-aa-tz0"): ("mathematics", "mathematics-analysis-and-approaches", "tz0", None),
        ("mathematics", "mathematics-analysis-and-approaches-tz0"): (
            "mathematics",
            "mathematics-analysis-and-approaches",
            "tz0",
            None,
        ),
        ("mathematics", "nov-2022-ai"): ("mathematics", "mathematics-applications-and-interpretation", None, None),
        ("mathematics", "computer-science"): ("sciences", "computer-science", None, None),
        ("mathematics", "computer-science-case-study"): ("sciences", "computer-science", "case-study", None),
        ("sciences", "nov-2022-cs"): ("sciences", "computer-science", None, None),
        ("sciences", "nov-22-physics"): ("sciences", "physics", None, None),
        ("societies", "geography-asia-leak"): ("societies", "geography", "leak", None),
        ("other", "chem-leak"): ("sciences", "chemistry", "leak", None),
        ("other", "chem-sl-and"): ("sciences", "chemistry", None, None),
        ("other", "ib-biology-2024"): ("sciences", "biology", None, None),
        ("other", "chi-l-and-l"): ("language-literature", "chinese-a-language-and-literature", None, None),
        ("other", "chinese-a-l-and-l"): ("language-literature", "chinese-a-language-and-literature", None, None),
        ("other", "chinese-abinitio"): ("language-acquisition", "mandarin-ab-initio", None, None),
        ("other", "mandarin-ab"): ("language-acquisition", "mandarin-ab-initio", None, None),
        ("other", "compsci-case-study"): ("sciences", "computer-science", "case-study", None),
        ("other", "digital-society-spanish"): ("societies", "digital-society", None, None),
        ("other", "eng-b-reading"): ("language-acquisition", "english-b", "reading", None),
        ("other", "eng-b-reading-text-booklet"): ("language-acquisition", "english-b", "reading-text-booklet", None),
        ("other", "english-b-reading-comprehension-question-booklet"): (
            "language-acquisition",
            "english-b",
            "reading-comprehension-question-booklet",
            None,
        ),
        ("other", "english-b-reading-comprehension-text-booklet"): (
            "language-acquisition",
            "english-b",
            "reading-comprehension-text-booklet",
            None,
        ),
        ("other", "english-a-lang-and-lit"): ("language-literature", "english-a-language-and-literature", None, None),
        ("other", "english-lang-and-lit"): ("language-literature", "english-a-language-and-literature", None, None),
        ("other", "english-a-literature-tz0"): ("language-literature", "english-a-literature", "tz0", None),
        ("other", "spanish-a-lit"): ("language-literature", "spanish-a-literature", None, None),
        ("other", "business-management-case-study"): ("societies", "business-management", "case-study", None),
        ("language-acquisition", "eng-b"): ("language-acquisition", "english-b", None, None),
        ("language-acquisition", "may-2025-polish-a"): ("language-literature", "polish-a-literature", None, None),
        ("language-literature", "vietmanese-a-language-and-literature"): (
            "language-literature",
            "vietnamese-a-language-and-literature",
            None,
            None,
        ),
        ("societies", "global-politics-2-3"): ("societies", "global-politics", None, None),
    }
    if (group, subject) in aliases:
        return aliases[(group, subject)]
    if group == "language-literature" and subject.endswith("-a1"):
        return group, subject[: -len("-a1")] + "-a-literature", None, None
    if subject.endswith("-tz0"):
        return group, subject[: -len("-tz0")], "tz0", None
    if subject.endswith("-tz-b"):
        return group, subject[: -len("-tz-b")], "tz2", None
    if subject.startswith("history-route-2"):
        return "societies", "history", subject[len("history-") :], None
    for component in COMPONENTS:
        suffix = "-" + component
        if subject.endswith(suffix) and subject != component:
            return group, subject[: -len(suffix)], component, None
    return None


def tagged_name(filename: str, tag: str | None) -> str:
    if not tag:
        return filename
    stem = filename[:-4] if filename.lower().endswith(".pdf") else filename
    if tag == "tz2" and "-tz" not in stem:
        return f"{stem}-tz2.pdf"
    if tag in stem:
        return filename if filename.lower().endswith(".pdf") else stem + ".pdf"
    return f"{stem}-{tag}.pdf"


def unique(dest: Path) -> Path:
    stem, suffix = dest.stem, dest.suffix
    number = 2
    while True:
        candidate = dest.with_name(f"{stem}--{number}{suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def merge(apply: bool) -> dict[str, int]:
    counts = {"moved": 0, "duplicate": 0, "variant": 0, "folders": 0}
    for group_dir in sorted(path for path in LIBRARY.iterdir() if path.is_dir()):
        for subject_dir in sorted(path for path in group_dir.iterdir() if path.is_dir()):
            decided = plan(group_dir.name, subject_dir.name)
            if decided is None:
                continue
            new_group, new_subject, tag, level = decided
            if (new_group, new_subject) == (group_dir.name, subject_dir.name):
                continue
            counts["folders"] += 1
            for src in sorted(subject_dir.rglob("*.pdf")):
                rel = src.relative_to(subject_dir)
                parts = list(rel.parts)
                if level and parts:
                    parts[0] = level
                parts[-1] = tagged_name(parts[-1], tag)
                dest = LIBRARY / new_group / new_subject / Path(*parts)
                if dest.exists():
                    if dest.stat().st_size == src.stat().st_size:
                        counts["duplicate"] += 1
                        if apply:
                            src.unlink()
                        continue
                    dest = unique(dest)
                    counts["variant"] += 1
                else:
                    counts["moved"] += 1
                if apply:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(src, dest)
            if apply:
                for dirpath, dirnames, filenames in __import__("os").walk(subject_dir, topdown=False):
                    if not dirnames and not filenames:
                        Path(dirpath).rmdir()
    return counts


def main() -> None:
    import sys

    print(merge("--apply" in sys.argv))


if __name__ == "__main__":
    main()
