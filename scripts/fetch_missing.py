"""Download the missing Math AA HL papers from the pirateIB mirror."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from catalog import ROOT

BASE = "https://dl.pirateib.sh"
LIBRARY = (
    ROOT
    / "papers"
    / "library"
    / "mathematics"
    / "mathematics-analysis-and-approaches"
    / "hl"
)
SPECIMEN = (
    ROOT / "papers" / "official" / "dp-mathematics-analysis-and-approaches-specimen-papers-en.pdf"
)
SPECIMEN_PATH = (
    "IB SPECIMEN PAPERS/Group 5 - Mathematics/Analysis and Approaches/"
    "Specimen Papers 2021 - English.pdf"
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
)

# (year, session, paper, time zone) for every paper still listed as missing.
MISSING = [
    (2023, "May", 1, 2),
    (2023, "May", 2, 2),
    (2023, "May", 3, 2),
    (2024, "May", 1, 1),
    (2024, "May", 1, 2),
    (2024, "May", 2, 1),
    (2024, "May", 2, 2),
    (2024, "May", 3, 1),
    (2024, "May", 3, 2),
    (2025, "May", 1, 1),
    (2025, "May", 1, 2),
    (2025, "May", 1, 3),
    (2025, "May", 2, 1),
    (2025, "May", 2, 2),
    (2025, "May", 2, 3),
    (2025, "May", 3, 1),
    (2025, "May", 3, 2),
    (2025, "May", 3, 3),
    (2025, "November", 1, 1),
    (2025, "November", 1, 3),
    (2025, "November", 2, 1),
    (2025, "November", 2, 3),
    (2025, "November", 3, 1),
    (2025, "November", 3, 3),
    (2026, "May", 1, 1),
    (2026, "May", 1, 2),
    (2026, "May", 1, 3),
    (2026, "May", 2, 1),
    (2026, "May", 2, 2),
    (2026, "May", 2, 3),
    (2026, "May", 3, 1),
    (2026, "May", 3, 2),
    (2026, "May", 3, 3),
]


def selected(year: int | None, session: str | None) -> list[tuple]:
    rows = MISSING
    if year is not None:
        rows = [row for row in rows if row[0] == year]
    if session is not None:
        rows = [row for row in rows if row[1] == session]
    return rows


def cookie_value(args: argparse.Namespace) -> str:
    if args.cookie:
        return args.cookie
    env = os.environ.get("CF_CLEARANCE") or os.environ.get("PIRATEIB_COOKIE")
    if env:
        return env if "=" in env else f"cf_clearance={env}"
    for path in (
        Path(args.cookie_file) if args.cookie_file else None,
        ROOT / ".cf_clearance",
        Path.home() / ".config" / "pirateib" / "cf_clearance",
    ):
        if path and path.exists():
            value = path.read_text().strip()
            if value:
                return value
    raise SystemExit(
        "No cookie. Copy the cf_clearance cookie for dl.pirateib.sh from your browser "
        "and pass --cookie, set CF_CLEARANCE, or save it to .cf_clearance."
    )


def get_json(path: str, cookie: str, user_agent: str) -> list[dict] | None:
    url = f"{BASE}/{urllib.parse.quote(path, safe='/')}/?json"
    request = urllib.request.Request(
        url,
        headers={
            "Cookie": cookie,
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read()).get("paths", [])
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code == 403:
                raise SystemExit(
                    "Cloudflare rejected the request. Refresh the cf_clearance cookie "
                    "for dl.pirateib.sh and try again."
                ) from error
            if attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(1 + attempt)
    return None


def listing_for(
    year: int, session: str, cookie: str, user_agent: str, cache: dict
) -> tuple[str, list[dict]]:
    key = (year, session)
    if key in cache:
        return cache[key]
    stamp = f"{session} {year} Examination Session"
    root = f"IB PAST PAPERS - YEAR/{year} Examination Session/{stamp}"
    for suffix in ("files and resources/Mathematics", "PDFs/Mathematics", "Mathematics"):
        folder = f"{root}/{suffix}"
        entries = get_json(folder, cookie, user_agent)
        if entries is not None:
            cache[key] = (folder, entries)
            return cache[key]
    raise SystemExit(f"No Mathematics folder found for {stamp}")


def pick(entries: list[dict], paper: int, tz: int, markscheme: bool) -> str | None:
    for entry in entries:
        if entry.get("path_type") != "File":
            continue
        name = entry["name"]
        low = name.lower()
        if "analysis_and_approaches" not in low:
            continue
        if ("markscheme" in low) != markscheme:
            continue
        if any(language in low for language in ("german", "french", "spanish")):
            continue
        if not re.search(rf"paper[_\s-]*{paper}(?![0-9])", low):
            continue
        if not re.search(rf"tz[_\s-]*{tz}(?![0-9])", low):
            continue
        if not re.search(r"(?<![a-z])hl(?![a-z])", low):
            continue
        return name
    return None


def destination(year: int, session: str, paper: int, tz: int, markscheme: bool) -> Path:
    month = "05" if session == "May" else "11"
    name = f"p{paper}-tz{tz}"
    if markscheme:
        name += "-markscheme"
    return LIBRARY / f"{year}-{month}" / "en" / f"{name}.pdf"


def download(url: str, dest: Path, cookie: str, user_agent: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Cookie": cookie,
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = response.read()
            break
        except urllib.error.HTTPError as error:
            if error.code == 403:
                raise SystemExit(
                    "Cloudflare rejected the download. Refresh the cf_clearance cookie "
                    "for dl.pirateib.sh and try again."
                ) from error
            if attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(1 + attempt)
    if data[:4] != b"%PDF":
        raise RuntimeError(f"not a PDF: {url}")
    existed = dest.exists()
    if existed and dest.read_bytes() == data:
        return "identical"
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(".part")
    temporary.write_bytes(data)
    temporary.replace(dest)
    return "updated" if existed else "downloaded"


def fetch_specimen(cookie: str, user_agent: str, dry_run: bool) -> str:
    if SPECIMEN.exists() and SPECIMEN.stat().st_size > 100_000:
        if SPECIMEN.read_bytes()[:4] == b"%PDF":
            return "identical"
    if dry_run:
        return "planned"
    url = f"{BASE}/{urllib.parse.quote(SPECIMEN_PATH, safe='/')}"
    return download(url, SPECIMEN, cookie, user_agent)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cookie", help="cf_clearance cookie value")
    parser.add_argument("--cookie-file", help="file holding the cf_clearance cookie")
    parser.add_argument(
        "--user-agent",
        default=os.environ.get("PIRATEIB_USER_AGENT", USER_AGENT),
        help="user agent bound to the cf_clearance cookie",
    )
    parser.add_argument(
        "--markschemes", action="store_true", help="also download markschemes"
    )
    parser.add_argument("--year", type=int, help="only this exam year, for example 2025")
    parser.add_argument("--session", choices=("May", "November"), help="only this session")
    parser.add_argument("--dry-run", action="store_true", help="print without downloading")
    args = parser.parse_args()

    cookie = cookie_value(args)
    cache: dict = {}
    counts = {"downloaded": 0, "updated": 0, "identical": 0, "planned": 0, "missing": 0}

    if args.year is None and args.session is None:
        result = fetch_specimen(cookie, args.user_agent, args.dry_run)
        counts[result] += 1
        print(f"  {result:10} Specimen 2021 Paper 1, 2 and 3 -> {SPECIMEN.relative_to(ROOT)}")

    roles = [False, True] if args.markschemes else [False]
    rows = selected(args.year, args.session)
    if not rows:
        raise SystemExit(f"No papers listed for {args.session or ''} {args.year or ''}".strip())
    for year, session, paper, tz in rows:
        folder, entries = listing_for(year, session, cookie, args.user_agent, cache)
        for markscheme in roles:
            name = pick(entries, paper, tz, markscheme)
            suffix = " markscheme" if markscheme else ""
            label = f"{session} {year} Paper {paper} TZ{tz}{suffix}"
            if not name:
                print(f"  {'NOT FOUND':10} {label}")
                counts["missing"] += 1
                continue
            dest = destination(year, session, paper, tz, markscheme)
            already = False
            if dest.is_file() and dest.stat().st_size > 100_000:
                with dest.open("rb") as handle:
                    already = handle.read(4) == b"%PDF"
            if already:
                print(f"  {'identical':10} {label} -> {dest.relative_to(ROOT)}")
                counts["identical"] += 1
                continue
            if args.dry_run:
                print(f"  {'would get':10} {label} -> {dest.relative_to(ROOT)}")
                counts["planned"] += 1
                continue
            url = f"{BASE}/{urllib.parse.quote(f'{folder}/{name}', safe='/')}"
            result = download(url, dest, cookie, args.user_agent)
            counts[result] += 1
            print(f"  {result:10} {label} -> {dest.relative_to(ROOT)}")

    print(
        "done: "
        + ", ".join(f"{name}={count}" for name, count in counts.items() if count)
    )
    print("next: python scripts/build.py")


if __name__ == "__main__":
    main()
