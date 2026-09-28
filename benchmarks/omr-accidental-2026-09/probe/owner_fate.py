"""ROADMAP 2.7 — where every DECIDED accidental owner went, and the gate's
count-page figure, off an ARM record.

`accidental_reading.unowned` says how many decided owners did not become an
`<accidental>`; it cannot say WHY. This joins each decided owner's head to
the exporter's own refusals, taken from the exporter and not restated:

  * a place-time refusal (`no_pitch`, `owned_by_another_staff`,
    `duration_narrowed`, ...) through `review.rerun.export_with_subjects`,
    whose control raises if its per-subject log does not sum to the
    exporter's own totals;
  * a render-time bar hold-out (roadmap 2.8, `bar_does_not_add_up`) through
    the report's own `bars_held_out_sum.held` list of (page, system, staff,
    cell) — the render-time drop is filed after the last parse, so the
    per-subject wrapper cannot attribute it and is not asked to.

Per page it also counts `<accidental>`-bearing notes the exporter wrote
(owned head placed, not in a held bar, its `Q.ACCIDENTAL` row `printed`).

    python3 benchmarks/omr-accidental-2026-09/probe/owner_fate.py \\
        --arm <arm.record.json> --label litolff --out <json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review.rerun import export_with_subjects  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    doc = load_record(a.arm)
    rec = doc["record"]
    xml, report, refusals, _placed = export_with_subjects(doc)
    refused = {}
    for sub, reason in refusals:
        refused.setdefault(sub, reason)
    held = {(h["page"], h["system"], h["staff"], h["cell"])
            for h in (report.get("bars_held_out_sum") or {}).get("held", [])}
    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    acc_v = {v["subject"]: v for v in rec["verdicts"]
             if v["quantity"] == "accidental" and v["id"] not in sup}
    fate = collections.Counter()
    per_page = collections.defaultdict(collections.Counter)
    # ⚠️ PER HEAD, NOT PER OWNER: two glyphs may own one head and the file
    # writes one `<accidental>` per note. A head whose owners disagree is
    # `contradicted` and `apply_printed_accidental` writes nothing on it.
    alts = collections.defaultdict(set)
    for v in rec["verdicts"]:
        if (v["quantity"] == "accidental_owner" and v["id"] not in sup
                and v["outcome"] == "decided"):
            alts[v["value"]].add((v.get("detail") or {}).get("alteration"))
    seen = set()
    head_fate = {}
    for v in rec["verdicts"]:
        if v["quantity"] != "accidental_owner" or v["id"] in sup:
            continue
        page = int(v["subject"].split("/")[1])
        if v["outcome"] != "decided":
            per_page[page][f"abstained:{v['reason']}"] += 1
            continue
        per_page[page]["decided_owners"] += 1
        head = v["value"]
        if head in seen:
            continue
        seen.add(head)
        per_page[page]["heads_owned"] += 1
        _, p, s, st, c, _gi = head.split("/")
        a_row = acc_v.get(head)
        if len(alts[head]) > 1:
            why = "contradicted"
        elif head in refused:
            why = f"head_refused:{refused[head]}"
        elif (int(p), int(s), int(st), int(c)) in held:
            why = "bar_held_out:bar_does_not_add_up"
        elif a_row is None or a_row.get("decider") != "apply_printed_accidental":
            why = "no_printed_row:no_pitch_for_the_consequence"
        elif not (a_row.get("detail") or {}).get("printed"):
            why = "printed_flag_false"
        else:
            why = "written"
        fate[why] += 1
        per_page[page][why] += 1
        head_fate[head] = why
    out = {
        "label": a.label, "arm": a.arm,
        "accidental_elements_in_file": xml.count("<accidental"),
        "written_by_this_join": fate.get("written", 0),
        # the file writes a condensed staff's doubled copy twice (2.1b); the
        # join counts heads, so it must equal elements minus those copies
        "accidental_elements_on_a_doubled_copy": (report.get(
            "accidental_reading") or {}).get("applied_on_a_doubled_copy"),
        "CONTROL_join_equals_file": fate.get("written", 0)
        == xml.count("<accidental") - int((report.get("accidental_reading")
                                           or {}).get(
            "applied_on_a_doubled_copy") or 0),
        "decided_owner_fate": dict(fate),
        "per_page": {str(k): dict(v) for k, v in sorted(per_page.items())},
        "head_fate": head_fate,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in (
        "accidental_elements_in_file", "accidental_elements_on_a_doubled_copy",
        "written_by_this_join",
        "CONTROL_join_equals_file", "decided_owner_fate")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
