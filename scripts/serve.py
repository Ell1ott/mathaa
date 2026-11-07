"""Local question browser. Bind to localhost only."""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from catalog import ROOT
from transcribe import tidy_question

QUESTIONS = ROOT / "data" / "questions.json"
COVERAGE = ROOT / "data" / "coverage.json"
REVIEWS = ROOT / "data" / "reviews.json"
TEMPLATE = ROOT / "template.html"
PORT = 8765
CUT_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.png")
HEADER = re.compile(
    r"(?m)^[#\s]*(\d+)\.\s*(?:\\\()?\s*\[Maximum marks?:\s*(\d+)\]\s*(?:\\\))?[ \t]*\n?"
)
SESSION_ORDER = {"November": 0, "May": 1, "Specimen": 2}


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text())


def question_bank(questions: list[dict]) -> dict:
    """Shape questions.json into the {topics, qs} blob template.html reads."""
    topics: dict[str, list[str]] = {}
    out = []
    for question in questions:
        text = question["text"]
        number = question["number"]
        marks = None
        headers = list(HEADER.finditer(text))
        own = next((header for header in headers if int(header.group(1)) == number), None)
        if own:
            marks = int(own.group(2))
            end = next(
                (
                    header.start()
                    for header in headers
                    if header.start() > own.start() and int(header.group(1)) != number
                ),
                len(text),
            )
            text = text[own.end() : end]
        else:
            nxt = next((header.start() for header in headers if int(header.group(1)) == number + 1), None)
            if nxt:
                text = text[:nxt]
        for topic in question["topics"]:
            topics[topic["code"]] = [topic["topic"], topic["area"]]
        out.append(
            {
                "i": question["id"],
                "y": question["year"],
                "s": question["session"],
                "p": question["paper"],
                "z": question["tz"],
                "n": number,
                "m": marks,
                "t": text.strip(),
                "c": [topic["code"] for topic in question["topics"]],
                "v": question["status"] == "matched",
                "a": question["page_start"],
                "b": question["page_end"],
            }
        )
    out.sort(key=lambda item: (-item["y"], SESSION_ORDER[item["s"]], item["p"], item["z"] or "", item["n"]))
    return {"topics": topics, "qs": out}


def bank_page() -> bytes:
    payload = load_json(QUESTIONS, {"questions": []})
    blob = json.dumps(question_bank(payload.get("questions", [])), ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text().replace("__DATA__", blob.replace("</", "<\\/"), 1)
    return html.encode()


def pdf_for(question_id: str | None, paper_id: str | None) -> Path | None:
    payload = load_json(QUESTIONS, {"questions": []})
    for question in payload.get("questions", []):
        if question_id and question["id"] != question_id:
            continue
        if paper_id and question.get("paper_id") != paper_id:
            continue
        path = (ROOT / question["file"]).resolve()
        if ROOT.resolve() not in path.parents:
            return None
        if path.is_file():
            return path
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} {fmt % args}")

    def send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send(200, bank_page(), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/questions":
            payload = load_json(QUESTIONS, {"questions": []})
            flags = load_json(REVIEWS, {})
            for question in payload.get("questions", []):
                question["flagged"] = bool(flags.get(question["id"]))
                cleaned = tidy_question(question.get("text") or "", question.get("number") or 0)
                if cleaned:
                    question["text"] = cleaned
            coverage = load_json(COVERAGE, {})
            payload["coverage"] = {
                "present": coverage.get("present", 0),
                "missing": coverage.get("missing", 0),
                "needs_ocr": coverage.get("needs_ocr", 0),
                "total": len(coverage.get("papers", [])),
            }
            self.send(200, json.dumps(payload).encode(), "application/json")
            return
        if parsed.path == "/api/coverage":
            self.send(200, json.dumps(load_json(COVERAGE, {})).encode(), "application/json")
            return
        if parsed.path.startswith("/cut/") or parsed.path.startswith("/fig/"):
            kind = "cuts" if parsed.path.startswith("/cut/") else "figs"
            name = parsed.path.split("/", 2)[2]
            path = (ROOT / "data" / kind / name).resolve()
            if not CUT_NAME.fullmatch(name) or path.parent != (ROOT / "data" / kind).resolve() or not path.is_file():
                self.send(404, b"image not on disk", "text/plain; charset=utf-8")
                return
            self.send(200, path.read_bytes(), "image/png")
            return
        if parsed.path == "/pdf":
            query = parse_qs(parsed.query)
            path = pdf_for(
                query.get("question", [None])[0],
                query.get("paper", [None])[0],
            )
            if path is None:
                self.send(404, b"PDF not on disk", "text/plain; charset=utf-8")
                return
            self.send(200, path.read_bytes(), "application/pdf")
            return
        self.send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/reviews":
            self.send(404, b"not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        qid = body.get("id")
        if not qid:
            self.send(400, b"missing id", "text/plain; charset=utf-8")
            return
        flags = load_json(REVIEWS, {})
        if body.get("flagged"):
            flags[qid] = True
        else:
            flags.pop(qid, None)
        REVIEWS.write_text(json.dumps(flags, indent=2) + "\n")
        self.send(200, json.dumps({"ok": True, "flagged": bool(flags.get(qid))}).encode(), "application/json")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
