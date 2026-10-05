#!/usr/bin/env python3
"""ROADMAP 2.48 -- score base vs arm against the 2.44c reference-backed
truth set, on BOTH far heads (reusing truth_set_2_44c.py's own machinery
unmodified) and in-staff heads (the same onset-exact truth matcher, applied
to every notehead with a Q.NOTEHEAD_STAFF_POSITION row, not just the far
ones the ledger readers gate on).

MEASUREMENT ONLY. Reads two already-built GATHER+ADJUDICATE records for the
SAME page (base, arm); writes nothing back into the pipeline.
"""
import sys
import json
import collections
from pathlib import Path

REPO = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks/omr-local-staff-2026-09"))

import truth_set_2_44c as T  # noqa: E402
from tools.omr.staged import export as EXP  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.pitch_resolver import _pitch_from_position  # noqa: E402

RECORD_PATHS = {
    ("beethoven5-litolff", "base"): Path("/tmp/base-248-run/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json"),
    ("beethoven5-litolff", "arm"): REPO / "benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json",
    ("brahms1-breitkopf", "base"): Path("/tmp/base-248-run/benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json"),
    ("brahms1-breitkopf", "arm"): REPO / "benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json",
}


def load_doc_at(doc_id, record_path):
    cfg = dict(T.DOCS[doc_id])
    cfg["record"] = record_path
    result = json.loads(record_path.read_text())
    rec = EXP.Record(result)
    built = EXP.build(rec)
    parts = built[0]
    offsets, numbering = EXP._document_bar_offsets(parts)
    works_row = T._load_works_row(cfg["works_row_id"])
    ref_root = T._reference_root(works_row["reference"]["catalog_path"])

    window = works_row.get("window") or {}
    first_ref_measure = window.get("first_ref_measure")
    page_index = cfg["pdf_page_index"]
    doc_bar_of_first_cell = (offsets or {}).get((page_index, 0))
    bar_correction = 0
    if first_ref_measure is not None and doc_bar_of_first_cell is not None:
        bar_correction = int(first_ref_measure) - (doc_bar_of_first_cell + 1)
    bad_pages = T._bad_bar_count_pages(rec, cfg, offsets or {})
    return dict(cfg=cfg, rec=rec, parts=parts, offsets=offsets or {},
                works_row=works_row, ref_root=ref_root,
                bar_correction=bar_correction, bad_pages=bad_pages)


def all_notehead_subjects(rec):
    subs = set()
    for o in rec.observations:
        if o["quantity"] == Q.NOTEHEAD_STAFF_POSITION:
            subs.add(o["subject"])
    return sorted(subs)


def build_rows_all(doc_id, loaded):
    rec = loaded["rec"]
    offsets = loaded["offsets"]
    detmap = T._subject_detections(loaded["parts"])
    ref_root = loaded["ref_root"]
    bad_pages = loaded.get("bad_pages") or {}
    # ⚠️ The 2.44 ledger readers (Q.LEDGER_CLEAN_COUNT_POSITION / Q.LEDGER_
    # RUNG_GRID_POSITION) truth_set_2_44c.py's own `_far_head_subjects` uses
    # are from the UNMERGED 2.44 branch and are not present on this tree
    # (confirmed: AttributeError on Q.LEDGER_CLEAN_COUNT_POSITION). "Far"
    # is reclassified geometrically instead: outside the 5-line staff
    # (position < 0 or > 8, the same bound `gather_clef`'s own docstring
    # uses for "standing off the staff") -- a strictly WIDER population
    # than the ledger readers' own gate, so every truth_set_2_44c.py far
    # head is included, plus some this tree cannot otherwise identify.

    rows = []
    for sub in all_notehead_subjects(rec):
        parts_of_sub = sub.split("/")
        page, system, staff, cell, glyph_i = (int(x) for x in parts_of_sub[1:6])
        staff_key = f"staff/{page}/{system}/{staff}"
        clef_v = rec.value(Q.CLEF, staff_key)
        pos_obs = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
        if not pos_obs or clef_v is None:
            continue
        raw_pos = float(pos_obs[-1]["value"])
        geom_pos = int(round(raw_pos))
        geom_pitch = _pitch_from_position(geom_pos, str(clef_v))

        det = detmap.get(sub)
        our_part_id = det["our_part_id"] if det else None
        family = T._family_for_part_id(doc_id, our_part_id) if our_part_id else None
        bar = None
        if det is not None:
            off = offsets.get((det["page"], det["system"]))
            if off is not None:
                bar = off + det["cell"] + 1 + loaded["bar_correction"]

        if page in bad_pages:
            truth_pitches = []
        else:
            truth_pitches = T.onset_exact_truth(
                rec, doc_id, family, bar, ref_root, page, system, staff,
                cell, glyph_i) or []

        rows.append(dict(
            subject=sub, far=(geom_pos < 0 or geom_pos > 8), raw_pos=raw_pos,
            geom_pitch=geom_pitch, truth_pitches=truth_pitches,
        ))
    return rows


def verdict(row):
    return T._verdict(row["geom_pitch"], row["truth_pitches"])


def main():
    for doc_id in T.DOCS:
        print(f"=== {doc_id} ===")
        base = load_doc_at(doc_id, RECORD_PATHS[(doc_id, "base")])
        arm = load_doc_at(doc_id, RECORD_PATHS[(doc_id, "arm")])
        base_rows = {r["subject"]: r for r in build_rows_all(doc_id, base)}
        arm_rows = {r["subject"]: r for r in build_rows_all(doc_id, arm)}

        for label, rows in (("base", base_rows), ("arm", arm_rows)):
            for bucket in ("far", "in-staff"):
                want_far = (bucket == "far")
                sub_rows = [r for r in rows.values() if r["far"] == want_far]
                tally = collections.Counter(verdict(r) for r in sub_rows)
                print(f"  {label:<5} {bucket:<9} n={len(sub_rows):4d}  {dict(tally)}")

        common = sorted(set(base_rows) & set(arm_rows))
        changed = []
        for sub in common:
            bv = verdict(base_rows[sub])
            av = verdict(arm_rows[sub])
            if bv != av or base_rows[sub]["geom_pitch"] != arm_rows[sub]["geom_pitch"]:
                changed.append((sub, base_rows[sub]["far"], bv, av,
                               base_rows[sub]["geom_pitch"], arm_rows[sub]["geom_pitch"],
                               base_rows[sub]["raw_pos"], arm_rows[sub]["raw_pos"]))
        print(f"  heads present in both, pitch-or-verdict changed: {len(changed)}")
        right_to_wrong = [c for c in changed if c[2] == "right" and c[3] != "right"]
        wrong_to_right = [c for c in changed if c[2] != "right" and c[3] == "right"]
        print(f"  right->wrong: {len(right_to_wrong)}   wrong/other->right: {len(wrong_to_right)}")
        for sub, far, bv, av, bp, ap, braw, araw in changed:
            print(f"    {'FAR' if far else 'in-staff':9s} {sub:28s} "
                  f"{bv:7s}->{av:7s}  {bp!s:5s}->{ap!s:5s}  "
                  f"pos {braw:.2f}->{araw:.2f}")
        only_base = set(base_rows) - set(arm_rows)
        only_arm = set(arm_rows) - set(base_rows)
        print(f"  only in base: {len(only_base)}   only in arm: {len(only_arm)}")


if __name__ == "__main__":
    raise SystemExit(main())
