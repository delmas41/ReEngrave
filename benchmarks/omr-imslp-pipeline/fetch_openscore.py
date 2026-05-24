#!/usr/bin/env python3
"""Fetch OpenScore Orchestral Corpus symphony MusicXML files from Hauptstimme.

Pulls one .mxl per movement for Beethoven 1-9 and Brahms 1-4 from
https://github.com/MarkGotham/Hauptstimme (scores: CC0; code: MIT) into
the gitignored drop folder tools/omr/training/data/imslp/.

Idempotent — existing files are skipped.

Run from anywhere:
    python3 benchmarks/omr-imslp-pipeline/fetch_openscore.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = "MarkGotham/Hauptstimme"
BRANCH = "main"
API_BASE = f"https://api.github.com/repos/{REPO}/contents"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

COMPOSERS = {
    "Beethoven,_Ludwig_van": ("beethoven", "Beethoven"),
    "Brahms,_Johannes": ("brahms", "Brahms"),
}

SYMPHONY_RE = re.compile(r"^Symphony_No\.(\d+),_Op\.(\d+)$")

REPO_ROOT = Path(__file__).resolve().parents[2]
DROP_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"


def http_json(url: str) -> list | dict:
    req = Request(url, headers={"Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def http_bytes(url: str) -> bytes:
    with urlopen(url, timeout=60) as r:
        return r.read()


def main() -> int:
    DROP_ROOT.mkdir(parents=True, exist_ok=True)
    downloaded = skipped = 0
    errors: list[str] = []

    for github_name, (slug, surname) in COMPOSERS.items():
        try:
            works = http_json(f"{API_BASE}/data/{github_name}")
        except (HTTPError, URLError) as exc:
            errors.append(f"{github_name}: list works failed — {exc}")
            continue

        for work in works:
            if work.get("type") != "dir":
                continue
            m = SYMPHONY_RE.match(work["name"])
            if not m:
                continue
            sym_n, op_n = m.group(1), m.group(2)

            try:
                movements = http_json(f"{API_BASE}/data/{github_name}/{work['name']}")
            except (HTTPError, URLError) as exc:
                errors.append(f"{work['name']}: list movements failed — {exc}")
                continue

            target_dir = DROP_ROOT / f"{slug}-symphony-{sym_n}" / "musicxml"
            target_dir.mkdir(parents=True, exist_ok=True)

            source_yaml = target_dir.parent / "source.yaml"
            if not source_yaml.exists():
                source_yaml.write_text(
                    f"source: OpenScore Orchestral Corpus (Hauptstimme)\n"
                    f"repo: https://github.com/{REPO}\n"
                    f"github_path: data/{github_name}/{work['name']}\n"
                    f"composer: {github_name.replace('_', ' ')}\n"
                    f"work: {work['name'].replace('_', ' ')}\n"
                    f"license: CC0-1.0 (scores), MIT (annotations/code)\n"
                )

            for mvt in movements:
                if mvt.get("type") != "dir" or not mvt["name"].isdigit():
                    continue
                mvt_n = mvt["name"]
                target_file = target_dir / f"mvt-{mvt_n}.mxl"
                if target_file.exists():
                    skipped += 1
                    continue

                raw_url = (
                    f"{RAW_BASE}/data/{github_name}/{work['name']}/"
                    f"{mvt_n}/{surname}_Op.{op_n}_{mvt_n}.mxl"
                )
                try:
                    data = http_bytes(raw_url)
                except (HTTPError, URLError) as exc:
                    errors.append(f"{raw_url}: {exc}")
                    continue

                target_file.write_bytes(data)
                downloaded += 1
                print(f"  {slug}-symphony-{sym_n}/musicxml/mvt-{mvt_n}.mxl  ({len(data)//1024} KB)")

    print(f"\nDownloaded: {downloaded}, skipped (already present): {skipped}, errors: {len(errors)}")
    for err in errors:
        print(f"  ! {err}", file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
