"""Write the browser bank once for the Vite dev server."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog import ROOT  # noqa: E402
from serve import PHYSICS_QUESTIONS, QUESTIONS, bank_json, load_json, paper_files  # noqa: E402

CACHE = ROOT / "web" / ".cache"
SCHEMES = ROOT / "data" / "schemes"
ECON = ROOT / "papers" / "library" / "societies" / "economics"


def newest(path: Path) -> float:
    if not path.exists():
        return 0
    latest = path.stat().st_mtime
    if path.is_file():
        return latest
    for child in path.rglob("*"):
        if child.is_file():
            latest = max(latest, child.stat().st_mtime)
    return latest


def sources_mtime() -> float:
    return max(newest(QUESTIONS), newest(PHYSICS_QUESTIONS), newest(SCHEMES), newest(ECON))


def rel(path: Path) -> str | None:
    root = ROOT.resolve()
    resolved = path.resolve()
    if root not in resolved.parents or not resolved.is_file():
        return None
    return resolved.relative_to(root).as_posix()


def file_index() -> dict[str, str]:
    """Question id and paper id to a repo-relative PDF path."""
    files: dict[str, str] = {}
    for paper_id, path in paper_files().items():
        name = rel(path)
        if name:
            files[paper_id] = name
    for source in (QUESTIONS, PHYSICS_QUESTIONS):
        for question in load_json(source, {"questions": []}).get("questions", []):
            qid = question.get("id")
            if not qid or qid in files:
                continue
            paper_id = question.get("paper_id")
            if paper_id and paper_id in files:
                files[qid] = files[paper_id]
                continue
            file = question.get("file")
            if file:
                name = rel(ROOT / file)
                if name:
                    files[qid] = name
    return files


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    stamp_path = CACHE / "stamp"
    bank_path = CACHE / "questions.json"
    files_path = CACHE / "files.json"
    latest = sources_mtime()
    if bank_path.is_file() and files_path.is_file() and stamp_path.is_file():
        try:
            if float(stamp_path.read_text()) >= latest:
                return
        except ValueError:
            pass
    bank_path.write_bytes(bank_json())
    files_path.write_text(json.dumps(file_index(), separators=(",", ":")))
    stamp_path.write_text(repr(latest))


if __name__ == "__main__":
    main()
