#!/usr/bin/env python3
"""Collect the INPUT to `slots.build_reference`, per document — nothing else.

MEASUREMENT ONLY, and deliberately cheap: one staff detection plus one Surya
read per probed page (~5 s), the same recipe as
`omr-staff-identity-layer-2026-09/probe_roster_availability.py`.  A full
transcription of the same pages costs ~280 s each and would buy nothing here,
because `build_reference` sees ONLY what this probe records: for every system
of the run, its staff count and the labels that resolved on it.

WHY A CACHE OF VIEWS AND NOT A VERDICT.  The question is which system a
*selection rule* picks, and there are several rules to try.  Probing is the
expensive half and rule evaluation is free, so the probe writes the views and
`analyse_rules.py` replays every rule over them offline.  Re-running a rule
costs nothing and can never re-read a margin differently (Surya has a known
temperature nondeterminism — `contextual.py`).

⚠️ A RUN, NOT A DOCUMENT.  The bug this workstream is about only exists across
a MULTI-PAGE run: page 1 of Beethoven 5 prints 12 staves, pages 2+ print 11,
and it is the pooling of those pages that lets the condensed shape out-vote the
full one.  So the unit here is a window of consecutive pages, the way the web
app runs (`OMR_MAX_PAGES=5`), not a single page.

    python3 .../probe_system_views.py --plan
    python3 .../probe_system_views.py --limit 60 --window 0-2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO))

LIB = Path(os.getenv("SCORE_LIBRARY",
                     "/Users/seanjohnson/Desktop/ReEngrave/library"))
CATALOG = Path(os.getenv(
    "SCORE_CATALOG",
    "/Users/seanjohnson/Desktop/ReEngrave/data/score-library/catalog.json"))
CACHE = Path(os.getenv("REFSEL_CACHE", str(HERE.parent / "views-cache")))

MIN_STAVES = 4       # below this it is not an orchestral system
DPI = 300            # measured identical to 600 for label reading


def house(pub: str | None) -> str:
    for h in ("Breitkopf", "Litolff", "Simrock", "Peters", "Eulenburg",
              "Kalmus", "Universal", "Durand", "Schott", "Ricordi",
              "Novello", "Augener", "Bote", "Steingraber"):
        if h.lower() in (pub or "").lower():
            return h
    return "other/unknown"


def editions():
    cat = json.loads(CATALOG.read_text())
    out = []
    for e in cat["entries"]:
        if e.get("kind") != "edition":
            continue
        if (e.get("pages") or 0) < 8:
            continue
        if (LIB / e["path"]).exists():
            out.append(e)
    return out


def probe_document(e, pages, dpi):
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr import staff_labels_surya as S

    pdf = LIB / e["path"]
    views = []
    for pi in pages:
        if pi >= (e.get("pages") or 0):
            continue
        try:
            pws = detect_staves(render_page(pdf, pi, dpi=dpi))
        except Exception as exc:
            views.append({"page": pi, "error": repr(exc)[:160]})
            continue
        if len(pws.staves) < MIN_STAVES:
            views.append({"page": pi, "n_staves": len(pws.staves),
                          "reason": "too few staves"})
            continue
        try:
            labs = S.read_staff_labels_surya(pws)
        except Exception as exc:
            views.append({"page": pi, "error": repr(exc)[:160]})
            continue
        # confident labels only — the same gate `slots.labels_by_staff` uses
        by_staff = {l.staff_index: (l.instrument.name if l.instrument else None,
                                    l.confidence)
                    for l in labs if l.matched}
        by_system = defaultdict(list)
        for st in sorted(pws.staves, key=lambda s: s.top_y):
            by_system[st.system_index].append(st)
        for sysi, staves in sorted(by_system.items()):
            names = []
            for st in staves:
                nm, conf = by_staff.get(st.staff_index, (None, None))
                names.append({"staff_index": st.staff_index, "name": nm,
                              "confidence": conf,
                              "group_index": st.group_index})
            views.append({"page": pi, "system": sysi, "size": len(staves),
                          "staves": names})
    return views


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--window", default="0-2",
                    help="page window, e.g. 0-2 or 0-4")
    ap.add_argument("--dpi", type=int, default=DPI)
    args = ap.parse_args()

    lo, _, hi = args.window.partition("-")
    pages = list(range(int(lo), int(hi or lo) + 1))

    eds = editions()
    by_house = defaultdict(list)
    for e in eds:
        by_house[house(e.get("publisher"))].append(e)
    ordered, i = [], 0
    while len(ordered) < len(eds):
        for h in sorted(by_house):
            if i < len(by_house[h]):
                ordered.append(by_house[h][i])
        i += 1
    if args.limit:
        ordered = ordered[: args.limit]

    print(f"editions on disk with >=8 pages: {len(eds)}  "
          f"houses={dict(Counter(house(e.get('publisher')) for e in eds))}")
    print(f"probing {len(ordered)} documents, pages {pages}, dpi {args.dpi}")
    if args.plan:
        return 0

    from tools.omr import staff_labels_surya as S
    if not S.available():
        raise SystemExit("Surya unavailable — every document would report zero "
                         "labels and every rule would tie. Refusing.")

    outdir = CACHE / f"w{pages[0]}-{pages[-1]}"
    outdir.mkdir(parents=True, exist_ok=True)
    for k, e in enumerate(ordered, 1):
        key = f"{e['work_id']}--{e.get('imslp_id') or e['sha256'][:8]}"
        path = outdir / f"{key}.json"
        if path.exists():
            continue
        t0 = time.time()
        views = probe_document(e, pages, args.dpi)
        rec = {"work_id": e["work_id"], "key": key,
               "house": house(e.get("publisher")),
               "publisher": (e.get("publisher") or "")[:70],
               "composer": e.get("composer_slug"), "pdf_pages": e.get("pages"),
               "window": pages, "views": views,
               "seconds": round(time.time() - t0, 1)}
        path.write_text(json.dumps(rec))
        sizes = [v.get("size") for v in views if "size" in v]
        labs = [sum(1 for s in v["staves"] if s["name"]) for v in views
                if "staves" in v]
        print(f"  [{k}/{len(ordered)}] {rec['house']:12s} {key:44s} "
              f"sizes={sizes} labels={labs} {rec['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
