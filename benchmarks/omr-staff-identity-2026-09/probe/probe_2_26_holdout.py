"""ROADMAP 2.26 probe. Loads ONE staged record via `record_io.load_record`
(the one legal reader of a record FILE -- CLAUDE.md rule "a record file is
read ONLY via record_io.load_record"), finds every STAFF the exporter holds
out under `staff_not_identified`, and for each one reports:

  * page/system/staff, the number of notehead glyphs that would reach the
    `held_out` check and be counted there (mirrors `export._place_notes`'s
    ladder exactly, lines 796-983 of `tools/omr/staged/export.py`, up to and
    including the `held_out` test -- never re-derived from the aggregate);
  * the staff's own `Q.SLOT_INDEX` verdict (outcome, reason, detail,
    candidates) -- what `adjudicate_slot_index` and, where it fired,
    `inferences.collapse_slot_index_to_family_block` said about it;
  * the staff's `Q.INSTRUMENT` verdict;
  * its system's `Q.SYSTEM_STAFF_COUNT` verdict and the document's widest
    system (the reference-lineup size `adjudicate_slot_index` picks against);
  * the document's `Q.PART_PARTITION` verdict (which join was used and why).

Usage:
    python3 benchmarks/omr-staff-identity-2026-09/probe/probe_2_26_holdout.py \
        <record.json> <out.json>

Run under `nohup` for the whole-movement Brahms record (1.4 GB) -- see the
FINDINGS for the command and the memory note (CLAUDE.md rule: another
re-decide runs on the same file; watch RSS).
"""
from __future__ import annotations

import collections
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged import export as X  # noqa: E402
from tools.omr.staged import adjudicate as A  # noqa: E402
from tools.omr.staged.adjudicators.ownership import (  # noqa: E402
    OWNER_NOT_READ_REASONS)
from tools.omr.staged.record import Q  # noqa: E402


def _parse(sub: str):
    return X._parse_subject(sub)


def _staff_key(page, system, staff) -> str:
    return X._staff_key(page or 0, system or 0, staff or 0)


def _classify(rec: X.Record, sub: str, refuse_whole_rest_ink: bool):
    """Mirrors `export._place_notes`'s ladder for ONE glyph. Returns a
    `(reason, home_or_None)` pair -- `reason` is the exact bucket the real
    exporter would drop this glyph under (or `"written"` if it survives every
    check this probe replicates -- duration VALUE placement and downstream
    join failures are not mirrored, since only the reasons up to and
    including `staff_not_identified` matter for this question), and `home` is
    the staff key the drop (or write) is attributed to."""
    s = _parse(sub)
    is_rest = bool(rec.obs(Q.REST, sub))
    if not is_rest and not rec.obs(Q.NOTEHEAD_CLASS, sub):
        return None, None  # not part of the notehead/rest population at all

    if not is_rest:
        npv = rec.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
        if npv is not None and npv["outcome"] == "decided" and npv["value"] is True:
            return "not_a_notehead", None
    else:
        rnv = rec.verdict(Q.REST_IS_NOT_A_REST, sub)
        if rnv is not None and rnv["outcome"] == "decided" and rnv["value"] is True:
            return "not_a_rest", None

    if (not is_rest and refuse_whole_rest_ink
            and rec.value(Q.NOTEHEAD_IS_A_WHOLE_REST, sub) is True):
        return "ink_is_a_whole_rest", None

    pitch = None if is_rest else rec.value(Q.PITCH, sub)
    if pitch is None and not is_rest:
        return "no_pitch", None

    dur_v = rec.verdict(Q.DURATION, sub)
    dur = dur_v["value"] if dur_v and dur_v["outcome"] == "decided" else None
    if not isinstance(dur, dict):
        return ("rest_" if is_rest else "") + "duration_not_decided", None

    owner = rec.value(Q.GLYPH_OWNER, sub)
    if A.is_relocated_copy(sub, owner):
        return "owned_by_another_staff", None
    own_v = rec.verdict(Q.GLYPH_OWNER, sub)
    if (own_v and own_v.get("outcome") == "abstained"
            and own_v.get("reason") in OWNER_NOT_READ_REASONS):
        return "owner_not_read", None

    home = _staff_key(s["page"], s["system"], s["staff"])
    return "reaches_held_out_check", home


def _slot_summary(rec: X.Record, staff_key: str) -> dict:
    v = rec.verdict(Q.SLOT_INDEX, staff_key)
    if v is None:
        return {"outcome": "absent"}
    out = {"outcome": v["outcome"], "reason": v.get("reason"),
           "decider": v.get("decider"), "value": v.get("value")}
    detail = v.get("detail") or {}
    # Keep the detail SMALL -- some carry a `run`/`candidates` list, never the
    # per-glyph `basis`/`considered` ids (thousands of them, pooled).
    out["detail"] = {k: detail[k] for k in
                     ("family", "instrument", "run", "front_aligned",
                      "block_size", "block_index", "reference",
                      "condensed_with_slot", "channels", "channels_dropped",
                      "narrowed_from", "note")
                     if k in detail}
    cands = v.get("candidates") or []
    out["candidates"] = [{"value": c.get("value"), "support": c.get("support"),
                          "detail": c.get("detail")} for c in cands]
    return out


