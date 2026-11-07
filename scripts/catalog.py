"""Expected English Math AA HL papers, May 2021 through May 2026, plus the 2021 specimen."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "catalog.json"

AREAS = {
    "1": "Number and algebra",
    "2": "Functions",
    "3": "Geometry and trigonometry",
    "4": "Statistics and probability",
    "5": "Calculus",
}

# Time zones are not the same every session. Counts: 3+6+3+6+3+6+3+6+3+9+6+9 = 63.
SESSIONS = [
    (2021, "Specimen", [None]),
    (2021, "May", ["TZ1", "TZ2"]),
    (2021, "November", [None]),
    (2022, "May", ["TZ1", "TZ2"]),
    (2022, "November", [None]),
    (2023, "May", ["TZ1", "TZ2"]),
    (2023, "November", [None]),
    (2024, "May", ["TZ1", "TZ2"]),
    (2024, "November", [None]),
    (2025, "May", ["TZ1", "TZ2", "TZ3"]),
    (2025, "November", ["TZ1", "TZ3"]),
    (2026, "May", ["TZ1", "TZ2", "TZ3"]),
]


def paper_id(year: int, session: str, paper: int, tz: str | None) -> str:
    if session == "Specimen":
        return f"specimen-{year}-p{paper}"
    month = "05" if session == "May" else "11"
    zone = f"-{tz.lower()}" if tz else ""
    return f"{year}-{month}-p{paper}{zone}"


def paper_label(year: int, session: str, paper: int, tz: str | None) -> str:
    zone = f" {tz}" if tz else ""
    return f"{session} {year} Paper {paper}{zone}"


def build_catalog() -> list[dict]:
    papers = []
    for year, session, zones in SESSIONS:
        for paper in (1, 2, 3):
            for tz in zones:
                papers.append(
                    {
                        "id": paper_id(year, session, paper, tz),
                        "year": year,
                        "session": session,
                        "paper": paper,
                        "tz": tz,
                        "label": paper_label(year, session, paper, tz),
                        "source": "official" if session == "Specimen" else "inbox",
                    }
                )
    if len(papers) != 63:
        raise RuntimeError(f"expected 63 papers, got {len(papers)}")
    return papers


def write_catalog() -> list[dict]:
    papers = build_catalog()
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(papers, indent=2) + "\n")
    return papers


def load_catalog() -> list[dict]:
    if not CATALOG_PATH.exists():
        return write_catalog()
    return json.loads(CATALOG_PATH.read_text())


if __name__ == "__main__":
    papers = write_catalog()
    print(f"wrote {len(papers)} papers to {CATALOG_PATH}")
