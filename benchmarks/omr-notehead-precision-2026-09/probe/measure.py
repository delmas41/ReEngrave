"""ROADMAP 2.4a — base vs arm for `notehead_is_not_a_notehead`, on ONE tree.

Isolates ADJUDICATE to the ONE new decision, over a Log built from the
record's own GATHER observations only (`Q.GLYPH_BOX`, `Q.CELL_BOX`,
`Q.CELL_STAFF_SPACE`, `Q.NOTEHEAD_STAFF_POSITION`, `Q.GLYPH_CONF`) — every
one a pure Observation the new decision reads directly, so re-running the
other 27 decisions (which CLAUDE.md records costing ~2.5 hours on a record
this size, full re-adjudication) buys nothing: nothing else declares or reads
this quantity (checked below, off the registry, before any number is
trusted), so their verdicts cannot move. The "base" arm is the record's OWN
saved verdicts, untouched; the "arm" is those SAME verdicts plus the new ones
appended -- so the export diff isolates exactly this decision.

    python3 probe/measure.py <record.json> --label litolff --out out/litolff.json

Exits non-zero and prints REACH=0 if nothing in the domain was found.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged import export as SX                        # noqa: E402
from tools.omr.staged.record import Log, Q, Subject              # noqa: E402

NEEDED = (Q.GLYPH_BOX, Q.CELL_BOX, Q.CELL_STAFF_SPACE,
          Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_CONF, Q.NOTEHEAD_CLASS)


def registry_check() -> None:
    """The cheap, static proof that no other decision can move: nobody else
    declares this quantity anywhere in its own registration."""
    q = Q.NOTEHEAD_IS_NOT_A_NOTEHEAD
    offenders = []
    for name, spec in adjudicate.REGISTRY.items():
        if name == q:
            continue
        if q in spec.wants or q in (spec.composed_from or ()) \
                or q in (adjudicate.domain_of(spec) or ()):
            offenders.append(name)
    if offenders:
        raise SystemExit(f"NOT ISOLATED: {offenders} also reference {q!r}")
    print(f"registry check: no other decision references {q!r} — OK")


def build_gather_log(rec: dict) -> Log:
    log = Log()
    for r in rec["observations"]:
        if r["quantity"] not in NEEDED:
            continue
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                    frame=r["frame"], score=r.get("score"), **detail)
    for r in rec.get("abstentions", []):
        if r["quantity"] not in NEEDED:
            continue
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"],
                    reason=r["reason"], **detail)
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    registry_check()

    print(f"loading {a.record} ...", file=sys.stderr)
    result = json.load(open(a.record))
    rec = result["record"]
    print(f"  observations={len(rec['observations'])} "
          f"verdicts={len(rec['verdicts'])} "
          f"abstentions={len(rec.get('abstentions', []))}", file=sys.stderr)

    log = build_gather_log(rec)
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    new_verdicts = [v for v in log.to_json()["verdicts"]
                   if v["quantity"] == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD]

    reach = len(new_verdicts)
    print(f"REACH: {reach} verdicts on {a.label}", file=sys.stderr)
    if reach == 0:
        print("DEAD: zero reach, refusing to report a result", file=sys.stderr)
        return 2

    by_reason = collections.Counter(v["reason"] for v in new_verdicts)
    refused = {v["subject"]: v for v in new_verdicts if v["value"] is True}
    print(f"  by reason (all decided): {dict(by_reason)}", file=sys.stderr)
    print(f"  refused (value=True): {len(refused)}", file=sys.stderr)

    # ── export: base (record's own verdicts) vs arm (+ new verdicts) ────────
    base_result = {"record": {"observations": rec["observations"],
                              "verdicts": rec["verdicts"],
                              "abstentions": rec.get("abstentions", [])},
                   "source": result.get("source", {})}
    arm_verdicts = list(rec["verdicts"]) + new_verdicts
    arm_result = {"record": {"observations": rec["observations"],
                             "verdicts": arm_verdicts,
                             "abstentions": rec.get("abstentions", [])},
                  "source": result.get("source", {})}

    print("exporting BASE ...", file=sys.stderr)
    _xml_base, rep_base = SX.to_musicxml(base_result)
    print("exporting ARM ...", file=sys.stderr)
    _xml_arm, rep_arm = SX.to_musicxml(arm_result)

    out = {
        "label": a.label,
        "record_counts": {"observations": len(rec["observations"]),
                          "verdicts": len(rec["verdicts"]),
                          "abstentions": len(rec.get("abstentions", []))},
        "reach": reach,
        "by_reason": dict(by_reason),
        "refused_subjects": {k: v["reason"] for k, v in refused.items()},
        "base": {
            "notes_written": rep_base["written"].get("notes"),
            "rests_written": rep_base["written"].get("rests"),
            "parts": rep_base["written"].get("parts"),
            "notes_not_written": dict(rep_base["notes_not_written"]),
            "notes_not_written_total": rep_base["notes_not_written_total"],
        },
        "arm": {
            "notes_written": rep_arm["written"].get("notes"),
            "rests_written": rep_arm["written"].get("rests"),
            "parts": rep_arm["written"].get("parts"),
            "notes_not_written": dict(rep_arm["notes_not_written"]),
            "notes_not_written_total": rep_arm["notes_not_written_total"],
        },
    }
    out["balance_holds"] = {
        "base": (rep_base["written"].get("notes", 0)
                 + rep_base["written"].get("rests", 0)
                 + rep_base["notes_not_written_total"]),
        "arm": (rep_arm["written"].get("notes", 0)
                + rep_arm["written"].get("rests", 0)
                + rep_arm["notes_not_written_total"]),
    }
    out["parts_unchanged"] = (rep_base["written"].get("parts")
                              == rep_arm["written"].get("parts"))

    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("refused_subjects",)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