def _instrument_summary(rec: X.Record, staff_key: str) -> dict:
    v = rec.verdict(Q.INSTRUMENT, staff_key)
    if v is None:
        return {"outcome": "absent"}
    val = v.get("value")
    return {"outcome": v["outcome"], "reason": v.get("reason"),
           "name": (val or {}).get("name") if isinstance(val, dict) else None,
           "family": (val or {}).get("family") if isinstance(val, dict) else None}


def main(argv):
    record_path, out_path = argv[1], argv[2]
    t0 = time.time()
    result = load_record(record_path)
    t1 = time.time()
    print(f"loaded {record_path} in {t1 - t0:.1f}s", file=sys.stderr)
    rec = X.Record(result)
    t2 = time.time()
    print(f"indexed in {t2 - t1:.1f}s ({len(rec.observations)} obs, "
          f"{len(rec.verdicts)} verdicts)", file=sys.stderr)

    join_v = rec.verdict(Q.PART_PARTITION, "document")
    join = None
    if join_v and join_v["outcome"] == "decided":
        join = (join_v.get("value") or {}).get("join")

    # Every staff this record names, from the two quantities the exporter
    # itself keys the held-out test on -- SLOT_INDEX (the test) and
    # STAFF_ORDINAL (present on every gathered staff, held-out or not, so the
    # union catches a staff SLOT_INDEX never even ran on).
    staff_keys = set()
    for q in (Q.SLOT_INDEX, Q.STAFF_ORDINAL):
        for v in rec.verdicts_of(q):
            s = _parse(v["subject"])
            if s.get("staff") is not None and s.get("glyph") is None and s.get("cell") is None:
                staff_keys.add(_staff_key(s["page"], s["system"], s["staff"]))

    held_out = set()
    if join == "slot":
        for k in staff_keys:
            if not isinstance(rec.value(Q.SLOT_INDEX, k), int):
                held_out.add(k)

    # System staff counts, for the reference-lineup context.
    system_counts = {}
    for v in rec.verdicts_of(Q.SYSTEM_STAFF_COUNT):
        if v["outcome"] == "decided" and isinstance(v.get("value"), int):
            system_counts[v["subject"]] = v["value"]
    widest = max(system_counts.values()) if system_counts else None

    refuse_whole_rest_ink = X.whole_rest_ink_enabled()
    drop_totals = collections.Counter()
    heads_by_home = collections.Counter()      # noteheads only
    rests_by_home = collections.Counter()
    n_notehead_glyphs = 0
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = _parse(sub)
        if s.get("glyph") is None:
            continue
        is_rest = bool(rec.obs(Q.REST, sub))
        if not is_rest:
            n_notehead_glyphs += 1
        reason, home = _classify(rec, sub, refuse_whole_rest_ink)
        if reason is None:
            continue
        if reason == "reaches_held_out_check":
            if home in held_out:
                drop_totals["staff_not_identified"] += 1
                if is_rest:
                    rests_by_home[home] += 1
                else:
                    heads_by_home[home] += 1
            else:
                drop_totals["written_or_downstream"] += 1
        else:
            drop_totals[reason] += 1
    t3 = time.time()
    print(f"walked {n_notehead_glyphs} notehead glyphs in {t3 - t2:.1f}s",
          file=sys.stderr)

    per_staff = []
    for k in sorted(held_out, key=lambda k: (
            _parse(k)["page"], _parse(k)["system"], _parse(k)["staff"])):
        s = _parse(k)
        sys_key = f"system/{s['page']}/{s['system']}"
        per_staff.append({
            "staff": k,
            "page": s["page"], "system": s["system"], "staff_ordinal": s["staff"],
            "heads_held_out": heads_by_home.get(k, 0),
            "rests_held_out": rests_by_home.get(k, 0),
            "system_staff_count": system_counts.get(sys_key),
            "widest_system_in_document": widest,
            "slot_index": _slot_summary(rec, k),
            "instrument": _instrument_summary(rec, k),
        })

    report = {
        "record": str(record_path),
        "commit": (result.get("provenance") or {}).get("commit"),
        "dirty": (result.get("provenance") or {}).get("dirty"),
        "document_part_partition": {
            "outcome": join_v["outcome"] if join_v else "absent",
            "reason": join_v.get("reason") if join_v else None,
            "value": join_v.get("value") if join_v else None,
        },
        "join_used": join,
        "n_staff_subjects": len(staff_keys),
        "n_held_out_staves": len(held_out),
        "held_out_staves": sorted(held_out),
        "heads_held_out_total": sum(heads_by_home.values()),
        "rests_held_out_total": sum(rests_by_home.values()),
        "drop_ladder_totals": dict(drop_totals),
        "slot_index_reason_histogram_over_held_out_staves": dict(collections.Counter(
            (rec.verdict(Q.SLOT_INDEX, k) or {}).get("outcome", "absent")
            for k in held_out
        )),
        "slot_index_abstain_reason_histogram": dict(collections.Counter(
            (rec.verdict(Q.SLOT_INDEX, k) or {}).get("reason")
            for k in held_out
            if (rec.verdict(Q.SLOT_INDEX, k) or {}).get("outcome") == "abstained"
        )),
        "per_staff": per_staff,
    }
    Path(out_path).write_text(json.dumps(report, indent=1))
    t4 = time.time()
    print(f"wrote {out_path} in {t4 - t3:.1f}s; "
          f"heads_held_out_total={report['heads_held_out_total']} "
          f"n_held_out_staves={report['n_held_out_staves']}", file=sys.stderr)
    print(json.dumps(report["slot_index_abstain_reason_histogram"], indent=2))


if __name__ == "__main__":
    main(sys.argv)
