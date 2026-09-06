#!/usr/bin/env python3
"""KC-1 and KC-2 — does the WIRED roster acquire, and does identity move?

⚠️ THIS RUNS THE PRODUCTION PATH, not a re-implementation. Each arm calls
`contextual.apply_contextual_analysis` on the gate's stored transcription with
freshly detected staves, exactly as `transcribe` does, and reads the identity
back off the staff dicts it mutates. The only thing the probe supplies is the
truth and the scoring.

TWO ARMS, one difference:

    OFF   OMR_ROSTER=0 — today
    ON    OMR_ROSTER=1 — a roster name may fill a slot the run's pages did not

⚠️ THE LABEL READS ARE CACHED ACROSS ARMS, deliberately. Surya's temperature
nondeterminism is documented in `contextual.py` (45 replays, one character
flipping between sessions on identical bytes); without a cache the two arms
would differ by the reader as well as by the flag, and every delta would be
uninterpretable. The cache is keyed on (pdf, page_index) and is the same
discipline `roster.py` states for the production read.

⚠️ STAFF DETECTION IS ALSO CACHED, and asserted against the fixture. The
fixture's staff dicts are what identity is written onto; if fresh detection
disagrees with the fixture about how many staves a system has, the join would
be writing onto the wrong staves and the row ABSTAINS rather than reporting.

    export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
    python3 benchmarks/omr-roster-wiring-2026-09/probe_roster_identity.py
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
FIXTURES = MAIN / (".claude/worktrees/reconciliation/benchmarks/"
                   "omr-scan-e2e-2026-09/fixtures")
TAG = "reconciliation"
WORKS = REPO / "benchmarks/omr-scan-e2e-2026-09/works.json"
ARMS = Path(os.getenv("ROSTER_ARMS", "/tmp/roster-arms"))

PUBLISHER = {"beethoven": "Litolff", "brahms": "Breitkopf",
             "dvorak": "Simrock", "mahler": "Peters", "bach": "?"}

_STAVES: dict[tuple[str, int], object] = {}
_LABELS: dict[tuple[str, int], list] = {}


def install_caches():
    """Memoize staff detection and the label ladder, per (pdf, page)."""
    from tools.omr import contextual as C
    from tools.omr import roster as R

    real_labels = C._labels_for_page

    def cached_labels(pws, pdf_path, page_index, **kw):
        key = (str(pdf_path), int(page_index))
        if key not in _LABELS:
            _LABELS[key] = real_labels(pws, pdf_path, page_index, **kw)
        return _LABELS[key]

    C._labels_for_page = cached_labels

    real_render = R.__dict__.get("render_page")  # imported lazily inside
    return real_labels


def staves_for(pdf_path: Path, page_index: int, dpi: int):
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    key = (str(pdf_path), int(page_index))
    if key not in _STAVES:
        _STAVES[key] = detect_staves(render_page(pdf_path, page_index, dpi=dpi))
    return _STAVES[key]


def canonical(name):
    from tools.omr import instruments as INST
    if not name:
        return None
    m = INST.lookup(str(name))
    return m.instrument.name if m else None


def acceptable(name):
    """Every canonical name a truth string may legitimately come out as."""
    c = canonical(name)
    return {c} if c else set()


def resolve_truth(row, by_id, _depth=0):
    """The row's staff lineup, following `same-as:` aliases.

    ⚠️ The two Beethoven rows carry their truth as a STRING alias to the other
    scan of the same Litolff plate. Reading `row["staves"]` directly gets the
    string `"same-as:..."` and either crashes or silently scores nothing. Same
    resolution `probe_heldout_identity.py` uses.
    """
    if _depth > 4:
        return None
    st = row.get("staves")
    if isinstance(st, str) and st.startswith("same-as:"):
        return resolve_truth(by_id[st.split(":", 1)[1]], by_id, _depth + 1)
    if isinstance(st, list):
        return st
    sap = (row.get("condensation") or {}).get("staves_as_printed")
    return sap if isinstance(sap, list) else None


def systems_of(doc):
    out = []
    for page in doc.get("pages", []):
        for system in page.get("systems", []):
            if system.get("staves"):
                out.append((page.get("page_index"), system.get("system_index"),
                            system["staves"]))
    return out


def run_arm(doc, pdf_path, dpi, staved, use_roster: bool):
    """One arm. Returns (mutated copy, contextual summary)."""
    from tools.omr.assist import Assist
    from tools.omr.contextual import apply_contextual_analysis
    os.environ["OMR_ROSTER"] = "1" if use_roster else "0"
    work = copy.deepcopy(doc)
    # Wipe the identity the fixture already carries, so an arm cannot read its
    # own answer key out of the file it is about to rewrite.
    for _pi, _si, staves in systems_of(work):
        for st in staves:
            for k in ("instrument", "instrument_family", "instrument_source",
                      "instrument_label", "slot_index", "unpitched"):
                st.pop(k, None)
    # ⚠️ `apply_clefs=True` — the PRODUCTION configuration. Identity is computed
    # before clef correction runs, so the KC-2 comparison is unaffected, and it
    # means the documents this dumps are the ones KC-3 can price without a
    # second (nondeterministic, slow) label read.
    summary = apply_contextual_analysis(
        work, pdf_path=pdf_path, dpi=dpi, apply_clefs=True,
        assist=Assist("none"), staved=staved)
    return work, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="*", default=None)
    args = ap.parse_args()

    install_caches()
    works = json.loads(WORKS.read_text())
    by_id = {r["row_id"]: r for r in works["rows"]}

    records = []
    acquisitions = {}
    abstained = []

    for row in works["rows"]:
        rid = row["row_id"]
        if args.rows and rid not in args.rows:
            continue
        f = FIXTURES / f"{rid}.{TAG}.omr.json"
        if not f.exists():
            abstained.append((rid, "no fixture"))
            continue
        doc = json.loads(f.read_text())
        pdf_path = Path(doc["source_pdf"])
        if not pdf_path.exists():
            abstained.append((rid, "source pdf missing"))
            continue
        dpi = doc.get("dpi") or 300
        page_indices = [p.get("page_index") for p in doc.get("pages", [])]

        # ── the assertion that makes the arms meaningful ────────────────────
        staved = [staves_for(pdf_path, i, dpi) for i in page_indices]
        fx_sizes = [len(s) for _, _, s in systems_of(doc)]
        fresh = []
        for pws in staved:
            by_sys = defaultdict(int)
            for st in pws.staves:
                by_sys[st.system_index] += 1
            fresh.extend(v for _k, v in sorted(by_sys.items()))
        if fresh != fx_sizes:
            abstained.append((rid, f"detection {fresh} != fixture {fx_sizes}"))
            continue

        print(f"  {rid} ...", flush=True)
        off, sum_off = run_arm(doc, pdf_path, dpi, staved, False)
        on, sum_on = run_arm(doc, pdf_path, dpi, staved, True)
        # Dumped so KC-3 can price these EXACT documents without paying for a
        # second label read — which would also be a second roll of Surya's
        # temperature dice, and the two arms would then differ by the reader.
        ARMS.mkdir(parents=True, exist_ok=True)
        (ARMS / f"{rid}.OFF.omr.json").write_text(json.dumps(off))
        (ARMS / f"{rid}.ON.omr.json").write_text(json.dumps(on))
        acquisitions[rid] = {
            "roster": sum_on.get("roster"),
            "offered": sum_on.get("roster_slots_offered"),
            "from_roster": sum_on.get("instruments_from_roster"),
            "from_score_order_off": sum_off.get("instruments_from_score_order"),
            "from_score_order_on": sum_on.get("instruments_from_score_order"),
        }

        truth = resolve_truth(row, by_id) or []
        tnames = [canonical(t.get("name")) for t in truth]
        for (pi, si, s_off), (_pi2, _si2, s_on) in zip(systems_of(off),
                                                       systems_of(on)):
            if not truth or len(s_off) != len(truth):
                abstained.append((f"{rid} sys{si}",
                                  f"n {len(s_off)} != truth {len(truth)}"))
                continue
            for i, (a, b) in enumerate(zip(s_off, s_on)):
                records.append({
                    "row_id": rid, "publisher": PUBLISHER.get(
                        rid.split("-")[0], "?"),
                    "page_index": pi, "system_index": si, "ordinal": i,
                    "TRUTH": tnames[i],
                    "TRUTH_printed": truth[i].get("name"),
                    "OFF": a.get("instrument"),
                    "OFF_source": a.get("instrument_source"),
                    "ON": b.get("instrument"),
                    "ON_source": b.get("instrument_source"),
                })

    # ── KC-1: ACQUISITION ───────────────────────────────────────────────────
    print(f"\n{'='*94}\nKC-1  ACQUISITION — the roster as the WIRED path read "
          f"it\n{'='*94}")
    print(f"  {'row':38s} {'page':>4s} {'sys':>3s} {'stav':>4s} {'named':>5s} "
          f"{'opened':>16s}  tiers")
    seen_edition = {}
    for rid, a in acquisitions.items():
        r = a["roster"]
        if not r:
            print(f"  {rid:38s}    -   -    -     -  {'':>16s}  NO ROSTER")
            continue
        t = r["label_tiers"]
        print(f"  {rid:38s} {r['page_index']:4d} {r['system_index']:3d} "
              f"{r['n_staves']:4d} {r['named']:5d} "
              f"{str(r['pages_opened']):>16s}  "
              f"tl={t['text_layer']} su={t['surya']} te={t['tesseract']}")
        seen_edition.setdefault(rid.rsplit("-p", 1)[0], r)

    # acquisition correctness, against works.json truth for the roster PAGE
    print(f"\n  acquisition correctness (roster page's own truth row, where one "
          f"exists):")
    acq_named = acq_right = 0
    for edition, r in sorted(seen_edition.items()):
        trow = None
        for cand_id, row in by_id.items():
            if cand_id.rsplit("-p", 1)[0] != edition:
                continue
            if (row.get("page") or {}).get("pdf_page_index") == r["page_index"] \
                    and resolve_truth(row, by_id):
                trow = row
                break
        if trow is None:
            print(f"    {edition:34s} roster page {r['page_index']}: "
                  f"{r['named']} named, NO TRUTH ROW — not scored")
            continue
        tnames = [canonical(t.get("name")) for t in resolve_truth(trow, by_id)]
        n_ok = n_bad = 0
        bad = []
        for e in r["entries"]:
            o = e["ordinal"]
            if o < len(tnames) and tnames[o] == e["instrument"]:
                n_ok += 1
            else:
                n_bad += 1
                bad.append((o, tnames[o] if o < len(tnames) else None,
                            e["instrument"], e["text"]))
        acq_named += n_ok + n_bad
        acq_right += n_ok
        print(f"    {edition:34s} roster page {r['page_index']}: "
              f"{n_ok + n_bad} named / {r['n_staves']} staves, "
              f"CORRECT {n_ok}")
        for o, t, g, txt in bad:
            print(f"        ⚠️ ord {o:2d}: truth {t} -> READ AS {g}  ({txt!r})")
    if acq_named:
        print(f"\n  ⭑ ACQUISITION PRECISION {acq_right}/{acq_named} = "
              f"{acq_right/acq_named:.3f}")

    # ── KC-2: IDENTITY ──────────────────────────────────────────────────────
    print(f"\n{'='*94}\nKC-2  IDENTITY — OFF vs ON, {len(records)} truth-bearing "
          f"staff records\n{'='*94}")

    def score(arm, subset=None):
        rs = [r for r in records if r["TRUTH"]]
        if subset:
            rs = [r for r in rs if subset(r)]
        named = [r for r in rs if r[arm]]
        right = [r for r in named if r[arm] in acceptable(r["TRUTH_printed"])
                 or r[arm] == r["TRUTH"]]
        return (len(rs), len(named), len(named) / len(rs) if rs else 0,
                len(right), len(right) / len(named) if named else 0)

    print(f"  {'arm':6s} {'n':>4s} {'named':>6s} {'cov':>7s} {'right':>6s} "
          f"{'prec':>7s}")
    for arm in ("OFF", "ON"):
        n, named, cov, right, prec = score(arm)
        print(f"  {arm:6s} {n:4d} {named:6d} {cov:7.3f} {right:6d} {prec:7.3f}")

    print(f"\n  by publisher:")
    print(f"  {'publisher':12s} {'arm':4s} {'n':>4s} {'named':>6s} {'cov':>7s} "
          f"{'right':>6s} {'prec':>7s}")
    for pub in sorted({r["publisher"] for r in records}):
        for arm in ("OFF", "ON"):
            n, named, cov, right, prec = score(
                arm, lambda r, p=pub: r["publisher"] == p)
            print(f"  {pub:12s} {arm:4s} {n:4d} {named:6d} {cov:7.3f} "
                  f"{right:6d} {prec:7.3f}")

    changed = [r for r in records if r["OFF"] != r["ON"]]
    print(f"\n  staves whose NAME changed: {len(changed)}")
    tally = Counter()
    for r in changed:
        if not r["TRUTH"]:
            tally["no truth"] += 1
            continue
        was = r["OFF"] == r["TRUTH"]
        now = r["ON"] == r["TRUTH"]
        tally[("fixed" if now and not was else
               "broken" if was and not now else
               "still right" if now else "still wrong")] += 1
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"    {str(k):14s} {v}")
    for r in changed[:40]:
        if r["TRUTH"] and r["OFF"] != r["TRUTH"] and r["ON"] == r["TRUTH"]:
            mark = "✅"
        elif r["TRUTH"] and r["OFF"] == r["TRUTH"] and r["ON"] != r["TRUTH"]:
            mark = "⚠️"
        else:
            mark = "  "
        print(f"    {mark} {r['row_id']:34s} s{r['system_index']} "
              f"ord{r['ordinal']:2d}  truth {str(r['TRUTH']):14s} "
              f"{str(r['OFF']):14s} ({r['OFF_source']}) -> "
              f"{str(r['ON']):14s} ({r['ON_source']})")

    src_off = Counter(r["OFF_source"] for r in records)
    src_on = Counter(r["ON_source"] for r in records)
    print(f"\n  provenance, all {len(records)} records:")
    for k in sorted(set(src_off) | set(src_on), key=lambda x: str(x)):
        print(f"    {str(k):22s} OFF {src_off.get(k, 0):4d}   "
              f"ON {src_on.get(k, 0):4d}")

    if abstained:
        print(f"\n  ABSTAINED ({len(abstained)}):")
        for rid, why in abstained:
            print(f"    {rid:44s} {why}")

    (HERE / "roster-identity.json").write_text(json.dumps(
        {"meta": {"fixtures": str(FIXTURES), "tag": TAG,
                  "n_records": len(records)},
         "acquisitions": acquisitions, "records": records,
         "abstained": abstained}, indent=1))
    print(f"\n  wrote {HERE/'roster-identity.json'}")


if __name__ == "__main__":
    main()
