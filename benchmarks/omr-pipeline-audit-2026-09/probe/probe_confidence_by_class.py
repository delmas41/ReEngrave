#!/usr/bin/env python3
"""Agent I, round 1 — WHICH classes the un-read detection confidence belongs to.

The map's `[V1]` establishes that `export.py` reads a detection confidence zero
times and that ~29.7% of a scanned page's detections sit under 0.40. That is a
pooled figure. This splits it by category and by class, because the decision
that matters is not "is the pool weak" but "is the class a TRUSTED TIER is
built from weak".

Read-only over committed transcriptions. n = 2 pages, 2 editions, 2 weight
files — small, and the two agree.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_confidence_by_class.py
"""
from __future__ import annotations
import collections, json, statistics as s
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# ── OMR_AUDIT_GUARD ─────────────────────────────────────────────────────────
# ⚠️ A probe that prints a clean all-zero table when it means "I looked in the
# wrong place" is this audit's own recurring failure — it produced the round-2
# N4 retraction. Inputs are resolved from THIS FILE's location (never the CWD),
# `OMR_FIXTURE_ROOT` names the checkout for anything gitignored, and a missing
# or empty input set is a NON-ZERO EXIT, never a result.
import os as _os

FIXTURE_ROOT = Path(_os.environ.get(
    "OMR_FIXTURE_ROOT", "/Users/seanjohnson/Desktop/ReEngrave"))


def _require(paths, what):
    """Abort with exit 2 unless every named input exists and the set is non-empty."""
    missing = [str(p) for p in paths if not Path(p).exists()]
    if not paths or missing:
        print(f"FATAL: {len(missing) or 'all'} {what} missing "
              f"(set OMR_FIXTURE_ROOT if these are gitignored inputs)",
              file=sys.stderr)
        for m in missing[:5]:
            print(f"  {m}", file=sys.stderr)
        raise SystemExit(2)
    return list(paths)
# ────────────────────────────────────────────────────────────────────────────
FILES = {
    "beet5-p02  (scan, Litolff, hollow-graft-shift09)":
        "benchmarks/omr-reference-selection-2026-09/out/beet5-p02-on.json",
    "brahms1    (scan, Breitkopf, imgsz2048-ft-30ep)":
        "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json",
}


def dets(doc):
    for p in doc.get("pages", []):
        for sy in p.get("systems", []):
            for st in sy.get("staves", []):
                for m in st.get("measures", []):
                    yield from m.get("detections", [])


def main() -> int:
    _require([ROOT / r for r in FILES.values()], "transcriptions")
    for lab, rel in FILES.items():
        doc = json.load(open(ROOT / rel))
        by_cat, by_cls = collections.defaultdict(list), collections.defaultdict(list)
        for d in dets(doc):
            c = d.get("confidence", 1.0)
            by_cat[d.get("category")].append(c)
            if d.get("category") == "structural":
                by_cls[d.get("class")].append(c)
        allc = [x for v in by_cat.values() for x in v]
        print(f"\n=== {lab}   n={len(allc)}  median={s.median(allc):.3f}  "
              f"under 0.40 = {sum(x < 0.40 for x in allc)/len(allc):.3f}")
        print(f"{'category':16s}{'n':>6s}{'median':>8s}{'<0.40':>8s}{'<0.50':>8s}")
        for cat, v in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
            print(f"{str(cat):16s}{len(v):6d}{s.median(v):8.3f}"
                  f"{sum(x<0.40 for x in v)/len(v):8.3f}{sum(x<0.50 for x in v)/len(v):8.3f}")
        print("  -- structural, by class (this is where the ladder tier comes from) --")
        for cls, v in sorted(by_cls.items(), key=lambda kv: -len(kv[1]))[:8]:
            print(f"  {str(cls):22s}{len(v):6d}{s.median(v):8.3f}"
                  f"{sum(x<0.40 for x in v)/len(v):8.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
