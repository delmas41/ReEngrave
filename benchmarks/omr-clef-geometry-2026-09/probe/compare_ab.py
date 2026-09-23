#!/usr/bin/env python3
"""ROADMAP 2.11 — base vs arm on ONE page, against the roadmap's own gates.

    python3 benchmarks/omr-clef-geometry-2026-09/probe/compare_ab.py \
        --base <out>/base-litolff-p3.record.json \
        --arm  <out>/arm-litolff-p3.record.json \
        --subject staff/3/0/9 \
        --out-json <out>/ab-litolff-p3.json

Reports, and each is one of the gates:

  * the named subject's `clef` verdict, before and after;
  * EVERY `clef` verdict on the page, before and after, and how many READ
    clefs (a DECIDED verdict with a value) CHANGED — the gate is 0;
  * the `clef_located` rows that carry `overrides_notehead_box`, and the
    glyph subjects each one named;
  * the `is_a_clef` refusals, and their classes and confidences;
  * the export's own `notes_not_written` for the page, before and after;
  * `status_census.unaccounted` and the export balance, both arms.

⚠️ THE EXPORT IS RUN IN-PROCESS ON BOTH RECORDS BY THE SHIPPED
`to_musicxml`, not re-implemented. `to_musicxml` RAISES `Unbalanced` rather
than returning a flag, so an unbalanced arm fails this script rather than
being reported as a number.

⚠️ THE PER-STAFF HEAD COUNT IS NOT COMPUTED HERE. It is
`benchmarks/omr-notehead-funnel-2026-09/probe/funnel.py`'s question and that
probe instruments `export._place_notes` at runtime with its own control; a
second copy of "the refusal buckets" is exactly the mistake
`omr-cleanup-count-2026-09/build_sheet.py` already paid for. Run it on each
arm and quote it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.omr.staged.record_io import load_record            # noqa: E402
from tools.omr.staged import export as SX                     # noqa: E402


def _page_of(subject: str) -> Optional[str]:
    p = subject.split("/")
    return p[1] if len(p) > 1 and p[0] in ("staff", "cell", "glyph", "system") \
        else None


def _read(path: str) -> Dict[str, Any]:
    data = load_record(path)
    rec = data["record"]
    clef: Dict[str, dict] = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "clef":
            clef[v["subject"]] = {"outcome": v["outcome"],
                                  "value": v.get("value"),
                                  "reason": v.get("reason")}
    overrides: List[dict] = []
    located: Dict[str, List[dict]] = {}
    for o in rec["observations"]:
        if o["quantity"] != "clef_located":
            continue
        d = o.get("detail") or {}
        located.setdefault(o["subject"], []).append(
            {"frame": o.get("frame"), "read": o.get("value"),
             "symmetry": o.get("score"), "h_spaces": d.get("h_spaces"),
             "w_spaces": d.get("w_spaces")})
        if d.get("overrides_notehead_box"):
            overrides.append({
                "staff": o["subject"], "frame": o.get("frame"),
                "read": o.get("value"), "symmetry": o.get("score"),
                "h_spaces": d.get("h_spaces"), "w_spaces": d.get("w_spaces"),
                "overrode": list(d.get("overrode_glyph_subjects") or ())})

    box_class = {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box" and isinstance(o["value"], (list, tuple)):
            box_class[o["subject"]] = (str(o["value"][0]), o.get("score"))
    refusals: List[dict] = []
    for v in rec["verdicts"]:
        if v["quantity"] == "notehead_is_not_a_notehead" and v.get("value") \
                and v.get("reason") == "is_a_clef":
            cls, conf = box_class.get(v["subject"], (None, None))
            refusals.append({"glyph": v["subject"], "class": cls,
                             "conf": conf, "basis": v.get("basis")})

    # ⚠️ THE SHIPPED EXPORTER, on the SAME dict the CLI would hand it.
    _xml, report = SX.to_musicxml(data)
    census = SX.coverage(data).get("status_census") \
        if hasattr(SX, "coverage") else None

    return {
        "path": path,
        "provenance": data.get("provenance"),
        "clef": clef,
        "clef_located": located,
        "overrides": overrides,
        "is_a_clef_refusals": refusals,
        "notes_not_written": report.get("notes_not_written"),
        "notes_not_written_total": report.get("notes_not_written_total"),
        "notes_not_written_by_system": report.get("notes_not_written_by_system"),
        "status_census_unaccounted": (census or {}).get("unaccounted"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--subject", default=None)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    base = _read(args.base)
    arm = _read(args.arm)

    staves = sorted(set(base["clef"]) | set(arm["clef"]))
    changed: List[dict] = []
    read_changed: List[dict] = []
    for s in staves:
        b = base["clef"].get(s)
        a = arm["clef"].get(s)
        if b == a:
            continue
        row = {"staff": s, "base": b, "arm": a}
        changed.append(row)
        # A READ clef is a DECIDED verdict with a value. The gate is that no
        # such verdict moves -- a staff going ABSTAINED -> DECIDED is the
        # POINT of 2.11 and is not a change to a read clef.
        if b and b.get("outcome") == "decided" and b.get("value") is not None \
                and (not a or a.get("outcome") != "decided"
                     or a.get("value") != b.get("value")):
            read_changed.append(row)

    out = {
        "base": {k: base[k] for k in
                 ("path", "provenance", "notes_not_written",
                  "notes_not_written_total", "notes_not_written_by_system",
                  "status_census_unaccounted", "overrides",
                  "is_a_clef_refusals")},
        "arm": {k: arm[k] for k in
                ("path", "provenance", "notes_not_written",
                 "notes_not_written_total", "notes_not_written_by_system",
                 "status_census_unaccounted", "overrides",
                 "is_a_clef_refusals")},
        "clef_verdicts_base": base["clef"],
        "clef_verdicts_arm": arm["clef"],
        "clef_verdicts_changed": changed,
        "READ_clefs_changed": read_changed,
        "n_staves_with_a_clef_verdict": len(staves),
    }
    if args.subject:
        out["subject"] = {
            "id": args.subject,
            "clef_base": base["clef"].get(args.subject),
            "clef_arm": arm["clef"].get(args.subject),
            "clef_located_base": base["clef_located"].get(args.subject),
            "clef_located_arm": arm["clef_located"].get(args.subject),
        }

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=1))

    print("staves with a clef verdict      %d" % len(staves))
    print("clef verdicts CHANGED           %d" % len(changed))
    print("READ clefs CHANGED (gate 0)     %d" % len(read_changed))
    print("overrides base/arm              %d / %d"
          % (len(base["overrides"]), len(arm["overrides"])))
    print("is_a_clef refusals base/arm     %d / %d"
          % (len(base["is_a_clef_refusals"]), len(arm["is_a_clef_refusals"])))
    print("notes_not_written base          %s" % base["notes_not_written"])
    print("notes_not_written arm           %s" % arm["notes_not_written"])
    print("status_census unaccounted       %s / %s"
          % (base["status_census_unaccounted"],
             arm["status_census_unaccounted"]))
    if args.subject:
        print("%s clef  %s -> %s" % (args.subject,
                                     base["clef"].get(args.subject),
                                     arm["clef"].get(args.subject)))
    print("wrote %s" % args.out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
