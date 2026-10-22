#!/usr/bin/env python3
"""What meters does the repertoire actually print, and can the locator search for them?

Two populations, because they answer different halves of the question:

  * the 97 **dossiers** (`data/dossiers/*.json`) — orchestral movements with
    exact meter facts generated from MusicXML, which is the repertoire this
    project is aimed at;
  * the score library's 1745 **reference encodings**, which is wider (chorales,
    keyboard, chamber) and says whether the candidate list would hold up if the
    aim widened.

A meter absent from `DEFAULT_METERS` can never be read, no matter how well the
page prints it, so this is the cheapest bound available on the reader's ceiling.
"""
from __future__ import annotations

import collections
import io
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.time_signature_locator import DEFAULT_METERS  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")

CANDIDATES = {(n, d) for n, d, _ in DEFAULT_METERS}

TIME_RE = re.compile(
    rb"<time[^>]*>.*?<beats>\s*([0-9+ ]+)\s*</beats>.*?<beat-type>\s*(\d+)\s*</beat-type>",
    re.S,
)
SYMBOL_RE = re.compile(rb'<time[^>]*symbol="([a-z-]+)"')


def _first_time(raw: bytes) -> tuple[tuple[int, int] | None, str | None]:
    m = TIME_RE.search(raw)
    if not m:
        return None, None
    beats = m.group(1).decode().strip()
    if "+" in beats:  # additive meter, e.g. 3+2/8
        return None, "additive:" + beats
    try:
        pair = (int(beats), int(m.group(2)))
    except ValueError:
        return None, None
    sym = SYMBOL_RE.search(raw[: m.end()])
    return pair, sym.group(1).decode() if sym else None


def read_mxl(path: Path) -> tuple[tuple[int, int] | None, str | None]:
    try:
        if path.suffix == ".mxl":
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist()
                         if n.endswith(".xml") and not n.startswith("META-INF")]
                # container.xml points at the rootfile; the biggest .xml is it in practice
                names.sort(key=lambda n: -z.getinfo(n).file_size)
                for n in names[:2]:
                    pair, sym = _first_time(z.read(n))
                    if pair or sym:
                        return pair, sym
            return None, None
        return _first_time(path.read_bytes())
    except Exception as exc:  # noqa: BLE001 - a corrupt encoding is data, not a crash
        return None, f"error:{type(exc).__name__}"


def dossier_survey() -> dict:
    start = collections.Counter()
    every = collections.Counter()
    works_missing_start: list[str] = []
    works_missing_any: dict[str, list[str]] = {}
    for p in sorted((REPO / "data/dossiers").glob("*.json")):
        d = json.loads(p.read_text())
        sm = d["starting_meter"]
        k = (sm["beats"], sm["beat_type"])
        start[k] += 1
        if k not in CANDIDATES:
            works_missing_start.append(d["work_id"])
        for mc in d.get("meter_changes") or []:
            kk = (mc["beats"], mc["beat_type"])
            every[kk] += 1
            if kk not in CANDIDATES:
                works_missing_any.setdefault(d["work_id"], []).append(f"{kk[0]}/{kk[1]}")
    return {
        "n_works": sum(start.values()),
        "starting_meters": {f"{a}/{b}": n for (a, b), n in start.most_common()},
        "all_meters": {f"{a}/{b}": n for (a, b), n in every.most_common()},
        "starting_covered": sum(n for k, n in start.items() if k in CANDIDATES),
        "works_missing_starting_meter": works_missing_start,
        "works_missing_some_meter": works_missing_any,
    }


def library_survey() -> dict:
    ref = LIB / "reference"
    if not ref.exists():
        return {"unavailable": str(ref)}
    files = sorted(list(ref.rglob("*.mxl")) + list(ref.rglob("*.musicxml"))
                   + list(ref.rglob("*.xml")))
    meters = collections.Counter()
    symbols = collections.Counter()
    odd: list[str] = []
    unread = 0
    for f in files:
        pair, sym = read_mxl(f)
        if sym:
            symbols[sym] += 1
        if pair is None:
            unread += 1
            if sym and sym.startswith("additive"):
                odd.append(f"{f.name}: {sym}")
            continue
        meters[pair] += 1
        if pair not in CANDIDATES:
            odd.append(f"{f.relative_to(ref)}: {pair[0]}/{pair[1]}")
    covered = sum(n for k, n in meters.items() if k in CANDIDATES)
    return {
        "n_files": len(files),
        "n_unreadable": unread,
        "meters": {f"{a}/{b}": n for (a, b), n in meters.most_common()},
        "symbols": dict(symbols),
        "covered": covered,
        "total_read": sum(meters.values()),
        "outside_candidate_list": odd[:60],
        "n_outside": sum(n for k, n in meters.items() if k not in CANDIDATES),
    }


if __name__ == "__main__":
    out = {"candidate_list": sorted(f"{a}/{b}" for a, b in CANDIDATES),
           "dossiers": dossier_survey(),
           "library_reference": library_survey()}
    (Path(__file__).parent / "meter_survey.json").write_text(json.dumps(out, indent=2))
    d = out["dossiers"]
    print(f"dossiers: {d['starting_covered']}/{d['n_works']} works' STARTING meter is searchable")
    print("  missing:", d["works_missing_starting_meter"])
    print("  mid-work meters outside the list:", d["works_missing_some_meter"])
    l = out["library_reference"]
    if "unavailable" not in l:
        print(f"library: {l['covered']}/{l['total_read']} encodings' first meter is searchable "
              f"({l['n_outside']} outside, {l['n_unreadable']} unreadable of {l['n_files']})")
        print("  symbols:", l["symbols"])
        for line in l["outside_candidate_list"][:20]:
            print("   ", line)
