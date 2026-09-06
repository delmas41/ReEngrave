#!/usr/bin/env python3
"""KC-3 — what does the wired roster COST, in edits on the 20-row scan gate?

EXPORT-ONLY over documents `probe_roster_identity.py` already produced, so no
detector runs and no margin is read twice. Three arms:

    BASELINE  the committed fixture, re-exported UNMODIFIED by this tree
    OFF       contextual re-run on this tree with OMR_ROSTER=0
    ON        contextual re-run on this tree with OMR_ROSTER=1

⚠️ THE PAIR THAT PRICES THE FLAG IS **OFF vs ON**, never BASELINE vs ON.
BASELINE carries whatever contextual wrote when the fixture was made, on an
older tree; re-running contextual at all moves some rows for reasons that have
nothing to do with the roster. Quoting ON − BASELINE would charge the roster for
every one of them. BASELINE is here as a CONTROL: it says how far this tree's
exporter has drifted from the committed gate, and that drift is a known,
attributed quantity (`a4918874`, the whole-measure-rest fermata, worth roughly
±10 edits on 5 rows — see `price_clef_consumer.py`'s control section).

⚠️ `0.8444` IS NOT A BASELINE FOR THIS TREE, and no absolute figure from this
harness is quoted as the gate's. **The scan gate's noise floor is ±6 edits**, so
a delta inside ±6 is not a result.

    export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
    python3 benchmarks/omr-roster-wiring-2026-09/probe_roster_identity.py   # first
    python3 benchmarks/omr-roster-wiring-2026-09/price_roster_consumers.py

── KC-3 RESULT 2026-09-05: THE ROSTER COSTS **EXACTLY ZERO EDITS** ───────────

16 rows priced (the four Mahler rows are EXCLUDED and named — the identity
probe abstained on them because this tree's staff detection disagrees with the
committed fixture).

    BASELINE  63652
    OFF       63652   (+0 vs BASELINE)
    ON        63652   (+0 vs OFF  ⭑ the roster's price)

**Every single row is +0, not a compensating mixture**, and OFF == BASELINE on
every row as well. That second equality is a strong control in its own right:
re-running the whole contextual pass on this tree, clefs and all, with the flag
off, reproduces the stored export byte for byte. The harness is not measuring
itself.

⭑ SO THE ROSTER CORRECTS 27 STAFF NAMES AND TOUCHES NOTHING ELSE — no note, no
clef, no measure. That is the pre-registered PASS condition for part naming
(|delta| <= 6), and the pre-registration is explicit about why: musicdiff does
not score `<part-name>`, so the metric CANNOT see this consumer's value, and
the edit measurement's only job here is to prove it costs nothing. A non-zero
delta would have meant the roster changed something other than a name.

⚠️ THE STANDING "ZERO EDITS SHIPS DISABLED" RULE IS ABOUT CONSUMERS THE METRIC
CAN SEE, and this one it provably cannot. That distinction was written down
BEFORE the number was known (`PRE_REGISTERED.md`), which is the only thing that
makes it an argument rather than an excuse. The default is still Sean's.

── CONTROL: the drift is the known one, reproduced exactly ───────────────────

Four of 16 rows differ from the committed gate, and they are the SAME four
rows and the SAME magnitudes `price_clef_consumer.py` attributed to `a4918874`
("export: the whole-measure rest wears its fermata", 2026-09-04, an ancestor of
this branch that POSTDATES the committed `.omr.musicxml`):

    beethoven-575951-p1  -4    beethoven-984073-p1  -10
    beethoven-575951-p2  +1    beethoven-984073-p2   +6

Independent reproduction of an attributed drift from a different harness. It
affects only the comparison to the gate's absolute numbers, and no absolute
number from this harness is quoted as the gate's.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import omr_ned as omr_ned_mod          # noqa: E402
from tools.omr.export import to_musicxml              # noqa: E402

RECON = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
             "reconciliation/benchmarks/omr-scan-e2e-2026-09")
FIXTURES = RECON / "fixtures"
COMMITTED = RECON / "results-reconciliation.json"
TAG = ".reconciliation"
ARMS = Path(os.getenv("ROSTER_ARMS", "/tmp/roster-arms"))
SCRATCH = Path(os.getenv("ROSTER_SCRATCH", "/tmp/roster-price"))


def main():
    if not os.getenv("OMRNED_PYTHON"):
        raise SystemExit("set OMRNED_PYTHON to the main checkout's .venv-omrned")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    fixtures = sorted(FIXTURES.glob(f"*{TAG}.omr.json"))
    if len(fixtures) != 20:
        raise SystemExit(f"expected 20 gate rows, found {len(fixtures)}")

    all_rids = [p.name[: -len(f"{TAG}.omr.json")].rstrip(".") for p in fixtures]
    # ⚠️ A row with no arm document is one `probe_roster_identity.py` ABSTAINED
    # on — this tree's staff detection disagrees with the committed fixture, so
    # writing identity onto the fixture's staff dicts would be writing onto the
    # wrong staves. Those rows are EXCLUDED from both arms and named, rather
    # than silently carried at delta 0, which would dilute the pooled figure
    # with rows the flag never touched.
    rids = [r for r in all_rids if (ARMS / f"{r}.ON.omr.json").exists()]
    excluded = [r for r in all_rids if r not in rids]
    if not rids:
        raise SystemExit(f"no arm documents in {ARMS} — run "
                         f"probe_roster_identity.py first")
    print(f"rows priced: {len(rids)}   EXCLUDED (probe abstained): "
          f"{len(excluded)} {excluded}")

    docs = {
        "BASELINE": {r: json.loads(
            (FIXTURES / f"{r}{TAG}.omr.json").read_text()) for r in rids},
        "OFF": {r: json.loads((ARMS / f"{r}.OFF.omr.json").read_text())
                for r in rids},
        "ON": {r: json.loads((ARMS / f"{r}.ON.omr.json").read_text())
               for r in rids},
    }

    results = {}
    for arm, by_row in docs.items():
        pairs = []
        for rid, doc in by_row.items():
            xml = SCRATCH / f"{rid}.{arm}.musicxml"
            xml.write_text(to_musicxml(doc))
            pairs.append((rid, str(xml),
                          str(FIXTURES / f"{rid}.truth.musicxml")))
        # ⚠️ `detail` is a musicdiff DETAIL LEVEL STRING, not a boolean. The
        # default is what the gate itself scores with; passing anything else
        # would change the categories AND the edit count.
        scored = omr_ned_mod.score_batch(pairs)
        by = {s["name"]: s for s in scored.get("scores",
                                               scored.get("pairs", []))}
        if not by:
            raise SystemExit(f"scorer returned nothing; keys {list(scored)}")
        results[arm] = by
        print(f"  {arm:9s} exported and scored, "
              f"{sum(s.get('omr_ed', 0) or 0 for s in by.values())} edits")

    committed = json.loads(COMMITTED.read_text())
    comm = {}
    for r in committed.get("rows", committed):
        rid = r["row_id"]
        if rid.endswith(TAG):
            rid = rid[: -len(TAG)]
        comm[rid.rstrip(".")] = r

    print(f"\n{'='*100}\nCONTROL — this tree's re-export of the UNMODIFIED "
          f"fixture vs the committed gate\n{'='*100}")
    print(f"{'row':38s} {'committed':>10s} {'BASELINE':>10s} {'drift':>7s}")
    drift = 0
    for rid in rids:
        c = ((comm.get(rid) or {}).get("omr_ned") or {}).get("omr_ed")
        b = results["BASELINE"].get(rid, {}).get("omr_ed")
        d = (b - c) if (c is not None and b is not None) else None
        if d not in (0, None):
            drift += 1
        print(f"{rid:38s} {str(c):>10s} {str(b):>10s} {str(d):>7s}")
    print(f"\n  {drift} of {len(rids)} rows drift from the committed gate. "
          f"This is CONTEXT, not the result — see the docstring.")

    print(f"\n{'='*100}\nKC-3 — the roster flag, priced OFF vs ON\n{'='*100}")
    print(f"{'row':38s} {'BASELINE':>9s} {'OFF':>14s} {'ON':>14s}")
    moved = []
    for rid in rids:
        base = results["BASELINE"].get(rid, {}).get("omr_ed")
        off = results["OFF"].get(rid, {}).get("omr_ed")
        on = results["ON"].get(rid, {}).get("omr_ed")
        d_on = on - off if (on is not None and off is not None) else None
        if d_on:
            moved.append((rid, d_on))
        print(f"{rid:38s} {str(base):>9s} "
              f"{f'{off}({off - base:+d})':>14s} "
              f"{f'{on}({d_on:+d})':>14s}")
    tot = {a: sum(s.get("omr_ed", 0) or 0 for s in results[a].values())
           for a in results}
    print(f"\n  BASELINE {tot['BASELINE']:6d}")
    print(f"  OFF      {tot['OFF']:6d}   ({tot['OFF'] - tot['BASELINE']:+d} vs "
          f"BASELINE — contextual re-run on this tree, NOT the roster)")
    print(f"  ON       {tot['ON']:6d}   ({tot['ON'] - tot['OFF']:+d} vs OFF — "
          f"⭑ THIS IS THE ROSTER'S PRICE)")
    delta = tot["ON"] - tot["OFF"]
    print(f"\n  rows that moved: {moved or 'none'}")
    print(f"  ⚠️ noise floor is ±6 edits. |delta| = {abs(delta)} -> "
          f"{'INSIDE the noise floor: not a result' if abs(delta) <= 6 else 'outside the noise floor'}")

    (HERE / "kc3-roster-price.json").write_text(json.dumps(
        {"totals": tot, "delta_on_minus_off": delta,
         "moved": moved, "results": results}, indent=1))
    print(f"\n  wrote {HERE/'kc3-roster-price.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
