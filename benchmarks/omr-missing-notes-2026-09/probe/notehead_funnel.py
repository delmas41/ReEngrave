"""ROADMAP work-order item 2 (2026-09-28/29) -- the missing-notes diagnosis
for Brahms 1/i (Breitkopf). PATH: STAGED.

Reads the amended record ONCE via `record_io.load_record` (CLAUDE.md SS4b --
the one sanctioned reader) and dumps everything this diagnosis needs to a
small JSON so the record is never opened a second time. Two independent
questions, both answered off the SAME `Record` object built from the SAME
load:

  1. THE AUTHORITATIVE FUNNEL. `export.to_musicxml` is called once (the same
     function the product path calls at EXPORT -- no re-gather, no
     re-adjudicate, exactly `reexport.py`'s own precedent in
     `benchmarks/omr-accidental-2026-09/probe/reexport.py`). Its own
     `report["notes_not_written"]` and `report["bars_held_out_sum"]` are the
     numbers CLAUDE.md SS4c calls the accounting control -- an EQUALITY, not
     a computation this script invents.

  2. THE SUB-REASON BREAKDOWN. `report["notes_not_written"]` gives
     `duration_narrowed`, `no_pitch`, etc. as FLAT counts; the brief asks for
     `duration_narrowed` broken down by the duration verdict's OWN reason
     (`beams_ambiguous`, ...) and `no_pitch` by why the pitch never arrived.
     Getting that means walking the SAME population `_place_notes` walks, up
     to (not past) the duration/pitch checks -- so this script replicates
     ONLY that prefix of `export._place_notes` (lines ~789-945 of
     `tools/omr/staged/export.py`, read and copied deliberately rather than
     imported, because the real function's `_drop` closure is not
     addressable from outside it) and CROSS-VALIDATES every bucket it
     produces against the authoritative `dropped` counter `export.build`
     itself returns (the SAME call `to_musicxml` makes internally) -- a
     control that can fail: any drift between this walk and the real one
     shows up as a nonzero `mismatch` in the dump, not as a silent wrong
     answer.

Usage (run as nohup -- the record is 1.5 GB):

    python3 -m benchmarks.omr-missing-notes-2026-09.probe.notehead_funnel \
        --record /path/to/amended.record.json \
        --out benchmarks/omr-missing-notes-2026-09/probe/out/funnel.json

(module path has a hyphen, so invoke by file path instead -- see the nohup
script beside this file.)
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from tools.omr.staged import export as E
    from tools.omr.staged import record_io
    from tools.omr.staged.record import Q

    log(f"loading {a.record} via record_io.load_record (ONE read) ...")
    t0 = time.time()
    doc = record_io.load_record(a.record)
    log(f"loaded in {time.time() - t0:.1f}s")
    # ⚠️ `provenance` is a TOP-LEVEL sibling of `record`, not nested inside
    # it (`record_io.load_record`'s own envelope shape: {record, summary,
    # provenance}) -- get it wrong and every reader downstream silently sees
    # `None` and reports an unstamped record as if it were one.
    provenance = doc.get("provenance")
    log(f"provenance: {provenance}")

    log("building Record() index ...")
    t0 = time.time()
    rec = E.Record(doc)
    log(f"Record() built in {time.time() - t0:.1f}s "
        f"({len(rec.observations)} observations, {len(rec.verdicts)} verdicts)")

    # ── 1. THE AUTHORITATIVE FUNNEL: export.build + export.to_musicxml ─────
    log("calling export.build(rec) for the pre-render (_place_notes) funnel ...")
    t0 = time.time()
    (parts, build_provenance, build_dropped, arcs_dropped, artics_dropped,
     fermatas_dropped, ornaments_dropped, notes_dropped_by_system,
     dot_role_report) = E.build(rec)
    log(f"build() done in {time.time() - t0:.1f}s")

    log("calling export.to_musicxml(doc) for the full (post-render) census ...")
    t0 = time.time()
    xml, report = E.to_musicxml(doc)
    log(f"to_musicxml() done in {time.time() - t0:.1f}s, "
        f"xml is {len(xml)} chars")

    notes_not_written = dict(report.get("notes_not_written") or {})
    bars_held_out_sum = dict(report.get("bars_held_out_sum") or {})
    written = dict(report.get("written") or {})
    status_census = report.get("status_census")

    # sanity: build()'s own dropped is the PRE-RENDER subset of the full
    # notes_not_written; the only key the render adds is `bar_does_not_add_up`
    # (from `_BAR_SUM_REFUSAL`, `_part_xml`'s own `drops` calls) and
    # `possibly_unread_mark` (from `_MARK_REFUSAL`, 2.4c) where it fires.
    prerender_keys_mismatch = {
        k: (build_dropped.get(k, 0), notes_not_written.get(k, 0))
        for k in set(build_dropped) | set(notes_not_written)
        if k not in ("bar_does_not_add_up", "possibly_unread_mark")
        and build_dropped.get(k, 0) != notes_not_written.get(k, 0)
    }
    log(f"pre-render key mismatch (should be empty): {prerender_keys_mismatch}")

    # ── 2. SUB-REASON WALK, mirroring export._place_notes's PREFIX ─────────
    # (not_a_notehead / not_a_rest / whole_rest / no_pitch / duration only --
    # the checks that run BEFORE the owner/held-out checks, which need
    # `runs`/`held_out` this walk does not build).
    log("sub-reason walk over Q.GLYPH_BOX (mirrors _place_notes's prefix) ...")
    t0 = time.time()
    refuse_whole_rest_ink = E.whole_rest_ink_enabled()
    mirror_dropped: collections.Counter = collections.Counter()
    duration_narrowed_reasons: collections.Counter = collections.Counter()
    duration_abstained_reasons: collections.Counter = collections.Counter()
    rest_duration_narrowed_reasons: collections.Counter = collections.Counter()
    rest_duration_abstained_reasons: collections.Counter = collections.Counter()
    no_pitch_reasons: collections.Counter = collections.Counter()
    # A few named examples per (bucket, reason) for `trace --subject` later.
    # Capped per PAGE too, so a bucket's examples spread across the movement
    # instead of clustering on page 0 (the same reason `crop_losers_2_6b.py`
    # round-robins by page before it ever renders anything).
    examples: dict = collections.defaultdict(list)
    MAX_EXAMPLES = 20
    MAX_PER_PAGE = 3
    _examples_per_page: dict = collections.defaultdict(lambda: collections.Counter())

    def _example(key: str, sub: str, detail: dict) -> None:
        if len(examples[key]) >= MAX_EXAMPLES:
            return
        page = int(sub.split("/")[1])
        if _examples_per_page[key][page] >= MAX_PER_PAGE:
            return
        _examples_per_page[key][page] += 1
        examples[key].append({"subject": sub, **detail})

    clef_decided_cache: dict = {}

    def _clef_status(staff_key: str) -> str:
        if staff_key not in clef_decided_cache:
            v = rec.verdict(Q.CLEF, staff_key)
            if v is None:
                clef_decided_cache[staff_key] = "no_clef_verdict"
            elif v["outcome"] == "decided":
                clef_decided_cache[staff_key] = "clef_decided"
            else:
                clef_decided_cache[staff_key] = f"clef_{v['outcome']}"
        return clef_decided_cache[staff_key]

    n_glyph_box = 0
    for o in rec.obs_of(Q.GLYPH_BOX):
        n_glyph_box += 1
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None:
            continue
        is_rest = bool(rec.obs(Q.REST, sub))
        if not is_rest and not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue
        box_rows = rec.obs(Q.GLYPH_BOX, sub)
        bbox = box_rows[-1]["value"] if box_rows else None
        # ⚠️ CANONICAL, NOT PAGE PIXELS. `bbox`'s [x,y,w,h] is measured
        # inside the cell's own rescaled frame (CLAUDE.md SS10: "a canonical
        # cell frame cannot answer a cross-staff question"); the PAGE-frame
        # rectangle, when GATHER could place one, rides beside it in
        # `detail.bbox_page_px` as `[x0,y0,x1,y1]` corners
        # (`export._page_box_of`'s own reader). Crops need THIS one.
        bbox_page = (box_rows[-1].get("detail") or {}).get("bbox_page_px") \
            if box_rows else None
        if not is_rest:
            npv = rec.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
            if (npv is not None and npv["outcome"] == "decided"
                    and npv["value"] is True):
                key = f"not_a_notehead:{npv.get('reason', '?')}"
                mirror_dropped[key] += 1
                _example(key, sub, {"bbox": bbox, "bbox_page": bbox_page, "detail": npv.get("detail")})
                continue
        else:
            rnv = rec.verdict(Q.REST_IS_NOT_A_REST, sub)
            if (rnv is not None and rnv["outcome"] == "decided"
                    and rnv["value"] is True):
                key = f"not_a_rest:{rnv.get('reason', '?')}"
                mirror_dropped[key] += 1
                _example(key, sub, {"bbox": bbox, "bbox_page": bbox_page, "detail": rnv.get("detail")})
                continue
        if (not is_rest and refuse_whole_rest_ink
                and rec.value(Q.NOTEHEAD_IS_A_WHOLE_REST, sub) is True):
            mirror_dropped["ink_is_a_whole_rest"] += 1
            continue
        pitch = None if is_rest else rec.value(Q.PITCH, sub)
        if pitch is None and not is_rest:
            mirror_dropped["no_pitch"] += 1
            staff_key = f"staff/{s['page']}/{s['system']}/{s['staff']}"
            why = _clef_status(staff_key)
            no_pitch_reasons[why] += 1
            _example("no_pitch:" + why, sub, {"bbox": bbox, "bbox_page": bbox_page, "staff": staff_key})
            continue
        dur_v = rec.verdict(Q.DURATION, sub)
        dur = dur_v["value"] if dur_v and dur_v["outcome"] == "decided" else None
        if not isinstance(dur, dict):
            key = ("rest_" if is_rest else "") + "duration_" + (
                dur_v["outcome"] if dur_v else "absent")
            mirror_dropped[key] += 1
            reason = (dur_v.get("reason") if dur_v else "no_duration_verdict") or "unstated"
            bucket = (rest_duration_narrowed_reasons if is_rest and dur_v
                      and dur_v["outcome"] == "narrowed" else
                      rest_duration_abstained_reasons if is_rest and dur_v
                      and dur_v["outcome"] == "abstained" else
                      duration_narrowed_reasons if dur_v
                      and dur_v["outcome"] == "narrowed" else
                      duration_abstained_reasons)
            bucket[reason] += 1
            _example(f"{key}:{reason}", sub, {
                "bbox": bbox,
                "bbox_page": bbox_page,
                "detail": (dur_v.get("detail") if dur_v else None),
                "candidates": (dur_v.get("candidates") if dur_v else None),
            })
            continue
        # passes duration -- everything past here (owner/held-out/etc.) is
        # left to the authoritative `dropped` counter above; not re-walked.
        mirror_dropped["_passed_prefix"] += 1
    log(f"sub-reason walk done in {time.time() - t0:.1f}s over "
        f"{n_glyph_box} Q.GLYPH_BOX rows")

    # cross-validate the walk against the authoritative pre-render dropped,
    # for exactly the keys this walk computes (a control that can fail).
    walk_keys = set(mirror_dropped) - {"_passed_prefix"}
    walk_mismatch = {
        k: (mirror_dropped.get(k, 0), build_dropped.get(k, 0))
        for k in walk_keys | {k for k in build_dropped if k.split(":")[0] in
                              ("not_a_notehead", "not_a_rest") or k in
                              ("ink_is_a_whole_rest", "no_pitch",
                               "duration_narrowed", "duration_abstained",
                               "duration_absent", "rest_duration_narrowed",
                               "rest_duration_abstained", "rest_duration_absent")}
        if mirror_dropped.get(k, 0) != build_dropped.get(k, 0)
    }
    log(f"walk vs. authoritative mismatch (should be empty): {walk_mismatch}")

    # ── gathered population (for the accounting equality) ───────────────────
    gathered_notehead_or_rest = 0
    for o in rec.obs_of(Q.GLYPH_BOX):
        s = E._parse_subject(o["subject"])
        if s["glyph"] is None:
            continue
        is_rest = bool(rec.obs(Q.REST, o["subject"]))
        if is_rest or rec.obs(Q.NOTEHEAD_CLASS, o["subject"]):
            gathered_notehead_or_rest += 1

    # ── geometry for every EXAMPLE subject, so the crop step never has to
    # open the record a second time (CLAUDE.md SS4b: read it ONCE). Cheap:
    # a few dozen subjects, not the whole population.
    log("collecting crop geometry for example subjects ...")
    geometry: dict = {}
    for key, rows in examples.items():
        for row in rows:
            sub = row["subject"]
            s = E._parse_subject(sub)
            staff_key = f"staff/{s['page']}/{s['system']}/{s['staff']}"
            cell_key = f"cell/{s['page']}/{s['system']}/{s['staff']}/{s['cell']}"
            if sub in geometry:
                continue
            lines_rows = rec.obs(Q.STAFF_LINES, staff_key)
            sp_rows = rec.obs(Q.STAFF_SPACING, staff_key)
            cell_rows = rec.obs(Q.CELL_BOX, cell_key)
            mp_v = rec.verdict(Q.MEASURE_PARTITION, staff_key)
            geometry[sub] = {
                "page": s["page"], "system": s["system"], "staff": s["staff"],
                "cell": s["cell"],
                "staff_key": staff_key, "cell_key": cell_key,
                "staff_lines": lines_rows[-1]["value"] if lines_rows else None,
                "staff_spacing": sp_rows[-1]["value"] if sp_rows else None,
                "cell_box": cell_rows[-1]["value"] if cell_rows else None,
                "n_measures_on_staff": (mp_v.get("value")
                                         if mp_v and mp_v.get("outcome") == "decided"
                                         else None),
            }
    log(f"geometry collected for {len(geometry)} example subjects")

    pdf_path = (((provenance or {}).get("settings") or {}).get("args") or {}).get("pdf")

    out = {
        "record": a.record,
        "provenance": provenance,
        "pdf": pdf_path,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gathered_notehead_or_rest": gathered_notehead_or_rest,
        "written_notes": written.get("notes"),
        "written_rests": written.get("rests"),
        "written": written,
        "notes_not_written": notes_not_written,
        "notes_not_written_total": report.get("notes_not_written_total"),
        "bars_held_out_sum": {
            k: v for k, v in bars_held_out_sum.items() if k != "held"},
        "bars_held_out_sum_n_held_rows": len(bars_held_out_sum.get("held") or ()),
        "status_census": status_census,
        "prerender_vs_full_mismatch": prerender_keys_mismatch,
        "sub_reasons": {
            "duration_narrowed": dict(duration_narrowed_reasons),
            "duration_abstained": dict(duration_abstained_reasons),
            "rest_duration_narrowed": dict(rest_duration_narrowed_reasons),
            "rest_duration_abstained": dict(rest_duration_abstained_reasons),
            "no_pitch": dict(no_pitch_reasons),
        },
        "walk_cross_check": {
            "mismatch": walk_mismatch,
            "mirror_dropped": dict(mirror_dropped),
            "n_glyph_box_rows": n_glyph_box,
        },
        "examples": {k: v for k, v in examples.items()},
        "geometry": geometry,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    log(f"wrote {a.out}")
    print(json.dumps({
        "notes_not_written_total": out["notes_not_written_total"],
        "top5": sorted(notes_not_written.items(), key=lambda kv: -kv[1])[:5],
        "walk_mismatch_n": len(walk_mismatch),
        "prerender_mismatch_n": len(prerender_keys_mismatch),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
