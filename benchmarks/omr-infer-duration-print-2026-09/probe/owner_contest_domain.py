"""§10 — why 161 of the 358 geometrically-suspicious noteheads never entered
`glyph_owner`'s contest.

⚠️ §7b's OWN PROBE WAS NEVER COMMITTED (`git show --stat b19f4258` touches
FINDINGS.md alone), so the population definition here is RECONSTRUCTED from
§7b/§8's prose and its reproduction of 2,347 / 358 / 189 / 161 / 8 is the
control that the reconstruction is the same population. If the four numbers
do not come back, nothing below it is comparable to §7b and the run says so.

The population, exactly as §7b states it: every notehead in the record
carrying a page box; for each, the band distance (in staff spaces) from the
staff whose CELL it was cut from, against the band distance to the nearest
OTHER staff of the same (page, system). "Clearly nearer" = the neighbour
beats the filed staff by more than half a staff space.

⚠️ 358 IS NOT A MISATTRIBUTION COUNT (§7b). It is the population carrying the
geometric signature of the two subjects Sean adjudicated against the print.

The cause classification is read off the record and nothing else:
  * NO_BAND_ROW      -- no `Q.GLYPH_BAND_DISTANCE` row of any state exists for
                        the glyph, so `subjects_for` never made it a subject.
  * ABSTAINED_BANDS  -- band rows exist but every one is an Abstention, so the
                        glyph IS a subject and the adjudicator saw no evidence.
  * VERDICT_PRESENT  -- it was contested (should not appear among the 161).
And for NO_BAND_ROW the SUB-cause is measured against `gather.py`'s own three
contest conditions (same system, same smufl class, IoU >= CONTEST_IOU):
  * NO_TWIN_AT_ALL       -- no glyph of ANY class on the near staff overlaps it
  * TWIN_CLASS_DIFFERS   -- an overlapping glyph on the near staff, different
                            smufl name
  * TWIN_IOU_BELOW       -- same smufl name on the near staff, overlapping,
                            but IoU < CONTEST_IOU
  * OTHER                -- anything the three do not explain (must be 0 or
                            named)

⚠️ CONTROL THAT CAN FAIL, AND IT WAS RUN IN A STATE WHERE IT DOES. Everything
here recomputes `gather._band_distance_spaces` from the record's own
`Q.GLYPH_BOX.detail.bbox_page_px` and `Q.STAFF_LINES`, which is admissible
only if the recomputation reproduces the `Q.GLYPH_BAND_DISTANCE` rows GATHER
actually wrote. It does, bit-exactly, on every one of them (2,772 of 2,772 on
p1-p4; 12,026 of 12,026 on the whole movement). `OWNER_DOMAIN_BREAK_CONTROL=1`
perturbs the staff spacing by 1% and the control goes RED, 2,769 of 2,772
differing -- run that arm before believing the green one.

⚠️ THIS PROBE DECIDES NOTHING AND CROPS NOTHING. It reports a DOMAIN, i.e.
which glyphs were handed to `adjudicate_glyph_owner` at all. Whether any
individual glyph is on the wrong staff is a question for the print, and
`probe/crop_inferred.py` is the instrument for that.

The final arm counts how many of the never-contested the LEGACY predicate
would have handed in -- `transcribe._dedupe_cross_staff_detections` pairs on
`category` equality and `IoU > _CROSS_STAFF_DUPLICATE_IOU = 0.3`, where the
staged gather restates the same predicate as smufl NAME equality and
`CONTEST_IOU = 0.5`. It counts; it changes nothing.

Usage:
    python3 benchmarks/omr-infer-duration-print-2026-09/probe/\\
        owner_contest_domain.py <record.json> [--json out.json]
    OWNER_DOMAIN_BREAK_CONTROL=1 ...   # the RED arm
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

for p in list(Path(__file__).resolve().parents) + list(Path.cwd().resolve().parents) + [Path.cwd().resolve()]:
    if (p / "tools" / "omr" / "staged" / "record_io.py").exists():
        sys.path.insert(0, str(p))
        break

from tools.omr.staged.record_io import load_record          # noqa: E402
from tools.omr.staged.gather import CONTEST_IOU             # noqa: E402

NOTEHEAD_PREFIX = "notehead"
NEARER_BY_SPACES = 0.5


def _head_family(name: str) -> str:
    """`noteheadBlackOnLine` and `noteheadBlackInSpace` are ONE head spelled
    twice -- the suffix is the head's position RELATIVE TO A STAFF, which is
    exactly the thing under dispute in a cross-staff contest."""
    for suf in ("OnLine", "InSpace"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def band_distance(y, line_ys, spacing):
    top, bottom = min(line_ys), max(line_ys)
    if top <= y <= bottom:
        return 0.0
    gap = (top - y) if y < top else (y - bottom)
    return gap / spacing if spacing else gap


def iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    aa = (a[2] - a[0]) * (a[3] - a[1])
    ab = (b[2] - b[0]) * (b[3] - b[1])
    u = aa + ab - inter
    return inter / u if u > 0 else 0.0


def overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", dest="out_json")
    args = ap.parse_args()

    print(f"loading {args.record} ...", flush=True)
    rec = load_record(args.record)["record"]
    print("  observations", len(rec["observations"]),
          " abstentions", len(rec["abstentions"]),
          " verdicts", len(rec["verdicts"]), flush=True)

    # ── staff geometry ──────────────────────────────────────────────────────
    staff_lines = {}
    for o in rec["observations"]:
        if o["quantity"] == "staff_lines":
            ys = [float(y) for y in o["value"]]
            if len(ys) >= 2:
                staff_lines[o["subject"]] = ys
    # spacing from the staff's own line span (§7b: 63-65 px on every staff)
    # `gather._spacing` is the MEAN line gap, i.e. span / (n - 1).
    # ⚠️ `OWNER_DOMAIN_BREAK_CONTROL=1` perturbs it by 1% so the control below
    # can be seen going RED before it is trusted going green (CLAUDE.md rule 7).
    break_it = os.environ.get("OWNER_DOMAIN_BREAK_CONTROL") == "1"
    staff_geom = {}
    for key, ys in staff_lines.items():
        span = max(ys) - min(ys)
        sp = span / (len(ys) - 1)
        if sp > 0:
            staff_geom[key] = (ys, sp * (1.01 if break_it else 1.0))

    by_system = defaultdict(list)
    for key in staff_geom:
        page, system, staff = key.split("/")[1:4]
        by_system[(page, system)].append(key)

    # ── every glyph with a page box ─────────────────────────────────────────
    glyphs = {}          # subject -> (name, page_box)
    categories = {}      # subject -> the detector's CATEGORY (legacy's test)
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if pb is None:
            continue
        glyphs[o["subject"]] = (str(o["value"][0]), [float(v) for v in pb])
        categories[o["subject"]] = str((o.get("detail") or {}).get("category"))

    # band-distance rows (observations AND abstentions) per glyph
    band_obs = defaultdict(list)
    band_abs = defaultdict(list)
    for o in rec["observations"]:
        if o["quantity"] == "glyph_band_distance":
            band_obs[o["subject"]].append(o)
    for a in rec["abstentions"]:
        if a["quantity"] == "glyph_band_distance":
            band_abs[a["subject"]].append(a)

    cell_box = {}
    for o in rec["observations"]:
        if o["quantity"] == "cell_box":
            cell_box[o["subject"]] = [float(v) for v in o["value"]]

    owner_verdict = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "glyph_owner":
            owner_verdict[v["subject"]] = v

    glyphs_by_system = defaultdict(list)
    for sub, (name, pb) in glyphs.items():
        parts = sub.split("/")
        glyphs_by_system[(parts[1], parts[2])].append(sub)

    # ── CONTROL, AND IT CAN FAIL ────────────────────────────────────────────
    #
    # Everything below recomputes `_band_distance_spaces` from the record's own
    # `Q.GLYPH_BOX.detail.bbox_page_px` and `Q.STAFF_LINES`. That is admissible
    # only if the recomputation reproduces the rows GATHER actually wrote. Run
    # against every recorded `Q.GLYPH_BAND_DISTANCE` observation: a mismatch
    # over 1e-6 means the arithmetic here is not the pipeline's and nothing
    # after this point is comparable.
    checked = mismatched = unresolvable = 0
    worst = 0.0
    for sub, obs in band_obs.items():
        pbx = glyphs.get(sub)
        if pbx is None:
            unresolvable += len(obs)
            continue
        y = (pbx[1][1] + pbx[1][3]) / 2.0
        for o in obs:
            cand = (o.get("detail") or {}).get("candidate")
            g = staff_geom.get(cand)
            if g is None:
                unresolvable += 1
                continue
            checked += 1
            d = abs(band_distance(y, g[0], g[1]) - float(o["value"]))
            worst = max(worst, d)
            if d > 1e-6:
                mismatched += 1
    print()
    print(f"CONTROL  recomputed band distance vs the record's own rows: "
          f"{checked - mismatched} of {checked} agree, {mismatched} differ, "
          f"worst |delta| {worst:.2e}, {unresolvable} unresolvable")
    if checked == 0 or mismatched:
        print("  ⚠️ THE ARITHMETIC HERE IS NOT THE PIPELINE'S -- nothing below is comparable")

    # ── the sweep ───────────────────────────────────────────────────────────
    noteheads = 0
    suspicious = []
    for sub, (name, pb) in glyphs.items():
        if not name.lower().startswith(NOTEHEAD_PREFIX):
            continue
        parts = sub.split("/")
        page, system, staff = parts[1], parts[2], parts[3]
        own_key = f"staff/{page}/{system}/{staff}"
        if own_key not in staff_geom:
            continue
        noteheads += 1
        y = (pb[1] + pb[3]) / 2.0
        own_lines, own_sp = staff_geom[own_key]
        own_d = band_distance(y, own_lines, own_sp)
        best_other, best_d = None, None
        for cand in by_system[(page, system)]:
            if cand == own_key:
                continue
            lines, sp = staff_geom[cand]
            d = band_distance(y, lines, sp)
            if best_d is None or d < best_d:
                best_other, best_d = cand, d
        if best_other is None:
            continue
        if best_d + NEARER_BY_SPACES < own_d:
            suspicious.append((sub, own_key, own_d, best_other, best_d))

    print()
    print(f"noteheads with a page box on a staff with geometry : {noteheads}")
    print(f"a neighbouring staff clearly nearer (> 0.5 space)  : {len(suspicious)}")

    contested_near = contested_else = uncontested = 0
    the_eight = []
    never = []
    for sub, own_key, own_d, near_key, near_d in suspicious:
        v = owner_verdict.get(sub)
        if v is None:
            uncontested += 1
            never.append((sub, own_key, own_d, near_key, near_d))
        elif v.get("value") == near_key:
            contested_near += 1
        else:
            contested_else += 1
            the_eight.append((sub, own_key, own_d, near_key, near_d, v))

    print(f"  contested -> resolved to the NEAR staff          : {contested_near}")
    print(f"  never contested at all (no glyph_owner verdict)  : {uncontested}")
    print(f"  contested -> resolved elsewhere                  : {contested_else}")

    expect = {"noteheads": 2347, "suspicious": 358, "near": 189,
              "never": 161, "else": 8}
    got = {"noteheads": noteheads, "suspicious": len(suspicious),
           "near": contested_near, "never": uncontested,
           "else": contested_else}
    print()
    print("CONTROL vs FINDINGS §7b/§8:",
          "REPRODUCED" if got == expect else f"DIFFERS  expected {expect}")

    # ── cause of the never-contested ────────────────────────────────────────
    causes = Counter()
    subcauses = Counter()
    abstain_reasons = Counter()
    class_pairs = Counter()
    class_split = Counter()
    no_twin_reach = Counter()
    iou_bins = Counter()
    rows = []
    for sub, own_key, own_d, near_key, near_d in never:
        obs = band_obs.get(sub, [])
        abst = band_abs.get(sub, [])
        extra = {}
        if obs:
            cause = "BAND_ROW_PRESENT_BUT_NO_VERDICT"
            sc = ""
        elif abst:
            cause = "ABSTAINED_BANDS"
            for a in abst:
                abstain_reasons[a.get("reason")] += 1
            sc = ""
        else:
            cause = "NO_BAND_ROW"
            # why did no contest form? Measured against gather.py's three
            # conditions, and ONLY against the NEAR staff -- the contest that
            # would have mattered. `near_iou` is the best IoU with a glyph of
            # the SAME smufl name filed on the near staff.
            name, pb = glyphs[sub]
            parts = sub.split("/")
            page, system = parts[1], parts[2]
            near_staff_ord = near_key.split("/")[3]
            best_iou_same = 0.0
            overlapped_classes = []
            for other in glyphs_by_system[(page, system)]:
                if other == sub:
                    continue
                op = other.split("/")
                if op[3] != near_staff_ord:
                    continue                      # only the NEAR staff's cells
                oname, opb = glyphs[other]
                if not overlaps(pb, opb):
                    continue
                overlapped_classes.append((oname, round(iou(pb, opb), 3)))
                if oname == name:
                    best_iou_same = max(best_iou_same, iou(pb, opb))
            if not overlapped_classes:
                sc = "NO_TWIN_AT_ALL"
                # does the near staff's cell crop even reach this ink?
                inside = [ck for ck, cb in cell_box.items()
                          if ck.split("/")[1:4] == [page, system, near_staff_ord]
                          and cb[0] <= (pb[0]+pb[2])/2 <= cb[2]
                          and cb[1] <= (pb[1]+pb[3])/2 <= cb[3]]
                no_twin_reach[bool(inside)] += 1
            elif best_iou_same <= 0.0:
                sc = "TWIN_CLASS_DIFFERS"
                class_pairs[(name, tuple(sorted({c for c, _ in overlapped_classes})))] += 1
                base = _head_family(name)
                theirs = {c for c, _ in overlapped_classes}
                if any(_head_family(c) == base and c != name for c in theirs):
                    class_split["SAME HEAD, OnLine/InSpace differ"] += 1
                elif any(c.lower().startswith(NOTEHEAD_PREFIX) for c in theirs):
                    class_split["both noteheads, different head type"] += 1
                else:
                    class_split["no notehead on the near staff there"] += 1
            elif best_iou_same < CONTEST_IOU:
                sc = "TWIN_IOU_BELOW_0.5"
                iou_bins[round(best_iou_same * 10) / 10] += 1
            else:
                sc = "OTHER_unexplained"
            subcauses[sc] += 1
            extra = {"near_best_iou_same_class": round(best_iou_same, 3),
                     "overlapping_on_near_staff": overlapped_classes[:6],
                     "class": name}
        causes[cause] += 1
        rows.append({"subject": sub, "filed_on": own_key,
                     "own_spaces": round(own_d, 2), "near": near_key,
                     "near_spaces": round(near_d, 2),
                     "cause": cause, "subcause": sc, **extra})

    print()
    print("CAUSE of the never-contested")
    for c, n in causes.most_common():
        print(f"  {c:34s} {n:4d}")
    print("  sub-cause of NO_BAND_ROW (gather.py's three contest conditions)")
    for c, n in subcauses.most_common():
        print(f"    {c:32s} {n:4d}")
    if class_pairs:
        print("  TWIN_CLASS_DIFFERS -- this glyph's class vs what the near staff has there")
        for (mine, theirs), n in class_pairs.most_common(12):
            print(f"    {mine:22s} vs {','.join(theirs):34s} {n:4d}")
    if class_split:
        print("  TWIN_CLASS_DIFFERS, split")
        for k, n in class_split.most_common():
            print(f"    {k:44s} {n:4d}")
    if no_twin_reach:
        print("  NO_TWIN_AT_ALL: is the ink inside a cell of the near staff?")
        for k, n in no_twin_reach.most_common():
            print(f"    near staff's cell covers it = {k}   {n:4d}")
    if iou_bins:
        print("  TWIN_IOU_BELOW_0.5 -- best same-class IoU with the near staff")
        for b in sorted(iou_bins):
            print(f"    IoU ~{b:.1f}  {iou_bins[b]:4d}")
    if abstain_reasons:
        print("  abstention reasons")
        for c, n in abstain_reasons.most_common():
            print(f"    {c:32s} {n:4d}")
    print(f"  sum {sum(causes.values())}")

    # ── THE LEGACY PREDICATE, as an arm ─────────────────────────────────────
    #
    # `transcribe._dedupe_cross_staff_detections` pairs on
    #   di["category"] == dj["category"]  AND  IoU > _CROSS_STAFF_DUPLICATE_IOU
    # with the threshold 0.3, swept over three orchestral works and documented
    # as the LOWEST value costing no correctly-matched note on any of them
    # (`benchmarks/omr-orchestral-e2e/DEDUPE_THRESHOLD.md`). The staged gather
    # restates the same predicate as smufl NAME and 0.5. This arm counts what
    # the legacy predicate would have handed the contest -- it decides nothing.
    LEGACY_IOU = 0.3
    would_enter = Counter()
    by_sub_legacy = {}
    for sub, own_key, own_d, near_key, near_d in never:
        name, pb = glyphs[sub]
        cat = categories.get(sub)
        parts = sub.split("/")
        page, system = parts[1], parts[2]
        best_cat = best_name = 0.0
        for other in glyphs_by_system[(page, system)]:
            if other == sub or other.split("/")[3] == parts[3]:
                continue
            oname, opb = glyphs[other]
            v = iou(pb, opb)
            if v <= 0:
                continue
            if categories.get(other) == cat:
                best_cat = max(best_cat, v)
            if oname == name:
                best_name = max(best_name, v)
        by_sub_legacy[sub] = round(best_cat, 3)
        would_enter["legacy predicate (category, IoU > 0.3)"] += best_cat > LEGACY_IOU
        would_enter["category only, IoU still 0.5"] += best_cat >= CONTEST_IOU
        would_enter["name only, IoU > 0.3"] += best_name > LEGACY_IOU
    print()
    print("HOW MANY OF THE NEVER-CONTESTED THE LEGACY PREDICATE WOULD HAND IN")
    for k, n in would_enter.items():
        print(f"    {k:42s} {n:4d} of {len(never)}")
    residual = Counter()
    for r in rows:
        v = by_sub_legacy.get(r["subject"], 0.0)
        r["legacy_best_same_category_iou"] = v
        if v > LEGACY_IOU:
            residual["ENTERS under the legacy predicate"] += 1
        elif v <= 0.0:
            residual["no same-CATEGORY ink on another staff at all"] += 1
        else:
            residual["same category, IoU <= 0.3 (below the swept floor)"] += 1
    print("  the residual, if the legacy predicate were restored")
    for k, n in residual.most_common():
        print(f"    {k:52s} {n:4d}")

    # ── the 8 resolved elsewhere ────────────────────────────────────────────
    print()
    print("THE 8 CONTESTED -> RESOLVED ELSEWHERE")
    eight = []
    for sub, own_key, own_d, near_key, near_d, v in sorted(the_eight):
        det = v.get("detail") or {}
        row = {"subject": sub, "filed_on": own_key,
               "own_spaces": round(own_d, 2),
               "nearest": near_key, "near_spaces": round(near_d, 2),
               "outcome": v.get("outcome"), "value": v.get("value"),
               "reason": v.get("reason"),
               "margin": v.get("margin"),
               "would_win_on_distance": det.get("would_win_on_distance"),
               "scores": det.get("scores"),
               "n_basis": len(v.get("basis") or []),
               "candidates": [c.get("value") for c in (v.get("candidates") or [])]}
        eight.append(row)
        print(f"  {sub}  filed {own_key} ({own_d:.2f} sp)  nearest {near_key} "
              f"({near_d:.2f} sp)")
        print(f"      outcome={row['outcome']} value={row['value']} "
              f"reason={row['reason']} margin={row['margin']} "
              f"dist_winner={row['would_win_on_distance']} "
              f"scores={row['scores']} basis={row['n_basis']} "
              f"cands={row['candidates']}")

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(
            {"record": args.record, "counts": got, "expected": expect,
             "causes": dict(causes), "subcauses": dict(subcauses),
             "abstain_reasons": dict(abstain_reasons),
             "class_pairs": {f"{k[0]} vs {','.join(k[1])}": v
                             for k, v in class_pairs.items()},
             "iou_bins": {str(k): v for k, v in iou_bins.items()},
             "class_split": dict(class_split),
             "no_twin_reach": {str(k): v for k, v in no_twin_reach.items()},
             "never_contested": rows, "resolved_elsewhere": eight},
            indent=1))
        print(f"\nwrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
