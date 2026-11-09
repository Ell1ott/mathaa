"""Pack the question browser into site/ for a static host."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog import ROOT  # noqa: E402
from serve import bank_page  # noqa: E402

SITE = ROOT / "site"


def copy_dir(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        dest.mkdir(parents=True)


def main() -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "index.html").write_bytes(bank_page())
    copy_dir(ROOT / "data" / "cuts", SITE / "cut")
    copy_dir(ROOT / "data" / "figs", SITE / "fig")
    copy_dir(ROOT / "data" / "schemes", SITE / "scheme")
    print(SITE)


if __name__ == "__main__":
    main()
