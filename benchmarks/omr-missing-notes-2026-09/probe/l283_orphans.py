#!/usr/bin/env python3
"""l283_orphans: the detector's flag boxes that no duration verdict used ("orphans"), and which stemless heads each would
attach to under the geometry a flag has -- measured on a record, and on Sean's page against his levels. ROADMAP 2.83 probe.

A flag box is drawn from the far end (tip) of its stem; `flag8thDown` hangs from a DOWN stem (the stem stands at the head's
LEFT edge, the flag's box starts at it and runs up from the tip toward the head), `flag8thUp` from an UP stem (the head's RIGHT
edge, the flag runs down from the tip). CLAUDE.md 10: stems up -> right, down -> left (96 of 96 against print). So a head with
NO CV stem can be the flag's own where:
  * the flag's class direction D says which edge: Down -> flag x0 within X spaces of the head's left edge, Up -> of its right;
  * the head lies on the BODY side of the flag: for Down the head's bottom is above the flag's tip (the box bottom), for Up the
    head's top is below the flag's tip (the box top), and the head is within MAXLEN spaces of the tip along the stem;
  * no CV stem of the cell stands within the join tolerance of the flag box (else it is some stem's flag: not an orphan).

    python3 l283_orphans.py --record rec.json [--rows truth_rows.json --arm base]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

X_SPACES = 0.5
MAXLEN_SPACES = 7.0
MIN_LEN_SPACES = 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--rows", default=None)
    ap.add_argument("--arm", default="base")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    used = set()
    for v in run.verdicts:
        if v["quantity"] == Q.DURATION and v["decider"] == "adjudicate_duration":
            used.update(v.get("basis") or [])
    # cells: heads, flags, stems, space
    cells = collections.defaultdict(lambda: {"heads": [], "flags": [], "stems": [], "space": None})
    for k, g in run.glyphs.items():
        c = cells[g.cell_key]
        if (g.cls or "").startswith("notehead") and g.box_canon:
            c["heads"].append((k, g))
        elif (g.cls or "").startswith("flag") and g.box_canon:
            c["flags"].append((k, g))
    for ck, c in cells.items():
        for o in run.obs_at(ck, Q.STEM):
            c["stems"].append(o["value"])
        sp = run.obs_at(ck, Q.CELL_STAFF_SPACE)
        c["space"] = float(sp[-1]["value"]) if sp else None
    refused = {v["subject"] for v in run.verdicts if v["quantity"] == Q.FLAG_IS_NOT_A_FLAG and v["outcome"] == "decided" and v["value"] is True}
    n_flags = n_used = n_orphan = n_refused = 0
    cand_counts = collections.Counter()
    attach = {}
    for ck, c in cells.items():
        sp = c["space"]
        if not sp:
            continue
        for fk, f in c["flags"]:
            n_flags += 1
            if fk in refused:
                n_refused += 1
                continue
            fo = run.obs_at(fk, Q.FLAG)
            if any(o["id"] in used for o in fo):
                n_used += 1
                continue
            n_orphan += 1
            fx0, fy0, fx1, fy1 = f.box_canon
            D = "down" if f.cls.lower().endswith("down") else "up" if f.cls.lower().endswith("up") else None
            # a CV stem near the flag box => it is that stem's flag
            near_stem = any(max(0.0, max(sx, fx0) - min(sx + sw, fx1)) <= 0.8 * sp and max(0.0, max(sy, fy0) - min(sy + sh, fy1)) <= 0.8 * sp
                            for sx, sy, sw, sh in c["stems"])
            cands = []
            for hk, h in c["heads"]:
                hx0, hy0, hx1, hy1 = h.box_canon
                if D == "down":
                    ok_x = abs(fx0 - hx0) <= X_SPACES * sp
                    ok_y = hy1 <= fy1 - MIN_LEN_SPACES * sp and (fy1 - hy1) <= MAXLEN_SPACES * sp
                elif D == "up":
                    ok_x = abs(fx0 - hx1) <= X_SPACES * sp or abs(fx0 - (hx1 - 0.3 * sp)) <= X_SPACES * sp
                    ok_y = hy0 >= fy0 + MIN_LEN_SPACES * sp and (hy0 - fy0) <= MAXLEN_SPACES * sp
                else:
                    continue
                if ok_x and ok_y:
                    cands.append(hk)
            cand_counts[(f.cls, "near_a_cv_stem" if near_stem else "no_stem_near", len(cands))] += 1
            attach[fk] = (f.cls, near_stem, cands)
    print(f"flag boxes {n_flags}: used by a duration verdict {n_used}, refused as not-a-flag {n_refused}, ORPHANS {n_orphan}")
    for k, n in sorted(cand_counts.items()):
        print("  ", n, k)
    if a.rows:
        rows = json.loads(Path(a.rows).read_text())
        truth = {r[a.arm + "_key"]: r for r in rows if r.get(a.arm + "_key")}
        good = bad = unk = 0
        for fk, (cls, near_stem, cands) in attach.items():
            if near_stem:
                continue
            for hk in cands:
                r = truth.get(hk)
                if r is None:
                    unk += 1
                elif r["level"] >= 1:
                    good += 1
                else:
                    bad += 1
                    print("   WRONG ATTACH:", hk, "truth level", r["level"], r["kind"], "flag", fk, cls)
        print(f"on the hand-truth page, heads an orphan flag would attach to (no CV stem near the flag): level>=1 {good}, level 0 {bad}, not judged {unk}")


if __name__ == "__main__":
    main()
