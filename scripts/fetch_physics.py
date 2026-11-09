"""Download missing Physics HL/SL papers from the pirateIB mirror.

Mirrors the layout in papers/library/sciences/physics/{level}/{yyyy-mm}/{lang}/.
The cf_clearance cookie for dl.pirateib.sh is required (see fetch_missing.py).
"""

from __future__ import annotations

import argparse
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from catalog import ROOT

BASE = "https://dl.pirateib.sh"
LIBRARY = ROOT / "papers" / "library" / "sciences" / "physics"
SUBJECT = "IB PAST PAPERS - SUBJECT/Group 4 - Sciences"
YEAR = "IB PAST PAPERS - YEAR"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
)

ZONES = {"a": "1", "b": "2", "c": "3", "1": "1", "2": "2", "3": "3"}
LANGS = (("spanish", "es"), ("french", "fr"), ("german", "de"))


def cookie_value(args: argparse.Namespace) -> str:
    if args.cookie:
        return args.cookie
    env = os.environ.get("CF_CLEARANCE") or os.environ.get("PIRATEIB_COOKIE")
    if env:
        return env if "=" in env else f"cf_clearance={env}"
    path = ROOT / ".cf_clearance"
    if path.exists() and path.read_text().strip():
        value = path.read_text().strip()
        return value if "=" in value else f"cf_clearance={value}"
    raise SystemExit(
        "No cookie. Pass --cookie, set CF_CLEARANCE, or save cf_clearance to .cf_clearance."
    )


def get_json(path: str, cookie: str) -> list[dict] | None:
    url = f"{BASE}/{urllib.parse.quote(path, safe='/')}/?json"
    request = urllib.request.Request(
        url,
        headers={
            "Cookie": cookie,
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
            try:
                return __import__("json").loads(raw).get("paths", [])
            except ValueError:
                return None
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code == 403:
                raise SystemExit("Cloudflare rejected the listing. Refresh cf_clearance.") from error
            if attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(1 + attempt)
    return None


def physics_files(folder: str, cookie: str) -> list[str]:
    entries = get_json(folder, cookie)
    if not entries:
        return []
    return [
        entry["name"]
        for entry in entries
        if entry.get("path_type") == "File"
        and entry["name"].lower().endswith(".pdf")
        and "physic" in entry["name"].lower()
    ]


def sources(cookie: str) -> list[tuple[str, str, list[str]]]:
    """Return (year, month, [folders]) for every place physics papers live."""
    out: list[tuple[str, str, list[str]]] = []
    for level in ("Physics_HL", "Physics_SL"):
        entries = get_json(f"{SUBJECT}/{level}", cookie) or []
        for entry in entries:
            if entry.get("path_type") != "Dir":
                continue
            match = re.match(r"(\d{4}) (May|November)", entry["name"])
            if match:
                out.append((match.group(1), match.group(2), [f"{SUBJECT}/{level}/{entry['name']}"]))
    extra = [
        ("2023", "May", "May 2023 Examination Session/Experimental sciences"),
        ("2023", "November", "November 2023 Examination Session/Experimental sciences"),
        ("2024", "May", "May 2024 Examination Session/PDFs/Experimental sciences"),
        ("2024", "November", "DONATED PAPERS N24"),
        ("2025", "May", "DONATED PAPERS M25"),
        ("2025", "November", "DONATED PAPERS N25"),
        ("2026", "May", "DONATED PAPERS M26"),
    ]
    for year, month, leaf in extra:
        folder = f"{YEAR}/{year} Examination Session/{leaf}"
        out.append((year, month, [folder]))
    return out


def parse(name: str, folder_level: str | None) -> dict | None:
    low = name.lower()
    if "physic" not in low:
        return None
    level = folder_level
    if level is None:
        if re.search(r"(?<![a-z])hl(?![a-z])", low):
            level = "hl"
        elif re.search(r"(?<![a-z])sl(?![a-z])", low):
            level = "sl"
        else:
            return None
    lang = "en"
    for word, code in LANGS:
        if word in low:
            lang = code
            break
    paper = re.search(r"paper[_\s-]*(\d+[a-z]?)", low) or re.search(r"\bp(\d+[a-z]?)\b", low)
    if not paper:
        return None
    tz = None
    zone = re.search(r"tz\s*([abc123])", low) or re.search(r"zone\s*([abc])", low)
    if zone:
        tz = ZONES[zone.group(1)]
    markscheme = "markscheme" in low or bool(re.search(r"[_\s]ms[_\s]", low)) or low.endswith("_ms")
    return {"level": level, "lang": lang, "paper": paper.group(1), "tz": tz, "markscheme": markscheme}


def destination(year: str, month: str, info: dict) -> Path:
    ym = f"{year}-{'05' if month == 'May' else '11'}"
    name = f"p{info['paper']}"
    if info["tz"]:
        name += f"-tz{info['tz']}"
    if info["markscheme"]:
        name += "-markscheme"
    return LIBRARY / info["level"] / ym / info["lang"] / f"{name}.pdf"


def download(url: str, dest: Path, cookie: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Cookie": cookie,
            "User-Agent": USER_AGENT,
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
                raise SystemExit("Cloudflare rejected the download. Refresh cf_clearance.") from error
            if attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(1 + attempt)
    if data[:4] != b"%PDF":
        raise RuntimeError(f"not a PDF: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(".part")
    temporary.write_bytes(data)
    temporary.replace(dest)
    return "downloaded"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cookie", help="cf_clearance cookie value")
    parser.add_argument("--dry-run", action="store_true", help="print without downloading")
    parser.add_argument("--since", type=int, default=0, help="only years >= this (e.g. 2010)")
    args = parser.parse_args()

    cookie = cookie_value(args)
    planned: list[tuple[Path, str]] = []
    seen: set[Path] = set()
    unavailable: list[tuple[str, str, str]] = []

    for year, month, folders in sources(cookie):
        if int(year) < args.since:
            continue
        folder_level = "hl" if "Physics_HL" in folders[0] else ("sl" if "Physics_SL" in folders[0] else None)
        for folder in folders:
            for name in physics_files(folder, cookie):
                info = parse(name, folder_level)
                if not info:
                    unavailable.append((year, month, name))
                    continue
                dest = destination(year, month, info)
                if dest in seen or dest.exists():
                    continue
                seen.add(dest)
                url = f"{BASE}/{urllib.parse.quote(f'{folder}/{name}', safe='/')}"
                planned.append((dest, url))

    print(f"{len(planned)} missing physics PDFs")
    counts = {"downloaded": 0, "failed": 0}
    for dest, url in planned:
        rel = dest.relative_to(ROOT)
        if args.dry_run:
            print(f"  would get {rel}")
            continue
        try:
            download(url, dest, cookie)
            counts["downloaded"] += 1
            print(f"  downloaded {rel}")
        except Exception as error:  # noqa: BLE001 - report and keep going
            counts["failed"] += 1
            print(f"  FAILED {rel}: {error}")
    if unavailable:
        print(f"\n{len(unavailable)} files could not be mapped:")
        for item in unavailable[:20]:
            print(" ", "/".join(item))
    print("done: " + ", ".join(f"{k}={v}" for k, v in counts.items() if v))


if __name__ == "__main__":
    main()
