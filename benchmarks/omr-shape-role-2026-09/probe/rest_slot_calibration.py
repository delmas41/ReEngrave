"""ROADMAP 2.12b-cal — where do rests ACTUALLY hang on these three plates?

    python3 .../probe/rest_slot_calibration.py --all --out-dir <dir>
    python3 .../probe/rest_slot_calibration.py --record <rec> --label <id> \
        --out <json>

2.12b's bands are the convention's NOMINAL lines: a whole rest's centre at
step 5.5, a half rest's at 4.5, a slack of 0.5 half-steps between them. Sean
adjudicated the ten rows the rule said land on the other convention
(`out/print/ADJUDICATION-sean-2026-09-23-rests.json`): **ten of ten are whole
rests**, measured at steps 4.16-4.71. So the band, or the reference point it
is measured from, comes from the convention and not from the plate.

This probe decides nothing. It prints, per record and per class:

  * every rest's measured step at THREE reference points -- the box CENTRE
    (what `rhythm._staff_step` reads today), its TOP edge and its BOTTOM edge
    -- because a whole rest HANGS from its line (top edge ON the line) and a
    half rest SITS on its line (bottom edge ON the line), so a centre is the
    right reading only where the box is exactly one step tall;
  * the box HEIGHT in steps, which is what decides whether those three
    reference points are the same measurement or three different ones;
  * a histogram in 0.1-step bins and p5 / p50 / p95;
  * the same, restricted to the population 2.12b calls PRINT-CONFIRMED --
    the rows whose class **2.12b's NOMINAL bands** do not contradict, plus
    Sean's ten, which are confirmed by a human against the print. ⚠️ Pinned to
    the nominal bands and not to the live ones (`_nominal`), so the
    calibration cannot widen its own evidence.

⚠️ THE MEASUREMENT IS `rhythm._staff_step`, CALLED AND NOT COPIED, exactly as
`_rest_slot` calls it. A second spelling here would be free to answer
differently about the same ink, and the whole question this probe asks is
whether that one function is reading the right point.

⚠️ EVERY RECORD IS READ THROUGH `record_io.load_record` AND NOWHERE ELSE
(CLAUDE.md §4b / roadmap 1.1b).

⚠️ `--all` runs each document in its own SUBPROCESS: the two scan records are
314 MB and 478 MB and holding two in one interpreter is minutes versus swap.
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))

from tools.omr.staged import record_io                      # noqa: E402
from tools.omr.staged.adjudicators import rhythm as RH      # noqa: E402

_HERE = Path(__file__).resolve().parent
_ADJ = (_HERE.parent / "out" / "print"
        / "ADJUDICATION-sean-2026-09-23-rests.json")

#: The two classes whose slot says anything. ⚠️ IMPORTED, NEVER RETYPED --
#: `rhythm._REST_SLOT_BY_CLASS` is the whole domain of the question.
_CLASSES = tuple(RH._REST_SLOT_BY_CLASS)


def _nominal(name: str, step: float):
    """2.12b's verdict for one row, from ONE definition of the retired rule.

    ⚠️⚠️ **THE DERIVATION POPULATION MUST NOT MOVE WHEN THE BANDS DO.** The
    print-confirmed population is *the rows the bands under calibration do not
    contradict*, plus Sean's ten. If it were read off the LIVE bands, then the
    moment the calibrated bands land the population grows by the 124 rows they
    newly decide, and re-running this probe would 'confirm' a wider band with
    the rows that band itself admitted. `verdict_nominal` pins it; `verdict`
    beside it is whatever the tree in hand says.
    """
    sys.path.insert(0, str(_REPO / "benchmarks" / "omr-shape-role-2026-09"))
    import readjudicate_b_e                                       # noqa: E402
    live = RH._rest_slot_verdict
    try:
        readjudicate_b_e._nominal_bands()
        return RH._rest_slot_verdict(name, step)
    finally:
        RH._rest_slot_verdict = live


def _staff_of(key: str):
    bits = key.split("/")
    return "/".join(["staff"] + bits[1:4]) if len(bits) >= 4 else None


def _pct(v, q):
    if not v:
        return None
    s = sorted(v)
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return round(s[i], 3)


def _summary(vals):
    return {
        "n": len(vals),
        "p5": _pct(vals, 0.05), "p25": _pct(vals, 0.25),
        "p50": _pct(vals, 0.50), "p75": _pct(vals, 0.75),
        "p95": _pct(vals, 0.95),
        "min": round(min(vals), 3) if vals else None,
        "max": round(max(vals), 3) if vals else None,
    }


def _hist(vals, lo=-2.0, hi=12.0, width=0.1):
    """0.1-step bins. Rows outside the window are counted at the ends, named."""
    bins: collections.Counter = collections.Counter()
    under = over = 0
    for v in vals:
        if v < lo:
            under += 1
        elif v >= hi:
            over += 1
        else:
            bins[round(lo + width * int((v - lo) / width), 1)] += 1
    return {"bin_width": width, "below_%s" % lo: under, "at_or_above_%s" % hi: over,
            "bins": {("%.1f" % k): bins[k] for k in sorted(bins)}}


def measure(path: Path, label: str) -> dict:
    data = record_io.load_record(path)
    rec = data["record"]
    obs = rec.get("observations") or []

    lines, spacing = {}, {}
    boxes = {}
    rests = []
    for o in obs:
        q = o["quantity"]
        if q == "staff_lines":
            lines[o["subject"]] = o["value"]
        elif q == "staff_spacing":
            spacing[o["subject"]] = o["value"]
        elif q == "glyph_box":
            boxes[o["subject"]] = o
        elif q == "rest":
            rests.append(o)

    adjudicated = {}
    if _ADJ.exists():
        for v in json.loads(_ADJ.read_text())["verdicts"]:
            adjudicated[v["subject"]] = v

    rows = []
    no_geometry = collections.Counter()
    other_classes: collections.Counter = collections.Counter()
    for o in rests:
        name = str(o["value"])
        if name.lower() not in _CLASSES:
            other_classes[name] += 1
            continue
        subj = o["subject"]
        box = boxes.get(subj)
        page = ((box or {}).get("detail") or {}).get("bbox_page_px") \
            or (o.get("detail") or {}).get("bbox_page_px")
        st = _staff_of(subj)
        ly, sp = lines.get(st), spacing.get(st)
        if not page:
            no_geometry["no_page_frame"] += 1
            continue
        if not ly or not sp:
            no_geometry["no_staff_geometry"] += 1
            continue
        # ⚠️ `_staff_step` CALLED, NOT COPIED (see the module docstring). The
        # three reference points are three CALLS with a degenerate box, so a
        # change to that one function moves all three together.
        centre = RH._staff_step(page, ly, sp)
        top = RH._staff_step([page[0], page[1], page[2], page[1]], ly, sp)
        bottom = RH._staff_step([page[0], page[3], page[2], page[3]], ly, sp)
        if centre is None:
            no_geometry["no_staff_geometry"] += 1
            continue
        rows.append({
            "subject": subj, "class": name,
            "centre": round(centre, 3),
            "top": round(top, 3), "bottom": round(bottom, 3),
            "height_steps": round(top - bottom, 3),
            "verdict": RH._rest_slot_verdict(name, centre),
            "verdict_nominal": _nominal(name, centre),
            "sean": (adjudicated.get(subj) or {}).get("sean"),
        })

    out = {
        "label": label, "record": str(path),
        "provenance": {"commit": (data.get("provenance") or {}).get("commit"),
                       "dirty": (data.get("provenance") or {}).get("dirty")},
        "bands_in_force": {"whole": RH.WHOLE_REST_STEP,
                           "half": RH.HALF_REST_STEP,
                           "tolerance_below_whole": RH.REST_SLOT_TOLERANCE_WHOLE,
                           "tolerance_above_half": RH.REST_SLOT_TOLERANCE_HALF},
        "no_geometry": dict(no_geometry),
        "other_rest_classes": dict(other_classes.most_common(12)),
        "verdict_census": dict(collections.Counter(
            str(r["verdict"]) for r in rows)),
        "families": {},
        "rows": rows,
    }

    for cls in ("restWhole", "restHalf"):
        mine = [r for r in rows if r["class"] == cls]
        # PRINT-CONFIRMED: the class the bands do not contradict, plus the
        # rows a human read off the print. ⚠️ `class_not_contradicted` is the
        # weaker word on purpose (`rhythm.SLOT_NOT_CONTRADICTED`): ink
        # displaced away from BOTH slots lands there too, so the confirmed
        # population is reported beside the inside-the-staff restriction and
        # never instead of it.
        conf = [r for r in mine
                if r["verdict_nominal"] == RH.SLOT_NOT_CONTRADICTED
                or r["sean"]]
        inside = [r for r in conf if 0.0 <= r["centre"] <= 8.0]
        fam = {}
        for pop_name, pop in (("all", mine), ("confirmed", conf),
                              ("confirmed_inside_the_staff", inside)):
            fam[pop_name] = {
                "centre": _summary([r["centre"] for r in pop]),
                "top": _summary([r["top"] for r in pop]),
                "bottom": _summary([r["bottom"] for r in pop]),
                "height_steps": _summary([r["height_steps"] for r in pop]),
                "histogram_centre": _hist([r["centre"] for r in pop]),
                "histogram_top": _hist([r["top"] for r in pop]),
                "histogram_bottom": _hist([r["bottom"] for r in pop]),
            }
        out["families"][cls] = fam

    out["sean_ten"] = [r for r in rows if r["sean"]]
    return out


def derive(outdir: Path) -> dict:
    """Pool the three measured files and PRINT the bands they imply.

    ⚠️ THE POOLED POPULATION IS `confirmed ∩ inside the staff`, and the
    restriction is not cosmetic. 2.12b measured that 276 of the 433 rows
    landing on neither convention stand OUTSIDE the staff they are filed on
    (Breitkopf 186 at step −7.3 — the next staff down, reached through the
    cell's 4-space pad), which is an OWNERSHIP question and not a rest
    question. A band derived from rows filed on the wrong staff would be a
    band derived from another staff's ink.

    ⚠️ SEAN'S TEN ARE IN THE POOL AND ARE THE ONLY ROWS IN IT A HUMAN READ
    OFF THE PRINT. Everything else in it is confirmed only in the weak sense
    that the bands under test do not contradict it, which is why the derived
    edge is reported beside their own min and max.
    """
    per, pool, sean = {}, {"restWhole": [], "restHalf": []}, []
    for f in sorted(outdir.glob("rest-slot-cal--*.json")):
        d = json.loads(f.read_text())
        per[d["label"]] = d
        for r in d["rows"]:
            if r["class"] not in pool or not (0.0 <= r["centre"] <= 8.0):
                continue
            if r["sean"]:
                sean.append(r["centre"])
                pool[r["class"]].append(r["centre"])
            elif r["verdict_nominal"] == RH.SLOT_NOT_CONTRADICTED:
                pool[r["class"]].append(r["centre"])

    print("=== per record, per family — confirmed ∩ inside the staff ===")
    print("%-20s %-9s %6s %7s %7s %7s %7s %7s"
          % ("record", "class", "n", "p1", "p5", "p50", "p95", "p99"))
    for label, d in per.items():
        for cls in ("restWhole", "restHalf"):
            v = [r["centre"] for r in d["rows"]
                 if r["class"] == cls and 0.0 <= r["centre"] <= 8.0
                 and (r["verdict_nominal"] == RH.SLOT_NOT_CONTRADICTED
                      or r["sean"])]
            if not v:
                print("%-20s %-9s %6d   — nothing inside the staff"
                      % (label, cls, 0))
                continue
            print("%-20s %-9s %6d %7s %7s %7s %7s %7s"
                  % (label, cls, len(v), _pct(v, .01), _pct(v, .05),
                     _pct(v, .50), _pct(v, .95), _pct(v, .99)))

    print()
    print("=== pooled ===")
    got = {}
    for cls, v in pool.items():
        if not v:
            print("  %-9s EMPTY — no confirmed row inside any staff" % cls)
            got[cls] = None
            continue
        got[cls] = {"n": len(v), "p1": _pct(v, .01), "p5": _pct(v, .05),
                    "p50": _pct(v, .50), "p95": _pct(v, .95),
                    "p99": _pct(v, .99),
                    "min": round(min(v), 3), "max": round(max(v), 3)}
        print("  %-9s %s" % (cls, got[cls]))
    print("  sean ten   n=%d min=%s max=%s" % (len(sean), min(sean) if sean
                                               else None,
                                               max(sean) if sean else None))
    print("  sorted:", sorted(round(s, 3) for s in sean))
    if got.get("restWhole"):
        w = sorted(pool["restWhole"])
        for s in sorted(sean):
            import bisect
            print("    sean %.3f sits at the pooled whole population's "
                  "%.2f-th percentile"
                  % (s, 100.0 * bisect.bisect_left(w, s) / len(w)))
    return {"per_record": {k: v["families"] for k, v in per.items()},
            "pooled": got, "sean": sorted(sean)}


def _resolve(doc) -> Path:
    r = doc["record"]
    if r["root"] == "library":
        from tools.library.score_library import library_root
        return Path(library_root()) / r["path"]
    return _REPO / r["path"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record")
    ap.add_argument("--label", default="?")
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--derive", action="store_true")
    ap.add_argument("--out-dir")
    a = ap.parse_args()

    if a.derive:
        derive(Path(a.out_dir or (_HERE.parent / "out")))
        return 0

    if a.all:
        man = json.loads(
            (_REPO / "benchmarks/acceptance/manifest.json").read_text())
        outdir = Path(a.out_dir or (_HERE.parent / "out"))
        outdir.mkdir(parents=True, exist_ok=True)
        for doc in man["documents"]:
            p = _resolve(doc)
            dest = outdir / ("rest-slot-cal--%s.json" % doc["id"])
            print("→", doc["id"], p, flush=True)
            rc = subprocess.call(
                [sys.executable, str(Path(__file__).resolve()),
                 "--record", str(p), "--label", doc["id"], "--out", str(dest)])
            if rc:
                print("  FAILED rc=%d" % rc)
                return rc
        return 0

    if not a.record:
        ap.error("--record or --all")
    res = measure(Path(a.record), a.label)
    text = json.dumps(res, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(text)
        print("wrote", a.out, "rows", len(res["rows"]))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
