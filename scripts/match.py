"""Join extracted questions to Aimnova citations."""

from __future__ import annotations

import json
import re
from collections import defaultdict

from catalog import ROOT, load_catalog

REFS_PATH = ROOT / "data" / "references.json"
STOP = {"and", "the", "of", "only", "with", "from", "into", "using", "their", "higher", "level"}


def load_refs() -> list[dict]:
    if not REFS_PATH.exists():
        return []
    return json.loads(REFS_PATH.read_text()).get("refs", [])


def topic_words(topic: str) -> list[str]:
    return [word for word in re.findall(r"[a-zA-Z]{5,}", topic.lower()) if word not in STOP]


def lacks_overlap(topic: str, text: str) -> bool:
    words = topic_words(topic)
    if not words:
        return False
    haystack = text.lower()
    return not any(word in haystack for word in words)


def match_questions(papers: list[dict]) -> list[dict]:
    catalog = {paper["id"]: paper for paper in load_catalog()}
    by_key = defaultdict(list)
    for ref in load_refs():
        by_key[(ref["year"], ref["session"], ref["paper"], ref["tz"], ref["question"])].append(ref)
    questions = []
    for paper in papers:
        meta = catalog.get(paper["id"]) if paper.get("id") else None
        signals = paper.get("signals") or {}
        if meta:
            year, session, number, tz = meta["year"], meta["session"], meta["paper"], meta["tz"]
            label = meta["label"]
        else:
            year, session = signals.get("year"), signals.get("session")
            number, tz = signals.get("paper"), signals.get("tz")
            label = paper.get("reason") or "Unassigned paper"
        for question in paper["questions"]:
            topics = []
            if meta:
                topics = by_key.get((year, session, number, tz, question["number"]), [])
            seen = set()
            packed = []
            for topic in topics:
                key = (topic["code"], topic["topic"])
                if key in seen:
                    continue
                seen.add(key)
                packed.append({"code": topic["code"], "topic": topic["topic"], "area": topic["area"]})
            reasons = []
            if paper.get("ambiguous") or not meta:
                reasons.append(paper.get("reason") or "paper identity ambiguous")
            elif packed and any(lacks_overlap(topic["topic"], question["text"]) for topic in packed):
                reasons.append("topic words not in question")
            status = "review" if reasons else ("matched" if packed else "untagged")
            if paper.get("id"):
                qid = f"{paper['id']}-q{question['number']}"
            else:
                stem = re.sub(r"[^a-z0-9]+", "-", paper["file"].lower()).strip("-")
                qid = f"unassigned-{stem}-p{question['page_start']}-q{question['number']}"
            questions.append(
                {
                    "id": qid,
                    "paper_id": paper.get("id"),
                    "label": label,
                    "year": year,
                    "session": session,
                    "paper": number,
                    "tz": tz,
                    "number": question["number"],
                    "page_start": question["page_start"],
                    "page_end": question["page_end"],
                    "file": paper["file"],
                    "text": question["text"],
                    "text_source": question.get("text_source", "pymupdf"),
                    "topics": packed,
                    "status": status,
                    "reasons": reasons,
                }
            )
    return questions
