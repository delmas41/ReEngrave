"""ROADMAP 2.12b + 2.12e — the two populations, BEFORE either line is built.

⚠️ REACH BEFORE ACCURACY (CLAUDE.md §6b). This prints the population each
line would act on and **exits non-zero declaring itself DEAD at zero**, so a
later arm that moves nothing because it is inert and one that moves nothing
because the page holds nothing to move are not the same number.

It decides nothing and changes no code. Every number is a count over rows
already on disk.

⚠️ THE DEFINITIONS ARE `probe/role_disagreement.py`'s, REUSED AND NOT
REDEFINED. `_REST_SLACK`, `f_rest_whole_half`'s two-bucket split
(`lands_on_the_other_convention` vs `lands_on_neither_convention`) and
`f_flag_stem`'s cell join are imported from that module, so the numbers here
and the audit's table are the same measurement. What this adds is the three
questions the audit did not ask, because they are about what the ADJUDICATOR
can see rather than about what the record says:

  * 2.12b — is `Q.REST_POSITION` on the record at all? (`OMR_FAMILY_POSITIONS`
    is DEFAULT OFF, so the family-position row the reach ledger names as
    `adjudicate_duration`'s first consumer may simply not exist), and can
    `rhythm._staff_step` be computed for each rest from `Q.GLYPH_BOX`'s page
    box plus `Q.STAFF_LINES` / `Q.STAFF_SPACING` — which is what the
    adjudicator will actually read.
  * 2.12b — the same slot arithmetic in the adjudicator's OWN frame
    (`_staff_step`: bottom line 0, up positive, whole 5.5 / half 4.5) rather
    than the probe's (top line 0, down positive, whole 2.5 / half 3.5). The
    two frames are a reflection of each other and must give the same verdict
    on every rest; a row where they differ is a fault in one of them and is
    printed.
  * 2.12e — the UNJOINABLE flags, which the audit named as the finding
    underneath the disagreement: a flag whose notehead has no DECIDED
    `stem_direction`, split by why.

Run:

    python3 benchmarks/omr-shape-role-2026-09/probe/rest_slot_and_flag_join.py --all
    python3 .../rest_slot_and_flag_join.py --record <path> --label <id> --out <json>

⚠️ ONE SUBPROCESS PER RECORD under `--all`, for the reason
`role_disagreement.py` gives: the two scan records are 314 MB and 478 MB on
disk and holding two of them expanded in one interpreter is the difference
between minutes and swap.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
sys.path.insert(0, str(_REPO))

from tools.omr.staged import record_io  # noqa: E402
from tools.omr.staged.adjudicators import rhythm as RH  # noqa: E402

sys.path.insert(0, str(_HERE.parent))
import role_disagreement as RD  # noqa: E402


#: ⚠️ IMPORTED, NEVER RESTATED. The audit's slack and the audit's two
#: conventions; this module knows no constant of its own.
SLACK = RD._REST_SLACK

#: The adjudicator's frame, from the module the adjudicator lives in.
WHOLE_STEP = RH.WHOLE_REST_STEP          # 5.5, bottom line 0, up positive
#: ⚠️ DERIVED, not typed: the two conventions are one line apart and a line is
#: two half-steps, and the half rest sits on the line ABOVE the one the whole
#: rest hangs under, which in a bottom-up frame is one step LOWER.
HALF_STEP = WHOLE_STEP - 1.0             # 4.5


def _page_box(row) -> object:
    return (row.get("detail") or {}).get("bbox_page_px")


def rest_population(r: "RD.Rec") -> dict:
    """Every `restWhole` / `restHalf` row, measured the way `_rest_ruling`
    will measure it, and cross-checked against the audit's own frame."""
    # staff subject -> (line ys, spacing)
    spacing = {}
    for o in r.by_q.get("staff_spacing", ()):
        try:
            spacing[o["subject"]] = float(o["value"])
        except (TypeError, ValueError):
            pass

    have_rest_position = len(r.by_q.get("rest_position", ()))

    out = collections.Counter()
    frames_disagree = []
    steps = collections.defaultdict(list)
    #: ⚠️ THE QUESTION THE CROPS RAISED. A rest whose centre stands OUTSIDE
    #: the staff it is filed on has not told us anything about WHICH REST IT
    #: IS -- it has told us it may be on the wrong STAFF. The measure cell is
    #: padded 4 staff spaces (6 where the neighbour is far) and on a
    #: conductor's page that reaches the next staff's ink (CLAUDE.md §10), so
    #: this is `glyph_owner`'s contest showing through a rest-reading probe.
    #: Split so the two findings cannot be quoted as one.
    by_bucket = collections.defaultdict(collections.Counter)
    bucket_steps = collections.defaultdict(list)
    for o in r.by_q.get("rest", ()):
        name = str(o["value"])
        if name not in ("restWhole", "restHalf"):
            out["other_rest_class"] += 1
            continue
        out["population"] += 1
        subj = o["subject"]
        staff = RD._staff_of(subj) or ""
        box = r.box.get(subj)
        pbox = _page_box(box) if box else None
        lines = r.staff_lines.get(staff)
        sp = spacing.get(staff)
        if not pbox:
            out["no_page_box"] += 1
            continue
        if not lines or not sp:
            out["no_staff_geometry"] += 1
            continue
        step = RH._staff_step(pbox, lines, sp)
        if step is None:
            out["no_staff_geometry"] += 1
            continue
        out["measurable"] += 1
        steps[name].append(step)

        want = WHOLE_STEP if name == "restWhole" else HALF_STEP
        other = HALF_STEP if name == "restWhole" else WHOLE_STEP
        # ⚠️ THE AUDIT'S PREDICATE, CHARACTER FOR CHARACTER.
        if abs(step - other) + SLACK < abs(step - want):
            if abs(step - other) <= SLACK:
                out["lands_on_the_other_convention"] += 1
                verdict = "other"
            else:
                out["lands_on_neither_convention"] += 1
                verdict = "neither"
        else:
            out["class_not_contradicted"] += 1
            verdict = "agrees"

        # ⚠️ THE STAFF IS 8 HALF-STEPS TALL IN THIS FRAME: bottom line 0, top
        # line 8. Anything under 0 stands BELOW the staff it is filed on and
        # anything over 8 stands ABOVE it.
        if step < 0.0:
            by_bucket[verdict]["below_its_own_staff"] += 1
        elif step > 8.0:
            by_bucket[verdict]["above_its_own_staff"] += 1
        else:
            by_bucket[verdict]["inside_its_own_staff"] += 1
        bucket_steps[verdict].append(step)

        # the audit's own frame, on the audit's own input, for the same row
        y = (o.get("detail") or {}).get("y_center_page")
        alt = r.staff_step(subj, y)
        if alt is not None:
            aw = RD._WHOLE_REST_CENTRE if name == "restWhole" else RD._HALF_REST_CENTRE
            ao = RD._HALF_REST_CENTRE if name == "restWhole" else RD._WHOLE_REST_CENTRE
            if abs(alt - ao) + SLACK < abs(alt - aw):
                av = "other" if abs(alt - ao) <= SLACK else "neither"
            else:
                av = "agrees"
            out["cross_checked"] += 1
            if av != verdict:
                out["frames_disagree"] += 1
                if len(frames_disagree) < 12:
                    frames_disagree.append(
                        {"subject": subj, "class": name,
                         "adjudicator_step": round(step, 3), "says": verdict,
                         "audit_step": round(alt, 3), "audit_says": av})
    med = {}
    for k, v in steps.items():
        v.sort()
        med[k] = {"n": len(v), "median_step": round(v[len(v) // 2], 3),
                  "p10": round(v[len(v) // 10], 3),
                  "p90": round(v[(len(v) * 9) // 10], 3)}
    bstat = {}
    for k, v in bucket_steps.items():
        v = sorted(v)
        bstat[k] = {"n": len(v), "median_step": round(v[len(v) // 2], 3),
                    "p10": round(v[len(v) // 10], 3),
                    "p90": round(v[(len(v) * 9) // 10], 3)}
    return {
        "counts": dict(out),
        "where_the_ink_stands_by_bucket": {k: dict(v)
                                           for k, v in by_bucket.items()},
        "step_distribution_by_bucket": bstat,
        "rest_position_rows_on_the_record": have_rest_position,
        "measured_steps_adjudicator_frame": med,
        "convention": {"restWhole": WHOLE_STEP, "restHalf": HALF_STEP,
                       "slack_half_steps": SLACK,
                       "frame": "bottom line 0, one step per half space, "
                                "up positive (rhythm._staff_step)"},
        "frames_disagree_examples": frames_disagree,
    }


def flag_population(r: "RD.Rec") -> dict:
    """2.12e — how many flags can reach a DECIDED `stem_direction` at all.

    ⚠️ THE ADJUDICATOR'S JOIN, NOT THE AUDIT'S. `f_flag_stem` counts CELLS
    holding exactly one flag and exactly one decided direction, because a
    probe cannot re-run `_attached_flags`. The adjudicator joins a flag to a
    head through the STEM that touches both, so the population it can serve is
    *flags in a cell that holds at least one decided `stem_direction`* — wider
    than the audit's and still an upper bound on what the stem can answer.
    """
    by_cell = collections.defaultdict(list)
    no_role_half = 0
    pop = 0
    for o in r.by_q.get("flag", ()):
        name = str(o["value"])
        if name.endswith("Up"):
            claim = "up"
        elif name.endswith("Down"):
            claim = "down"
        else:
            no_role_half += 1
            continue
        pop += 1
        c = RD._cell_of(o["subject"])
        if c:
            by_cell[c].append(claim)

    decided = collections.defaultdict(list)
    abstained_cells = collections.Counter()
    for subj, v in r.verdict.get("stem_direction", {}).items():
        c = RD._cell_of(subj)
        if not c:
            continue
        if v.get("outcome") == "decided":
            decided[c].append(str(v.get("value")))
        else:
            abstained_cells[c] += 1

    reachable = unjoinable_no_decided = unjoinable_abstained = 0
    unjoinable_no_verdict_at_all = 0
    for c, claims in by_cell.items():
        if decided.get(c):
            reachable += len(claims)
        elif abstained_cells.get(c):
            unjoinable_abstained += len(claims)
            unjoinable_no_decided += len(claims)
        else:
            unjoinable_no_verdict_at_all += len(claims)
            unjoinable_no_decided += len(claims)

    audit = RD.f_flag_stem(r)
    return {
        "population_with_a_role_half": pop,
        "flag_classes_with_no_role_half": no_role_half,
        "in_a_cell_with_a_decided_stem_direction": reachable,
        "unjoinable": unjoinable_no_decided,
        "unjoinable_because_every_stem_direction_in_the_cell_abstained":
            unjoinable_abstained,
        "unjoinable_because_no_stem_direction_verdict_in_the_cell":
            unjoinable_no_verdict_at_all,
        "audit_cell_join": audit["detail"],
        "audit_disagree": audit["disagree"],
    }


def run(path: Path, label: str) -> dict:
    r = RD.Rec(path)
    return {
        "label": label,
        "record": str(path),
        "provenance": {"commit": r.provenance.get("commit"),
                       "dirty": r.provenance.get("dirty")},
        "rest_2_12b": rest_population(r),
        "flag_2_12e": flag_population(r),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record")
    ap.add_argument("--label", default="?")
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.all:
        man = json.loads(
            (_REPO / "benchmarks/acceptance/manifest.json").read_text())
        outdir = _REPO / "benchmarks/omr-shape-role-2026-09/out"
        outdir.mkdir(parents=True, exist_ok=True)
        results = []
        for doc in man["documents"]:
            p = RD._resolve(doc)
            dst = outdir / ("rest-flag-population--%s.json" % doc["id"])
            print("=== %s  %s" % (doc["id"], p), flush=True)
            if not p.exists():
                print("   MISSING", flush=True)
                continue
            rc = subprocess.call(
                [sys.executable, str(_HERE), "--record", str(p),
                 "--label", doc["id"], "--out", str(dst)],
                env={**os.environ, "PYTHONPATH": str(_REPO)})
            if rc not in (0, 3):
                print("   FAILED rc=%d" % rc, flush=True)
                continue
            results.append(json.loads(dst.read_text()))
        (outdir / "rest-flag-population--all.json").write_text(
            json.dumps(results, indent=1))
        return _summary(results)

    if not a.record:
        ap.error("--record or --all")
    res = run(Path(a.record), a.label)
    text = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(text)
        print("wrote", a.out)
    else:
        print(text)
    return _summary([res])


def _summary(results) -> int:
    print()
    print("%-52s %s" % ("", "  ".join("%-14s" % r["label"][:14]
                                      for r in results)))
    rows = [
        ("2.12b restWhole/restHalf on the record",
         lambda r: r["rest_2_12b"]["counts"].get("population", 0)),
        ("2.12b   measurable against the staff",
         lambda r: r["rest_2_12b"]["counts"].get("measurable", 0)),
        ("2.12b   class NOT contradicted (stays DECIDED)",
         lambda r: r["rest_2_12b"]["counts"].get("class_not_contradicted", 0)),
        ("2.12b   lands on the OTHER convention (-> NARROWED)",
         lambda r: r["rest_2_12b"]["counts"]
         .get("lands_on_the_other_convention", 0)),
        ("2.12b   lands on NEITHER (-> ABSTAIN)",
         lambda r: r["rest_2_12b"]["counts"]
         .get("lands_on_neither_convention", 0)),
        ("2.12b   ...of those, OUTSIDE their own staff",
         lambda r: (r["rest_2_12b"]["where_the_ink_stands_by_bucket"]
                    .get("neither", {}).get("below_its_own_staff", 0)
                    + r["rest_2_12b"]["where_the_ink_stands_by_bucket"]
                    .get("neither", {}).get("above_its_own_staff", 0))),
        ("2.12b   frames disagree (must be 0)",
         lambda r: r["rest_2_12b"]["counts"].get("frames_disagree", 0)),
        ("2.12b   Q.REST_POSITION rows on the record",
         lambda r: r["rest_2_12b"]["rest_position_rows_on_the_record"]),
        ("2.12e flags carrying a role half",
         lambda r: r["flag_2_12e"]["population_with_a_role_half"]),
        ("2.12e   reachable (cell has a decided stem_direction)",
         lambda r: r["flag_2_12e"]["in_a_cell_with_a_decided_stem_direction"]),
        ("2.12e   UNJOINABLE",
         lambda r: r["flag_2_12e"]["unjoinable"]),
    ]
    totals = {}
    for label, fn in rows:
        vals = [fn(r) for r in results]
        totals[label] = sum(vals)
        print("%-52s %s  = %d" % (label,
                                  "  ".join("%-14d" % v for v in vals),
                                  sum(vals)))
    live = (totals["2.12b   lands on the OTHER convention (-> NARROWED)"]
            + totals["2.12b   lands on NEITHER (-> ABSTAIN)"]
            + totals["2.12e   UNJOINABLE"])
    print()
    if live == 0:
        print("DEAD AT ZERO — neither line has a population on these records.")
        return 3
    print("POPULATION LIVE: %d rows across the three records." % live)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
