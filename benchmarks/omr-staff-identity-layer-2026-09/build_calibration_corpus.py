#!/usr/bin/env python3
"""The held-out-label corpus: transcribe pages, CACHE the label reads, emit records.

⚠️⚠️ STOPPED MID-RUN 2026-09-05 BY DECISION. THIS IS A PARTIAL, NOT AN ARM.
It was sized to calibrate DERIVED identity for an identity-driven clef
OVERRIDE. That consumer is now both circular (`probe_order_vs_clef.py`: with
labels hidden, identity is mostly downstream of the clef it would correct) and
superseded (`probe_page1_roster.py`: the page-1 roster reaches coverage 1.000
at precision 0.903, so the derived tier is not the path). The build was killed
to free CPU for the roster work at scale.

ACHIEVED AT THE STOP — against a target of 28 pages / >=2 houses / >=3 plates
and ~200 derived records minimum:

    in-corpus pages   17 of 28
    houses             2   (Breitkopf 4 plates, Litolff 1 page only)
    plates             5 of 7
    staves           359
    NAMED LABELS     281   (Breitkopf 265, Litolff 16)

⚠️ SO THE HOLDOUT HOUSE IS EFFECTIVELY ABSENT: 16 of 281 records. NO
CROSS-HOUSE CLAIM MAY BE MADE FROM THIS CACHE, and no calibration curve should
be drawn on it — that is the exact failure the sizing exercise existed to
prevent. The cached pages are KEPT because their label reads are real evidence
and may serve the roster work; they are not a completed corpus.

⚠️⚠️ OPERATIONAL TRAP — AND IT RECURRED, SO IT IS A PATTERN, NOT AN INCIDENT.
It wedged this build (18 minutes) and then wedged the roster-availability sweep
(4 minutes, at document 71 of 234) within the same session. Budget for it on
any long Surya-backed run: check liveness periodically rather than assuming
progress, and make the run RESUMABLE so a kill costs nothing (the sweep caches
per document and lost zero work; this build cached per page and lost zero).
The Surya keep-alive server's worker WEDGES AT 0% CPU and blocks its caller
SILENTLY.

⚠️⚠️ BUT 0% CPU ON THE PARENT IS NOT BY ITSELF A WEDGE, and I misdiagnosed a
healthy run on exactly that signature. A parent that shells out — the musicdiff
bridge, the Surya worker, any subprocess rung — sits at 0% while its CHILD does
the work. The wedge signature is 0% on the parent AND no child burning CPU.
Check for the child before killing anything:

    ps -eo etime,pcpu,args | grep -E "_omrned_worker|surya|llama-server"

⚠️ AND DO NOT REBASE OR CHECKOUT WHILE A LONG RUN IS READING THE TREE. A
23-step rebase swapped files under a running pricing job and killed it silently
— the log simply stopped after its header, which looks exactly like a wedge.
Finish long runs, or run them from a separate worktree, before touching git. The parent process sat at 0% with no output and no
error; `--check` reported the server healthy the whole time, because the
llama-server was alive and it was the worker that was stuck. Diagnose with
`ps -eo etime,pcpu` on the build process — 0.0% CPU with a long elapsed time is
the signature — and recover with `staff_labels_surya --stop && --serve`.
Redirecting a build's stdout through a pipe hides this: use `python3 -u` and a
plain redirect so progress is visible while it runs.


Builds the `derived`-tier corpus `probe_calibration.py` needs and does not have
(that probe has label 175 / roster 22 / derived **0**). The design is the one
this workstream was set up around:

    a publisher that labels every staff gives free identity truth at scale.
    HIDE the labels, predict from clef and score order, score the prediction
    against the labels the predictor never saw.

⚠️ THE LABEL READS ARE CACHED AS EVIDENCE, deliberately. They are the TRUTH of
this corpus, they cost Surya time, and a first bin design is usually wrong — so
the corpus must be re-scorable without re-transcribing. `--rebuild` forces a
re-read; by default an existing cache entry is reused and reported as cached.

⚠️ CONTAMINATION. `brahms--symphony-1` (Breitkopf) and `beethoven--symphony-5`
(Litolff) are EXCLUDED by name: both are in the 20-row gate this workstream
developed its rules on, and calibrating on them would measure memory. The
exclusion is asserted at startup, not left to page selection.

⚠️ TWO SCANS OF ONE PLATE ARE ONE ENGRAVING. Selection is keyed on PLATE, and
the achieved-count report is per plate as well as per house.

⚠️ LITOLFF'S TRUTH COVERAGE IS 0.64 AND THE ABSENCE IS SYSTEMATIC. That house
labels winds and brass on every system and strings NEVER, so a Litolff figure
is a figure about winds and brass. It is carried as `truth_coverage` on every
Litolff record so no downstream table can quote it without the caveat.

    python3 benchmarks/omr-staff-identity-layer-2026-09/build_calibration_corpus.py --plan
    python3 benchmarks/omr-staff-identity-layer-2026-09/build_calibration_corpus.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
CACHE = Path(os.getenv("IDCAL_CACHE", str(HERE / "corpus-cache")))

# ── the corpus, chosen on PLATE, and excluding every plate used to develop ──
#   house, work_id, plate, catalog path, pages (0-based PDF page indices)
# Pages are spread through each score and deliberately avoid page 0 (title /
# front matter). A page that yields no systems is reported, never silently
# dropped.
#
# ⚠️⚠️ MEASURED YIELD DECIDES MEMBERSHIP, NOT THE PUBLISHER AND NOT THE SERIES.
# `probe_label_yield.py`, 4 interior pages per plate, named labels / staves:
#
#     Breitkopf  brahms--symphony-4              0.89   USABLE
#     Breitkopf  brahms--piano-concerto-1        0.71   USABLE
#     Breitkopf  brahms--symphony-3              0.68   USABLE
#     Breitkopf  tchaikovsky--symphony-6         0.63   USABLE
#     Litolff    beethoven--symphony-3           0.61   USABLE
#     Litolff    beethoven--symphony-9           0.57   partial
#     Litolff    beethoven--symphony-7           0.47   partial
#     Breitkopf  brahms--ein-deutsches-requiem   0.00   NO TRUTH
#     Breitkopf  schumann--symphony-1            0.00   NO TRUTH
#     Breitkopf  mendelssohn--symphony-3         0.00   NO TRUTH
#     Breitkopf  sibelius--symphony-1            0.00   NO TRUTH
#     Breitkopf  schubert--symphony-9            0.00   NO TRUTH
#
# Five Breitkopf plates print NOTHING across 20 interior pages with 13-25
# staves each correctly detected and Surya working. So "Breitkopf labels every
# staff" is false of the HOUSE. It is nearly true of Brahms Sämtliche Werke --
# and `brahms--ein-deutsches-requiem` is in that series and prints nothing, so
# it is not simply true of the SERIES either.
#
# THE RULE THAT SURVIVES: whether a page prints staff labels is a property of
# the individual EDITION and must be MEASURED. It cannot be inferred from the
# publisher, and it cannot be inferred from the series.
#
# ✅ NOTE THIS IS THE ONE PLACE PUBLISHER IS LEGITIMATELY THE VARIABLE, and it
# is the second half of the decomposition Sean drew: **composition decides who
# is tacet; the publisher decides whether that staff disappears.** Label yield,
# condensation and tacet suppression are engraving choices, so measuring them
# per edition is exactly right. What may never be built from a publisher axis
# is a prior about WHICH INSTRUMENTS a page carries -- that is compositional,
# and this file's per-house tables say nothing about it.
#
# ⚠️ STATED LIMITATION OF THIS CORPUS: 3 of the 4 usable Breitkopf plates are
# Brahms Sämtliche Werke, the same series as the CONTAMINATED development plate
# (brahms--symphony-1, excluded by name). Different works and different plates,
# but one series -- so the Breitkopf arm is narrower than its plate count
# suggests. Litolff remains a genuine cross-house holdout.
USABLE = {  # measured mean named-label yield, from probe_label_yield.py
    "brahms--symphony-4": 0.89, "brahms--piano-concerto-1": 0.71,
    "brahms--symphony-3": 0.68, "tchaikovsky--symphony-6": 0.63,
    "beethoven--symphony-3": 0.61, "beethoven--symphony-9": 0.57,
    "beethoven--symphony-7": 0.47,
}

CORPUS = [
    # ── Breitkopf: labels EVERY staff -> truth coverage 1.00 ───────────────
    ("Breitkopf", "schumann--symphony-1", "8545",
     "editions/schumann/symphony-1-op38/schumann--symphony-1-op38--breitkopf--imslp"),
    ("Breitkopf", "mendelssohn--symphony-3", "6823",
     "editions/mendelssohn/symphony-3-op56/mendelssohn--symphony-3-op56--breitkopf--imslp"),
    ("Breitkopf", "tchaikovsky--symphony-6", "Part.B.4959",
     "editions/tchaikovsky/symphony-6-op74/tchaikovsky--symphony-6-op74--breitkopf--imslp"),
    ("Breitkopf", "sibelius--symphony-1", "30747",
     "editions/sibelius/symphony-1-op39/sibelius--symphony-1-op39--breitkopf--imslp"),
    ("Breitkopf", "schubert--symphony-9", "7954",
     "editions/schubert/symphony-9-d944/schubert--symphony-9-d944--breitkopf--imslp"),
    # ── Brahms Sämtliche Werke: the series the "labels everything" finding was
    # actually measured on. brahms--symphony-1 is the CONTAMINATED gate plate;
    # these are different works and different plates in the SAME series, and
    # they are the clean within-house contrast against the four Breitkopf
    # plates above that print nothing.
    ("Breitkopf", "brahms--symphony-3", "SW-sym3",
     "editions/brahms/symphony-3"),
    ("Breitkopf", "brahms--symphony-4", "SW-sym4",
     "editions/brahms/symphony-4"),
    ("Breitkopf", "brahms--ein-deutsches-requiem", "SW-requiem",
     "editions/brahms/ein-deutsches-requiem"),
    ("Breitkopf", "brahms--piano-concerto-1", "SW-pc1",
     "editions/brahms/piano-concerto-1"),
    # ── Litolff: winds+brass only -> truth coverage 0.64, HOLDOUT house ─────
    ("Litolff", "beethoven--symphony-3", "2767",
     "editions/beethoven/symphony-3-op55/beethoven--symphony-3-op55--litolff-1870--imslp"),
    ("Litolff", "beethoven--symphony-7", "2771",
     "editions/beethoven/symphony-7-op92/beethoven--symphony-7-op92--litolff-1870--imslp"),
    ("Litolff", "beethoven--symphony-9", "2773",
     "editions/beethoven/symphony-9-op125/beethoven--symphony-9-op125--litolff-1870--imslp"),
]
CONTAMINATED = {"brahms--symphony-1", "beethoven--symphony-5"}
# ⚠️ MEASURED, not guessed. A first pass used [3, 10, 18, 26] and page 3 of
# schumann--symphony-1 and mendelssohn--symphony-3 detected ZERO staves -- both
# are 218/244-page volumes whose front matter runs past p3. The smoke test
# caught it as "0 staves, 0 labels", which is exactly the empty-input failure
# this workstream is under standing orders to assert against. A staff-detection
# sweep over p3..p70 of all eight plates found these four non-empty on EVERY
# one (13-26 staves each), so they are chosen rather than assumed.
PAGES_PER_WORK = [6, 14, 22, 30]
TRUTH_COVERAGE = {"Breitkopf": 1.00, "Litolff": 0.64}


def catalog_editions():
    cat = json.loads((Path("/Users/seanjohnson/Desktop/ReEngrave/data/"
                           "score-library/catalog.json")).read_text())
    return [e for e in cat["entries"] if e.get("kind") == "edition"]


def resolve_corpus():
    """(house, work_id, plate, pdf Path) for every entry we can actually open."""
    eds = catalog_editions()
    by_work = defaultdict(list)
    for e in eds:
        by_work[e["work_id"]].append(e)
    out, missing = [], []
    for house, work_id, plate, _hint in CORPUS:
        if work_id in CONTAMINATED:
            raise SystemExit(f"REFUSING: {work_id} is a development plate")
        cands = [e for e in by_work.get(work_id, [])
                 if house.lower() in (e.get("publisher") or "").lower()]
        got = None
        for e in cands:
            p = LIB / e["path"]
            if p.exists():
                got = (house, work_id, plate, p, e.get("pages"))
                break
        (out if got else missing).append(got or (house, work_id, plate))
    return out, missing


def read_labels(pdf_path, page_index, dpi):
    """Cache-backed margin label read. THE TRUTH OF THIS CORPUS."""
    from tools.omr.assist import Assist
    from tools.omr.contextual import _labels_for_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.preprocessing import render_page

    pws = detect_staves(render_page(pdf_path, page_index, dpi=dpi))
    tiers = [0, 0, 0, 0, 0]
    labels = _labels_for_page(
        pws, pdf_path, page_index, assist=Assist("none"), budget=[0],
        surya_fallback=True, ocr_fallback=True, tiers=tiers)
    return [{
        "staff_index": l.staff_index, "text": l.text,
        "instrument": l.instrument.name if l.instrument else None,
        "confidence": l.confidence, "alias": l.alias,
        "y_center_px": l.y_center_px,
    } for l in labels], tiers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true",
                    help="resolve and print the corpus, transcribe nothing")
    ap.add_argument("--pages", type=int, default=len(PAGES_PER_WORK))
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--limit-works", type=int, default=0)
    ap.add_argument("--all-plates", action="store_true",
                    help="include plates measured to print no labels "
                         "(they supply no truth; for re-measuring yield only)")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    corpus, missing = resolve_corpus()
    if missing:
        print("⚠️ COULD NOT RESOLVE (reported, not skipped silently):")
        for m in missing:
            print(f"   {m}")
    if not args.all_plates:
        dropped = [c[1] for c in corpus if c[1] not in USABLE]
        corpus = [c for c in corpus if c[1] in USABLE]
        if dropped:
            print(f"\nDROPPED — measured to print no usable labels, so they "
                  f"supply no held-out truth:\n   " + "\n   ".join(dropped))
    if args.limit_works:
        corpus = corpus[: args.limit_works]

    print(f"\nCORPUS PLAN — target 20-30 pages, >=2 houses, >=3 distinct plates")
    print(f"  {'house':11s} {'work':28s} {'plate':13s} {'pdf pages':>9s}")
    for house, work, plate, pdf, npages in corpus:
        print(f"  {house:11s} {work:28s} {plate:13s} {str(npages):>9s}")
    plates = {(h, p) for h, _, p, _, _ in corpus}
    print(f"\n  houses {len({h for h,_,_,_,_ in corpus})}  "
          f"distinct plates {len(plates)}  "
          f"pages requested {len(corpus) * args.pages}")
    if args.plan:
        return 0

    from tools.omr.transcribe import transcribe

    records, per_plate, per_house = [], Counter(), Counter()
    failures = []
    for house, work, plate, pdf, _n in corpus:
        for pi in PAGES_PER_WORK[: args.pages]:
            key = f"{work}--p{pi}"
            cpath = CACHE / f"{key}.json"
            if cpath.exists() and not args.rebuild:
                blob = json.loads(cpath.read_text())
                print(f"  cached  {key}")
            else:
                t0 = time.time()
                try:
                    # contextual OFF: it would attach join outputs this corpus
                    # must not read, and its Surya pass duplicates the label
                    # read below. Raw clefs come from the detector regardless.
                    res = transcribe(pdf_path=pdf, pages=[pi], dpi=args.dpi,
                                     contextual=False, progress=False)
                    labels, tiers = read_labels(pdf, pi, args.dpi)
                    blob = {"house": house, "work": work, "plate": plate,
                            "page_index": pi, "pdf": str(pdf),
                            "truth_coverage": TRUTH_COVERAGE[house],
                            "label_tiers": tiers, "labels": labels,
                            "result": res, "seconds": round(time.time()-t0, 1)}
                    cpath.write_text(json.dumps(blob))
                    print(f"  built   {key}  {blob['seconds']}s  "
                          f"{len(labels)} labels")
                except Exception as exc:
                    failures.append((key, repr(exc)))
                    print(f"  FAILED  {key}  {exc!r}")
                    traceback.print_exc(limit=2)
                    continue
            records.append(blob)
            per_plate[(house, plate)] += 1
            per_house[house] += 1

    print(f"\n{'='*66}\nACHIEVED COUNTS vs TARGET\n{'='*66}")
    print(f"  {'house':11s} {'plate':14s} {'pages':>6s} {'staves':>7s} "
          f"{'labels':>7s}")
    tot_st = tot_lb = 0
    for (house, plate), npg in sorted(per_plate.items()):
        st = sum(b["result"].get("n_staves_total", 0) for b in records
                 if b["house"] == house and b["plate"] == plate)
        lb = sum(len(b["labels"]) for b in records
                 if b["house"] == house and b["plate"] == plate)
        tot_st += st; tot_lb += lb
        print(f"  {house:11s} {plate:14s} {npg:6d} {st:7d} {lb:7d}")
    print(f"\n  pages {sum(per_house.values())}   houses {len(per_house)}   "
          f"plates {len(per_plate)}   staves {tot_st}   labels read {tot_lb}")
    print(f"  TARGET was 20-30 pages, >=2 houses, >=3 distinct plates, "
          f"~200 derived records minimum")
    if failures:
        print(f"\n  ⚠️ FAILURES ({len(failures)}):")
        for k, e in failures:
            print(f"     {k}  {e}")
    (HERE / "corpus-manifest.json").write_text(json.dumps({
        "pages": sum(per_house.values()),
        "per_house": dict(per_house),
        "per_plate": {f"{h}/{p}": n for (h, p), n in per_plate.items()},
        "staves": tot_st, "labels_read": tot_lb,
        "failures": failures,
        "cache": str(CACHE),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
