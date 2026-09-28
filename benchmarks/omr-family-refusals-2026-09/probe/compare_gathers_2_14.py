"""BASE vs ARM gather, ROADMAP 2.14 — a GATHER change, priced by two full
re-gathers (CLAUDE.md §6b: `readjudicate`/`reexport_arm` are structurally
blind to a GATHER change).

    python3 .../compare_gathers_2_14.py <base.record.json> <arm.record.json> --out <json>

⚠️ UNLIKE `compare_gathers_g3.py`, THE TWO COMMITS ARE EXPECTED TO DIFFER.
That comparator polices a single-tree, flag-toggled A/B and refuses two
different commits outright; 2.14 has no flag (a GATHER change cannot be one
here — the rung-naming is unconditional) so base and arm are necessarily two
commits. What this script polices instead is CLAUDE.md's actual rule:
**base must be an ANCESTOR of arm** (`git merge-base --is-ancestor`), so the
diff is priced against nothing but this lane's own change, and BOTH records
must carry `dirty: False` (a dirty record is not a baseline).

Reports: the detector's box set (jitter control -- identical means every
difference below is the change's, not run-to-run noise); the ladder tally
(rows now carrying a named `rungs` list); every `Q.GLYPH_OWNER` verdict that
MOVED, named by subject, with the arm's own `ladder_discounted_rungs` beside
it; `<note>` counts through `staged.export` and whether the MusicXML is
byte-identical; the census.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path.cwd()))

from tools.omr.staged import export as SX                  # noqa: E402
from tools.omr.staged.record import Q                       # noqa: E402
from tools.omr.staged.record_io import load_record          # noqa: E402


def _is_ancestor(base_commit: str, arm_commit: str) -> bool:
    if base_commit == arm_commit:
        return True
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", base_commit, arm_commit],
            cwd=str(ROOT), check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def word(v):
    if v["outcome"] != "decided":
        return f"ABSTAINED:{v.get('reason')}"
    if v["quantity"] == Q.LEDGER_IS_NOT_A_LEDGER:
        return (f"refused:{v.get('reason')}" if v["value"] is True
                else f"kept:{v.get('reason')}")
    return f"{json.dumps(v.get('value'), default=str)}|{v.get('reason')}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("arm")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    B, A = load_record(a.base), load_record(a.arm)
    pb, pa = B.get("provenance") or {}, A.get("provenance") or {}
    if pb.get("dirty") is not False or pa.get("dirty") is not False:
        print("PROVENANCE REFUSED (dirty):", pb, pa)
        return 3
    if not _is_ancestor(pb.get("commit"), pa.get("commit")):
        print("PROVENANCE REFUSED (base is not an ancestor of arm):",
              pb.get("commit"), pa.get("commit"))
        return 3
    rb, ra = B["record"], A["record"]

    def boxes(r):
        return sorted((o["subject"], json.dumps(o["value"]))
                      for o in r["observations"]
                      if o["quantity"] == Q.GLYPH_BOX)
    bb, ba = boxes(rb), boxes(ra)

    def ladder_rows(r):
        return [o for o in r["observations"] if o["quantity"] == Q.GLYPH_LADDER]
    lb, la = ladder_rows(rb), ladder_rows(ra)
    named_arm = [o for o in la if isinstance((o.get("detail") or {}).get("rungs"),
                                             list)]
    named_base = [o for o in lb if isinstance((o.get("detail") or {}).get("rungs"),
                                              list)]
    # ⚠️ "LOST A RUNG": a named ladder row on the ARM whose `expected` exceeds
    # the ARM'S OWN `found` minus the rungs `glyph_owner` would go on to
    # discount cannot be read from GATHER alone (the discount happens in
    # ADJUDICATE) -- so this counts ladder ROWS eligible for a discount
    # (named, non-empty) as the GATHER-side population, and the ADJUDICATE
    # section below (`glyph_owner_moved`) is where a rung actually being
    # dropped shows up as a verdict change.
    ladder_named_nonempty_arm = sum(
        1 for o in named_arm if (o.get("detail") or {}).get("rungs"))

    vb = {(v["quantity"], v["subject"]): v for v in rb["verdicts"]}
    va = {(v["quantity"], v["subject"]): v for v in ra["verdicts"]}
    moved = collections.Counter()
    named = collections.defaultdict(list)
    owner_moved = []
    for k in sorted(set(vb) | set(va)):
        wb = word(vb[k]) if k in vb else "<absent>"
        wa = word(va[k]) if k in va else "<absent>"
        if wb != wa:
            moved[k[0]] += 1
            if len(named[k[0]]) < 40:
                named[k[0]].append({"subject": k[1], "base": wb, "arm": wa})
            if k[0] == Q.GLYPH_OWNER:
                arm_detail = va[k].get("detail") or {} if k in va else {}
                owner_moved.append({
                    "subject": k[1], "base": wb, "arm": wa,
                    "ladder_discounted_rungs":
                        arm_detail.get("ladder_discounted_rungs")})

    # every GLYPH_OWNER verdict on the arm that discounted a rung, whether or
    # not the WINNER changed -- CLAUDE.md: report a losing candidate's
    # discount too.
    owner_discounted_any = []
    for (q, subj), v in va.items():
        if q != Q.GLYPH_OWNER:
            continue
        d = (v.get("detail") or {}).get("ladder_discounted_rungs")
        if d:
            owner_discounted_any.append({"subject": subj, "discounted": d,
                                         "verdict": word(v)})

    xb, repb = SX.to_musicxml(B)
    xa, repa = SX.to_musicxml(A)
    out = {
        "provenance": {"base": pb.get("commit"), "arm": pa.get("commit"),
                       "base_dirty": pb.get("dirty"), "arm_dirty": pa.get("dirty")},
        "detector_boxes": {"base": len(bb), "arm": len(ba),
                           "identical": bb == ba},
        "ladder_rows": {"base": len(lb), "arm": len(la),
                        "named_base": len(named_base),
                        "named_arm": len(named_arm),
                        "named_nonempty_arm": ladder_named_nonempty_arm},
        "verdicts_moved_by_quantity": dict(sorted(moved.items())),
        "verdicts_moved_named": dict(named),
        "glyph_owner_moved": owner_moved,
        "glyph_owner_discounted_a_rung": owner_discounted_any,
        "notes": {"base": xb.count("<note"), "arm": xa.count("<note")},
        "musicxml_identical": xb == xa,
        "notes_not_written_identical":
            repb.get("notes_not_written") == repa.get("notes_not_written"),
        "census_unaccounted": {
            "base": (repb.get("status_census") or {}).get("unaccounted"),
            "arm": (repa.get("status_census") or {}).get("unaccounted")},
    }
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("verdicts_moved_named",)}, indent=1,
                     default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
