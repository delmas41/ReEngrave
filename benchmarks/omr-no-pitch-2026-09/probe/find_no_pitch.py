"""ROADMAP 2.20 probe. Loads ONE record via `record_io.load_record`, walks
the EXACT pre-pitch refusal ladder `export.to_musicxml` runs (mirrored, not
re-imported, because the ladder lives inside a closure), finds every
notehead subject that lands in `no_pitch`, and for each one classifies the
CAUSE: which staff's clef governs its pitch (its own, or the staff
`glyph_owner` moved it to) and why that staff produced nothing --
`clef_abstained:<reason>`, `clef_narrowed`, `clef_absent`,
`unknown_clef_anchor:<value>`, or `position_unread` (no
`Q.NOTEHEAD_STAFF_POSITION` row at all, so neither `restate_pitch` nor
`move_glyph` ever tried).

Usage: python3 -m tools.omr.staged... no -- run directly:
    python3 benchmarks/omr-no-pitch-2026-09/probe/find_no_pitch.py <record.json> <out.json>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged import export as X  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.pitch_resolver import _pitch_from_position  # noqa: E402


def _parse_subject(key: str):
    return X._parse_subject(key)


def classify_no_pitch(rec: X.Record, sub: str) -> dict:
    s = _parse_subject(sub)
    own_staff = f"staff/{s['page']}/{s['system']}/{s['staff']}"

    owner_v = rec.verdict(Q.GLYPH_OWNER, sub)
    owner_val = owner_v["value"] if owner_v and owner_v["outcome"] == "decided" else None
    effective_staff = own_staff
    if isinstance(owner_val, str) and owner_val and owner_val != own_staff:
        effective_staff = owner_val

    pos_rows = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
    if not pos_rows:
        return {"cause": "position_unread", "effective_staff": effective_staff,
                "owner_outcome": owner_v["outcome"] if owner_v else "absent"}

    clef_v = rec.verdict(Q.CLEF, effective_staff)
    if clef_v is None:
        cause = "clef_absent"
    elif clef_v["outcome"] == "abstained":
        cause = f"clef_abstained:{clef_v.get('reason', '?')}"
    elif clef_v["outcome"] == "narrowed":
        cause = "clef_narrowed"
    else:
        pos = int(round(float(pos_rows[0]["value"])))
        name = _pitch_from_position(pos, str(clef_v["value"]))
        if name is None:
            cause = f"unknown_clef_anchor:{clef_v['value']!r}"
        else:
            # Should not happen: pitch SHOULD have been written. Flag it.
            cause = "UNEXPLAINED_clef_decided_and_anchor_known"

    return {"cause": cause, "effective_staff": effective_staff,
            "own_staff": own_staff,
            "owner_outcome": owner_v["outcome"] if owner_v else "absent",
            "moved": effective_staff != own_staff,
            "position_value": pos_rows[0]["value"]}


def find_no_pitch(rec: X.Record) -> dict:
    """Mirrors `export.to_musicxml`'s ladder up to and including the
    `no_pitch` drop (export.py:796-936), nothing after it -- duration and
    ownership checks run LATER in the real exporter and must not gate this
    one."""
    from tools.omr.staged.export import whole_rest_ink_enabled

    refuse_whole_rest_ink = whole_rest_ink_enabled()
    no_pitch_subjects = []
    total_notehead_glyphs = 0
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = _parse_subject(sub)
        if s["glyph"] is None:
            continue
        is_rest = bool(rec.obs(Q.REST, sub))
        if not is_rest and not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue
        if is_rest:
            continue  # rests never ask for a pitch; not our population
        total_notehead_glyphs += 1
        npv = rec.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
        if npv is not None and npv["outcome"] == "decided" and npv["value"] is True:
            continue
        if refuse_whole_rest_ink and rec.value(Q.NOTEHEAD_IS_A_WHOLE_REST, sub) is True:
            continue
        pitch = rec.value(Q.PITCH, sub)
        if pitch is None:
            no_pitch_subjects.append(sub)

    causes = {}
    detail = {}
    for sub in no_pitch_subjects:
        c = classify_no_pitch(rec, sub)
        detail[sub] = c
        causes.setdefault(c["cause"], 0)
        causes[c["cause"]] += 1

    return {
        "total_notehead_glyphs": total_notehead_glyphs,
        "no_pitch_count": len(no_pitch_subjects),
        "causes": causes,
        "subjects": detail,
    }


def main(argv):
    record_path, out_path = argv[1], argv[2]
    t0 = time.time()
    result = load_record(record_path)
    t1 = time.time()
    print(f"loaded {record_path} in {t1 - t0:.1f}s", file=sys.stderr)
    rec = X.Record(result)
    t2 = time.time()
    print(f"indexed in {t2 - t1:.1f}s", file=sys.stderr)
    report = find_no_pitch(rec)
    report["commit"] = (result.get("provenance") or {}).get("commit")
    report["dirty"] = (result.get("provenance") or {}).get("dirty")
    Path(out_path).write_text(json.dumps(report, indent=1))
    t3 = time.time()
    print(f"classified {report['no_pitch_count']} no_pitch subjects in {t3 - t2:.1f}s -> {out_path}",
          file=sys.stderr)
    print(json.dumps(report["causes"], indent=2))


if __name__ == "__main__":
    main(sys.argv)
