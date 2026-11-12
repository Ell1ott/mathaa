"""Cache public Aimnova citation lists. Stops if robots.txt disallows the pages."""

from __future__ import annotations

import html
import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

from catalog import AREAS, ROOT

REFS_PATH = ROOT / "data" / "references.json"
SITEMAP = "https://www.aimnova.app/sitemap.xml"
ROBOTS = "https://www.aimnova.app/robots.txt"
INDEX = "https://www.aimnova.app/ib-math-aa/past-papers-hl"
UA = "mathaa-local-index/1.0 (personal study; public citations only)"
TOPIC_URL = re.compile(
    r"https://www\.aimnova\.app/ib-math-aa/past-papers-hl/(unit-\d-[a-z0-9-]+)/([a-z0-9-]+)"
)
AREA_FROM_SLUG = {
    "unit-1-number-algebra": AREAS["1"],
    "unit-2-functions": AREAS["2"],
    "unit-3-geometry-trigonometry": AREAS["3"],
    "unit-4-statistics-probability": AREAS["4"],
    "unit-5-calculus": AREAS["5"],
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read().decode("utf-8", "replace")


def robots_allows(robots: str, path: str) -> bool:
    """User-agent: * disallow rules. Empty Disallow means allow."""
    ua = None
    rules: list[str] = []
    for raw in robots.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            ua = value
        elif ua == "*" and key == "disallow" and value:
            rules.append(value)
    for rule in rules:
        if "*" in rule:
            pattern = re.escape(rule).replace(r"\*", ".*")
            if re.search(pattern, path):
                return False
        elif path.startswith(rule):
            return False
    return True


def topic_urls(sitemap: str) -> list[str]:
    found = []
    for match in TOPIC_URL.finditer(sitemap):
        url = match.group(0)
        if match.group(1) in AREA_FROM_SLUG and url not in found:
            found.append(url)
    return found


def parse_topic_page(page: str, url: str) -> list[dict]:
    slug = TOPIC_URL.search(url)
    if not slug or "by exam session" not in page:
        return []
    area = AREA_FROM_SLUG[slug.group(1)]
    title = ""
    heading = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    if heading:
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", heading.group(1)))).strip()
    code_match = re.match(r"(\d+\.\d+)\s+(.+)", title)
    if not code_match:
        return []
    topic = re.sub(r"\s*\(HL only\)\s*$", "", code_match.group(2)).strip()
    section = page.split("by exam session", 1)[1]
    section = re.split(r"Frequently asked|Generate Math", section, maxsplit=1)[0]
    refs = []
    session = None
    year = None
    token = re.compile(
        r'font-black">((?:May|November|Specimen) \d{4})</p>'
        r'|whitespace-nowrap">((?:P[123](?: TZ[123])?))</span>\s*<span[^>]*>([^<]*)</span>'
    )
    for match in token.finditer(section):
        if match.group(1):
            name, year_s = match.group(1).split()
            session, year = name, int(year_s)
            continue
        if session is None:
            continue
        paper_s, questions = match.group(2), match.group(3)
        parts = paper_s.split()
        paper = int(parts[0][1])
        tz = parts[1] if len(parts) > 1 else None
        for question in re.findall(r"Q(\d+)", questions):
            refs.append(
                {
                    "code": code_match.group(1),
                    "topic": topic,
                    "area": area,
                    "year": year,
                    "session": session,
                    "paper": paper,
                    "tz": tz,
                    "question": int(question),
                    "url": url,
                }
            )
    return refs


PHYSICS_REFS_PATH = ROOT / "data" / "physics" / "references.json"
PHYSICS_INDEXES = (
    ("hl", "https://www.aimnova.app/ib-physics/past-papers-hl"),
    ("sl", "https://www.aimnova.app/ib-physics/past-papers-sl"),
)
PHYSICS_AREAS = {
    "unit-1-space-time-and-motion": "Space, time and motion",
    "unit-2-the-particulate-nature-of-matter": "The particulate nature of matter",
    "unit-3-wave-behaviour": "Wave behaviour",
    "unit-4-fields": "Fields",
    "unit-5-nuclear-and-quantum-physics": "Nuclear and quantum physics",
    "unit-6-experimental-skills": "Experimental skills",
}
PHYSICS_TOPIC_URL = re.compile(
    r"https://www\.aimnova\.app/ib-physics/past-papers-(hl|sl)/(unit-\d-[a-z0-9-]+)/([a-z0-9-]+)"
)


def physics_topic_urls(sitemap: str) -> list[str]:
    found = []
    for match in PHYSICS_TOPIC_URL.finditer(sitemap):
        url = match.group(0)
        if match.group(2) in PHYSICS_AREAS and url not in found:
            found.append(url)
    return found


def parse_physics_page(page: str, url: str) -> list[dict]:
    slug = PHYSICS_TOPIC_URL.search(url)
    if not slug or "by exam session" not in page:
        return []
    level, unit = slug.group(1), slug.group(2)
    area = PHYSICS_AREAS[unit]
    title = ""
    heading = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    if heading:
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", heading.group(1)))).strip()
    code_match = re.match(r"(\d+\.\d+)\s+(.+)", title)
    if not code_match:
        return []
    topic = re.sub(r"\s*\(HL only\)\s*$", "", code_match.group(2)).strip()
    section = page.split("by exam session", 1)[1]
    section = re.split(r"Frequently asked|Generate ", section, maxsplit=1)[0]
    refs = []
    session = None
    year = None
    token = re.compile(
        r'font-black">((?:May|November|Specimen) \d{4})</p>'
        r'|whitespace-nowrap">((?:P[123](?: TZ[123])?))</span>\s*<span[^>]*>([^<]*)</span>'
    )
    for match in token.finditer(section):
        if match.group(1):
            name, year_s = match.group(1).split()
            session, year = name, int(year_s)
            continue
        if session is None:
            continue
        paper_s, questions = match.group(2), match.group(3)
        parts = paper_s.split()
        paper = int(parts[0][1])
        tz = parts[1] if len(parts) > 1 else None
        for question in re.findall(r"Q(\d+)", questions):
            refs.append(
                {
                    "level": level,
                    "code": code_match.group(1),
                    "topic": topic,
                    "area": area,
                    "year": year,
                    "session": session,
                    "paper": paper,
                    "tz": tz,
                    "question": int(question),
                    "url": url,
                }
            )
    return refs


def sync_physics() -> dict:
    robots = fetch(ROBOTS)
    for _level, index in PHYSICS_INDEXES:
        path = index.removeprefix("https://www.aimnova.app")
        if not robots_allows(robots, path):
            raise SystemExit(f"robots.txt disallows {path}; not fetching.")
    urls = physics_topic_urls(fetch(SITEMAP))
    if not urls:
        raise SystemExit("sitemap listed no Physics topic pages.")
    refs: list[dict] = []
    empty: list[str] = []
    for index, url in enumerate(urls, 1):
        page = fetch(url)
        parsed = parse_physics_page(page, url)
        if parsed:
            refs.extend(parsed)
        else:
            empty.append(url)
        print(f"[{index}/{len(urls)}] {len(parsed):3d}  {url}")
        time.sleep(0.25)
    unique = list(
        {
            (r["level"], r["code"], r["year"], r["session"], r["paper"], r["tz"], r["question"]): r
            for r in refs
        }.values()
    )
    unique.sort(
        key=lambda r: (r["level"], r["code"], r["year"], r["session"], r["paper"], r["tz"] or "", r["question"])
    )
    payload = {
        "source": [index for _level, index in PHYSICS_INDEXES],
        "fetched": date.today().isoformat(),
        "pages": len(urls),
        "empty_pages": empty,
        "refs": unique,
    }
    PHYSICS_REFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PHYSICS_REFS_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {len(unique)} physics citations from {len(urls)} pages")
    return payload


def sync() -> dict:
    robots = fetch(ROBOTS)
    if not robots_allows(robots, "/ib-math-aa/past-papers-hl"):
        raise SystemExit("robots.txt disallows Aimnova past-paper pages; not fetching.")
    urls = topic_urls(fetch(SITEMAP))
    if not urls:
        raise SystemExit("sitemap listed no Math AA HL topic pages.")
    refs: list[dict] = []
    empty: list[str] = []
    for index, url in enumerate(urls, 1):
        page = fetch(url)
        parsed = parse_topic_page(page, url)
        if parsed:
            refs.extend(parsed)
        else:
            empty.append(url)
        print(f"[{index}/{len(urls)}] {len(parsed):3d}  {url}")
        time.sleep(0.25)
    unique = list({(r["code"], r["year"], r["session"], r["paper"], r["tz"], r["question"]): r for r in refs}.values())
    unique.sort(key=lambda r: (r["code"], r["year"], r["session"], r["paper"], r["tz"] or "", r["question"]))
    payload = {
        "source": INDEX,
        "fetched": date.today().isoformat(),
        "pages": len(urls),
        "empty_pages": empty,
        "refs": unique,
    }
    REFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REFS_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {len(unique)} citations from {len(urls)} pages")
    return payload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physics", action="store_true", help="fetch Physics HL and SL instead of Math AA")
    args = parser.parse_args()
    sync_physics() if args.physics else sync()
