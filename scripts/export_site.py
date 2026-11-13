"""Pack the question browser into site/ for a static host."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog import ROOT  # noqa: E402
from serve import bank_json, paper_files, subject_pdf, write_paper_covers  # noqa: E402

SITE = ROOT / "site"
DIST = ROOT / "web" / "dist"


def copy_dir(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        dest.mkdir(parents=True)


def main() -> None:
    if not (DIST / "index.html").is_file():
        raise SystemExit("web/dist is missing. Run npm run build in web/.")
    if SITE.exists():
        shutil.rmtree(SITE)
    shutil.copytree(DIST, SITE)
    (SITE / "questions.json").write_bytes(bank_json())
    write_paper_covers()
    copy_dir(ROOT / "data" / "covers", SITE / "paper")
    docs = SITE / "doc"
    docs.mkdir(parents=True, exist_ok=True)
    for paper_id in paper_files():
        path = subject_pdf(paper_id)
        if path is not None:
            shutil.copy2(path, docs / f"{paper_id}.pdf")
    copy_dir(ROOT / "data" / "cuts", SITE / "cut")
    copy_dir(ROOT / "data" / "figs", SITE / "fig")
    copy_dir(ROOT / "data" / "schemes", SITE / "scheme")
    print(SITE)


if __name__ == "__main__":
    main()
