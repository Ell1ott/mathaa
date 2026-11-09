# Math AA HL question browser

Local browser for IB Mathematics: analysis and approaches HL papers. It filters by syllabus area, topic, year, session, paper, and time zone, shows the question text, and opens the PDF on the page where the question starts.

Question text and the cutout images in `data/questions.json`, `data/cuts/`, and `data/figs/` are committed. The PDFs in `papers/` stay gitignored.

## Deploy

`web/` is the Vite + React question browser. `scripts/export_site.py` copies `web/dist` into `site/`, writes `site/questions.json`, and copies `site/cut/`, `site/fig/`, and `site/scheme/`. `site/` is gitignored. Vercel installs and builds `web/`, then runs that script. Connect the GitHub repo and leave the framework as Other so `vercel.json` sets the build. Use the Git integration. A private repo keeps the files off public GitHub. The production URL is still public.

## Sources

- Topic citations come from the public pages under [Aimnova’s Math AA HL past-paper index](https://www.aimnova.app/ib-math-aa/past-papers-hl). Those pages list session, paper, time zone, and question number. They do not include the original question wording, and this project does not copy Aimnova’s practice questions. `robots.txt` allows those pages and disallows `/api/`, `/papers/`, and `/exam-vault`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build.py
python scripts/serve.py
```

In another terminal:

```bash
cd web
npm install
npm run dev
```

Open the Vite URL, http://127.0.0.1:5173. `serve.py` supplies the question bank, images, and PDFs.

`build.py` writes `data/catalog.json`, refreshes Aimnova citations if `data/references.json` is missing, extracts questions, and rewrites the coverage table below. Run `python scripts/build.py --refs` to fetch the citation pages again.

## Library

## Add a paper

1. Save one question-paper PDF into `papers/inbox/`. A name the catalog can read is enough, for example `2025-11-p2-tz1.pdf`, `n25-p2-tz1.pdf`, or `Mathematics_analysis_and_approaches_paper_2_TZ1_HL.pdf` when the cover still shows the session and year.
2. November 2025 Paper 2 TZ1, the paper from the photo, is `2025-11-p2-tz1.pdf`.
3. Run `python scripts/build.py` again.
4. If the PDF is a scan, coverage marks it `needs_ocr` and skips question text. A text-layer copy of the same paper is used instead. Question wording is then rewritten as Markdown by PaddleOCR-VL-1.6 through the [OpenParser](https://api.openparser.dev) API (`OPENPARSER_API_KEY` in `.env`). Finished questions are cached in `data/vl/` and are not redone. The PDF page stays the page you open.

## Coverage

<!-- coverage:start -->
| Paper | Status | Questions | File |
| --- | --- | --- | --- |
| Specimen 2021 Paper 1 | present | 12 | papers/official/dp-mathematics-analysis-and-approaches-specimen-papers-en.pdf |
| Specimen 2021 Paper 2 | present | 12 | papers/official/dp-mathematics-analysis-and-approaches-specimen-papers-en.pdf |
| Specimen 2021 Paper 3 | present | 2 | papers/official/dp-mathematics-analysis-and-approaches-specimen-papers-en.pdf |
| May 2021 Paper 1 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-05/en/p1-tz1.pdf |
| May 2021 Paper 1 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-05/en/p1-tz2.pdf |
| May 2021 Paper 2 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-05/en/p2-tz1.pdf |
| May 2021 Paper 2 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-05/en/p2-tz2.pdf |
| May 2021 Paper 3 TZ1 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-05/en/p3-tz1.pdf |
| May 2021 Paper 3 TZ2 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-05/en/p3-tz2.pdf |
| November 2021 Paper 1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-11/en/p1.pdf |
| November 2021 Paper 2 | present | 11 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-11/en/p2.pdf |
| November 2021 Paper 3 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2021-11/en/p3.pdf |
| May 2022 Paper 1 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-05/en/p1-tz1.pdf |
| May 2022 Paper 1 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-05/en/p1-tz2.pdf |
| May 2022 Paper 2 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-05/en/p2-tz1.pdf |
| May 2022 Paper 2 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-05/en/p2-tz2.pdf |
| May 2022 Paper 3 TZ1 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-05/en/p3-tz1.pdf |
| May 2022 Paper 3 TZ2 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-05/en/p3-tz2.pdf |
| November 2022 Paper 1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-11/en/p1.pdf |
| November 2022 Paper 2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-11/en/p2.pdf |
| November 2022 Paper 3 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-11/en/p3.pdf |
| May 2023 Paper 1 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p1-tz1.pdf |
| May 2023 Paper 1 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p1-tz2.pdf |
| May 2023 Paper 2 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p2-tz1.pdf |
| May 2023 Paper 2 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p2-tz2.pdf |
| May 2023 Paper 3 TZ1 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p3-tz1.pdf |
| May 2023 Paper 3 TZ2 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p3-tz2.pdf |
| November 2023 Paper 1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-11/en/p1-tz1.pdf |
| November 2023 Paper 2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-11/en/p2-tz1.pdf |
| November 2023 Paper 3 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-11/en/p3.pdf |
| May 2024 Paper 1 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-05/en/p1-tz1.pdf |
| May 2024 Paper 1 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-05/en/p1-tz2.pdf |
| May 2024 Paper 2 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-05/en/p2-tz1.pdf |
| May 2024 Paper 2 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-05/en/p2-tz2.pdf |
| May 2024 Paper 3 TZ1 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-05/en/p3-tz1.pdf |
| May 2024 Paper 3 TZ2 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-05/en/p3-tz2.pdf |
| November 2024 Paper 1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-11/en/p1.pdf |
| November 2024 Paper 2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-11/en/p2.pdf |
| November 2024 Paper 3 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-11/en/p3.pdf |
| May 2025 Paper 1 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p1-tz1.pdf |
| May 2025 Paper 1 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p1-tz2.pdf |
| May 2025 Paper 1 TZ3 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p1-tz3.pdf |
| May 2025 Paper 2 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p2-tz1.pdf |
| May 2025 Paper 2 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p2-tz2.pdf |
| May 2025 Paper 2 TZ3 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p2-tz3.pdf |
| May 2025 Paper 3 TZ1 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p3-tz1.pdf |
| May 2025 Paper 3 TZ2 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p3-tz2.pdf |
| May 2025 Paper 3 TZ3 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p3-tz3.pdf |
| November 2025 Paper 1 TZ1 | present | 11 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-11/en/p1-tz1.pdf |
| November 2025 Paper 1 TZ3 | present | 11 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-11/en/p1-tz3.pdf |
| November 2025 Paper 2 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-11/en/p2-tz1.pdf |
| November 2025 Paper 2 TZ3 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-11/en/p2-tz3.pdf |
| November 2025 Paper 3 TZ1 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-11/en/p3-tz1.pdf |
| November 2025 Paper 3 TZ3 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-11/en/p3-tz3.pdf |
| May 2026 Paper 1 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p1-tz1.pdf |
| May 2026 Paper 1 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p1-tz2.pdf |
| May 2026 Paper 1 TZ3 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p1-tz3.pdf |
| May 2026 Paper 2 TZ1 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p2-tz1.pdf |
| May 2026 Paper 2 TZ2 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p2-tz2.pdf |
| May 2026 Paper 2 TZ3 | present | 12 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p2-tz3.pdf |
| May 2026 Paper 3 TZ1 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p3-tz1.pdf |
| May 2026 Paper 3 TZ2 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p3-tz2.pdf |
| May 2026 Paper 3 TZ3 | present | 2 | papers/library/mathematics/mathematics-analysis-and-approaches/hl/2026-05/en/p3-tz3.pdf |

Files that did not map cleanly: papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-11/en/p1-tz0.pdf (needs_ocr); papers/library/mathematics/mathematics-analysis-and-approaches/hl/2022-11/en/p2-tz0.pdf (needs_ocr); papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p1-tz1-tz2.pdf (needs_ocr); papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p1-tz3.pdf (needs_ocr); papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p2-tz1-tz2.pdf (needs_ocr); papers/library/mathematics/mathematics-analysis-and-approaches/hl/2023-05/en/p3-tz1-tz2.pdf (needs_ocr); papers/library/mathematics/mathematics-analysis-and-approaches/hl/2024-05/en/p2.pdf (unrecognized); papers/library/mathematics/mathematics-analysis-and-approaches/hl/2025-05/en/p3.pdf (needs_ocr).
<!-- coverage:end -->
