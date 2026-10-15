"""ROADMAP 2.134 -- 2.96's held-bar dump on the 20261014-night records.

PATH: STAGED, EXPORT-only (record loaded once via record_io.load_record, exported
with today's exporter, never re-gathered). `held_funnel_2_96.py` reused WHOLE
(its `enrich`, and 2.22's `dump`). The ONE adaptation (2.117): the exporter's
`_bar_holds_out` is now called for every bar that does not add up, and a bar
with a certain prefix/suffix is then written PARTIAL (blue notes + red `unread`
bracket) and is NOT counted in `bars_held_out_sum`. `dump` captures both, so its
own control (captured == held_sum - doubled) reads FAIL here by design; this
script replaces it with a control that can fail:

    captured == held_sum - doubled + partial_written        (bar for bar)
    cells with a `report` row (the exporter's `held` list)  == held_sum - doubled
    cells without one                                       == partial_bars.written

and tags each captured bar `kind` = "held" | "partial" (the split `bars_add_up`
counts apart). Nothing in tools/ is changed.

    python3 .../held_funnel_2_134.py <record.json> --label L --out-dir D
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import held_funnel_2_96 as F          # noqa: E402  (also puts ROOT on sys.path)
import held_funnel_mvt_2_22 as H      # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    stash = {}
    orig = RR.export_with_subjects

    def spy(result, *args, **kw):
        out = orig(result, *args, **kw)
        stash["rep"] = out[1]
        return out
    RR.export_with_subjects = spy

    F.say(f"loading {a.record}")
    doc = load_record(a.record)
    F.say("loaded")
    H.dump(doc, a.label, "own", out_dir, False)     # its own control is superseded below
    gc.collect()
    rep = stash["rep"]
    held_rep = rep["bars_held_out_sum"]
    part_rep = rep.get("partial_bars") or {}
    p_in = out_dir / f"{a.label}-own.held.json"
    d = json.load(open(p_in))
    n_held = held_rep["bars"] - held_rep["bars_on_a_doubled_staff"]
    n_part = int(part_rep.get("written", 0))
    kinds = {"held": 0, "partial": 0}
    for b in d["bars"]:
        b["kind"] = "held" if b.get("report") else "partial"
        kinds[b["kind"]] += 1
    ctl = {"held_sum": held_rep["bars"], "doubled": held_rep["bars_on_a_doubled_staff"],
           "of_bars_with_events": held_rep["of_bars_with_events"],
           "partial_written": n_part, "captured": len(d["bars"]), "kinds": kinds,
           "stay_held_by_reason": part_rep.get("stay_held_by_reason"),
           "PASS": (len(d["bars"]) == n_held + n_part
                    and kinds["held"] == n_held and kinds["partial"] == n_part)}
    d["control_2_134"] = ctl
    json.dump(d, open(p_in, "w"), default=str)
    F.say(f"control 2.134: {ctl}")
    F.enrich(doc, p_in, out_dir / f"{a.label}-2.134.held.json")
    return 0 if ctl["PASS"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
