"""The slot-table fit on the DETECTOR's key markers, scored against the print.

`docs/NEXT-2026-09-21-keysig-reading-lever.md` asked for this. ⚠️⚠️ ITS PREMISE
IS FALSE AND THAT REFRAMES THE JOB: it says `fit_key_signature` "has never been
given the detector's markers as its ink source". `transcribe.py:856` has given
it exactly that since `7c6b6481` (2026-08-28), through `_staff_positions_for`
and a `_DETECTOR_FIT_CONFIG` written for the purpose. So this is not a new
reader -- it is a PORT of a shipped LEGACY one onto the staged path, the sixth
instance of the symbol sweep's §2a family.

⚠️ THE UNIT IS THE WHOLE DIFFICULTY, AND ONE HALF OF IT IS NOT ON THE RECORD.
`fit_key_signature` wants steps below the TOP STAFF LINE. `_cell_grid` returns
`(top_y, half_step)`; `Q.CELL_STAFF_SPACE` files `half_step` and DROPS `top_y`,
so 0 of 40,878 rows carry the cell's top line in the cell frame -- exactly the
consumer `_cell_grid`'s own docstring says had "nothing to ask with".

It is RECOVERABLE without a re-gather, because for any notehead
`pos_float = (y_center - top_y) / half_step` (gather.py:497), so

    top_y = (y + h // 2) - pos_float * half_step

POSITIVE CONTROL, and it can fail: every notehead in a cell must back-solve to
the SAME top_y. Measured 598/598 exact (<1e-9); the float spelling
`y + h/2.0` scores 154/598, so the control distinguishes. A cell with no
notehead has NO unit and ABSTAINS -- it is never given a nominal spacing.

⚠️ NO CODE UNDER `tools/`. This scores what the reader WOULD say; it ships
nothing and changes no default.

    python3 marker_fit_arm.py <record.json> --truth <truth.json>   # scored
    python3 marker_fit_arm.py <record.json>                        # reach only
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.key_signature_geometry import (      # noqa: E402
    KeySignatureFitConfig, fit_key_signature,
)

#: ⚠️ READ FROM `transcribe.py`'s SOURCE, NOT RESTATED AND NOT IMPORTED.
#: Restating it lets the two drift; importing `transcribe` drags cv2, fitz and
#: ultralytics into a probe that needs none of them. The AST read is the
#: anti-drift form this repo already uses for gather-site shapes.
def _detector_fit_config() -> KeySignatureFitConfig:
    src = (ROOT / "tools" / "omr" / "transcribe.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", None) == "_DETECTOR_FIT_CONFIG"
                        for t in node.targets)
                and isinstance(node.value, ast.Call)):
            kw = {k.arg: ast.literal_eval(k.value) for k in node.value.keywords}
            return KeySignatureFitConfig(**kw)
    raise SystemExit("transcribe._DETECTOR_FIT_CONFIG not found -- it moved")


FLATS  = "BEADGCF"
SHARPS = "FCGDAEB"


def altered_letters(fifths: int) -> set:
    if fifths < 0:
        return set(FLATS[:abs(fifths)])
    if fifths > 0:
        return set(SHARPS[:fifths])
    return set()


def load(path: Path) -> dict:
    rec = json.loads(Path(path).read_text())
    R = rec["record"]
    out = {"half": {}, "box": {}, "pos": {}, "mark": collections.defaultdict(list),
           "clef": {}, "pitch": collections.defaultdict(list), "abstain": []}
    for r in R["observations"]:
        q, s, d = r.get("quantity"), r.get("subject"), (r.get("detail") or {})
        if   q == "cell_staff_space": out["half"][s] = d.get("half_step")
        elif q == "glyph_box":        out["box"][s] = r.get("value")
        elif q == "notehead_staff_position": out["pos"][s] = r.get("value")
        elif q == "keysig_marker":
            out["mark"][s].append((d.get("x"), d.get("y_center"), str(r.get("value"))))
    for v in R["verdicts"]:
        q, s = v.get("quantity"), v.get("subject")
        if q == "clef" and v.get("outcome") == "decided":
            out["clef"][s] = v.get("value")
        elif q == "pitch" and v.get("outcome") == "decided":
            out["pitch"]["/".join(s.split("/")[:4]).replace("glyph", "staff", 1)].append(v.get("value"))
        elif q == "key_signature" and v.get("outcome") != "decided":
            out["abstain"].append((s, v.get("reason")))
    return out


def back_solve_top_y(D: dict) -> tuple:
    """(top_y per cell, n_controlled, n_disagreeing) -- the control is inline."""
    agree = collections.defaultdict(list)
    for g, pf in D["pos"].items():
        c = "cell/" + "/".join(g.split("/")[1:5])
        b, h = D["box"].get(g), D["half"].get(c)
        if not b or h is None or pf is None:
            continue
        try:
            _, x, y, w, ht = b
        except Exception:                                      # noqa: BLE001
            continue
        agree[c].append((float(y) + float(ht) // 2) - float(pf) * float(h))
    top, bad, ctl = {}, 0, 0
    for c, v in agree.items():
        if len(v) >= 2:
            ctl += 1
            if max(v) - min(v) >= 1e-6:
                bad += 1
                continue
        top[c] = v[0]
    return top, ctl, bad


def truth_for(truth: dict, page: int, system: int, staff: int):
    for row in truth["systems"]:
        if row["page"] == page and row["system"] == system:
            lineup = row["lineup"]
            if staff >= len(lineup):
                return None, f"staff {staff} past lineup of {len(lineup)}"
            name = lineup[staff]
            ent = truth["instruments"].get(name)
            return (ent["fifths"] if ent else None), name
    return None, "no truth system"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--truth")
    ap.add_argument("--json")
    a = ap.parse_args()

    cfg = _detector_fit_config()
    D = load(Path(a.record))
    top, ctl, bad = back_solve_top_y(D)
    truth = json.loads(Path(a.truth).read_text()) if a.truth else None

    print(f"RECORD {Path(a.record).name}")
    print(f"  fit config (from transcribe.py source): {cfg}")
    print(f"  top_y back-solve: {len(top)} cells; control {ctl} with >=2 "
          f"noteheads, {bad} DISAGREEING")
    if bad:
        print("  ⚠️ a disagreeing cell is EXCLUDED, never averaged")

    rows, reach = [], collections.Counter()
    for s, reason in sorted(D["abstain"]):
        mk = D["mark"].get(s, [])
        reach["abstaining"] += 1
        if not mk:
            reach["no markers"] += 1
            continue
        reach["carries markers"] += 1
        if reason == "needs_clef" or s not in D["clef"]:
            reach["OUT: no clef"] += 1
            continue
        p = s.split("/")
        c0 = f"cell/{p[1]}/{p[2]}/{p[3]}/0"
        h, ty = D["half"].get(c0), top.get(c0)
        if h is None or ty is None:
            reach["OUT: no unit (cell 0 has no notehead)"] += 1
            continue
        reach["MEASURABLE"] += 1

        sharps = [m for m in mk if m[2].lower().startswith("keysharp")]
        flats  = [m for m in mk if m[2].lower().startswith("keyflat")]
        marks, acc = (sharps, "#") if len(sharps) >= len(flats) else (flats, "b")
        if not marks:
            reach["fit: no sharp/flat markers"] += 1
            continue
        obsv = [ (float(m[1]) - ty) / float(h)
                 for m in sorted(marks, key=lambda m: m[0]) ]
        clef = D["clef"][s]
        read = fit_key_signature(obsv, clef, acc, cfg)
        got = read.fifths if read is not None else None
        reach["fit: ABSTAINS" if got is None else "fit: answers"] += 1

        t, name = (truth_for(truth, int(p[1]), int(p[2]), int(p[3]))
                   if truth else (None, None))
        # ⚠️ TWO DIRECTIONS, AND REPORTING ONLY ONE WOULD FLATTER THE FIT.
        # A fitted key that is a SUBSET of the truth (-1 under a true -3) moves
        # notes CORRECTLY and leaves the rest under-altered, so "notes moved"
        # is not a cost there. The cost is `notes_missed` -- notes the PRINT
        # alters that the fitted key leaves natural -- plus `notes_overmoved`,
        # notes the fit alters that the print does not.
        got_set = altered_letters(got) if got is not None else set()
        true_set = altered_letters(t) if t is not None else set()
        pitches = D["pitch"].get(s, [])
        moved = sum(1 for v in pitches if v and v[0] in got_set)
        missed = sum(1 for v in pitches if v and v[0] in (true_set - got_set))
        over = sum(1 for v in pitches if v and v[0] in (got_set - true_set))
        rows.append(dict(staff=s, reason=reason, instrument=name, clef=clef,
                         n_markers=len(marks), accidental=acc,
                         observed=[round(o, 3) for o in obsv],
                         fit=got, truth=t, notes_on_staff=len(pitches),
                         notes_moved=moved, notes_missed=missed,
                         notes_overmoved=over))

    print("\nREACH")
    for k in ("abstaining", "no markers", "carries markers", "OUT: no clef",
              "OUT: no unit (cell 0 has no notehead)", "MEASURABLE",
              "fit: answers", "fit: ABSTAINS"):
        if reach[k]:
            print(f"   {k:42s} {reach[k]}")
    if not reach["MEASURABLE"]:
        print("\n⚠️ DEAD: nothing measurable. Not a result.")
        return 2

    print("\nPER STAFF")
    hdr = f"   {'staff':14s} {'instrument':22s} {'clef':7s} {'n':>2s} {'observed':26s} {'fit':>4s} {'truth':>5s} {'notes':>6s} {'moved':>6s} {'missed':>7s} {'over':>5s}"
    print(hdr); print("   " + "-" * (len(hdr) - 3))
    for r in rows:
        print(f"   {r['staff']:14s} {str(r['instrument']):22s} {r['clef']:7s} "
              f"{r['n_markers']:2d} {str(r['observed']):26s} "
              f"{str(r['fit']):>4s} {str(r['truth']):>5s} "
              f"{r['notes_on_staff']:6d} {r['notes_moved']:6d} "
              f"{(str(r['notes_missed']) if r['truth'] is not None else '--'):>7s} "
              f"{(str(r['notes_overmoved']) if r['truth'] is not None else '--'):>5s}")

    if truth:
        scored = [r for r in rows if r["truth"] is not None]
        right  = sum(1 for r in scored if r["fit"] == r["truth"])
        absten = sum(1 for r in scored if r["fit"] is None)
        wrong  = sum(1 for r in scored if r["fit"] is not None and r["fit"] != r["truth"])
        # FILE: an abstention exports no <key>, which READS AS 0 accidentals.
        file_now = sum(1 for r in scored if r["truth"] == 0)
        file_new = sum(1 for r in scored if (r["fit"] if r["fit"] is not None else 0) == r["truth"])
        null_hit = sum(1 for r in scored if r["truth"] == -3)
        over_all   = sum(r["notes_overmoved"] for r in scored)
        missed_fit = sum(r["notes_missed"] for r in scored)
        # The NULL writes -3 everywhere, so it over-alters every staff whose
        # truth is not a superset of 3 flats. Same currency, both arms.
        missed_null = sum(
            sum(1 for v in D["pitch"].get(r["staff"], [])
                if v and v[0] in (altered_letters(r["truth"]) - altered_letters(-3)))
            for r in scored)
        over_null = sum(
            sum(1 for v in D["pitch"].get(r["staff"], [])
                if v and v[0] in (altered_letters(-3) - altered_letters(r["truth"])))
            for r in scored)
        print(f"\nSCORED on {len(scored)} staves")
        print(f"   READING   right {right}   wrong {wrong}   abstained {absten}")
        print(f"   FILE      now {file_now}/{len(scored)}   with the fit {file_new}/{len(scored)}")
        print(f"   NULL      '3 flats on every one' would score {null_hit}/{len(scored)}")
        print(f"   BLAST     a key now drives <alter> via respell_accidental, so a")
        print(f"             reading changes what the staff SOUNDS like:")
        print(f"               the fit  : {over_all:4d} notes altered the print does NOT,"
              f" {missed_fit:4d} left natural that the print alters")
        print(f"               the NULL : {over_null:4d} notes altered the print does NOT,"
              f" {missed_null:4d} left natural that the print alters")
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"config": str(cfg), "reach": dict(reach), "rows": rows}, indent=2))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
