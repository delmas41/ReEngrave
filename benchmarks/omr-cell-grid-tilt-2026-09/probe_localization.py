"""Does localizing a cell's grid onto its own ink reproduce the displacement
the page probe measured by hand?

`benchmarks/omr-cell-grid-tilt-2026-09/FINDINGS.md` §2 traced the printed line
y at 21 x-positions across 7 flagged staves and read the residual off the
profile. This runs the pipeline's own localization
(`measure_extractor._cell_line_offset`) on the same cells and compares. A
mechanism that cannot recover a displacement someone already measured by hand
is not worth a benchmark run.

    python3 benchmarks/omr-cell-grid-tilt-2026-09/probe_localization.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr import measure_extractor as _me  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

_me.PAD_ABOVE_STAFF_LINES = 5.0
_me.PAD_BELOW_STAFF_LINES = 5.0

# (edition path under library/, page0, system, staff, measure, name,
#  hand-measured displacement in staff spaces from FINDINGS §1)
CASES = [
    ("editions/dvorak/symphony-9-op95/"
     "dvorak--symphony-9-op95--simrock-1894--imslp405834.pdf",
     7, 0, 4, 12, "dvorak9-p8-sys0-s4-m12", -0.55),
    ("editions/mahler/symphony-1-gmw-11/"
     "mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf",
     2, 0, 7, 5, "mahler1-p3-sys0-s7-m5", +0.36),
    ("editions/mahler/symphony-1-gmw-11/"
     "mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf",
     3, 0, 0, 9, "mahler1-p4-sys0-s0-m9", +0.25),
    ("editions/mahler/symphony-1-gmw-11/"
     "mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf",
     3, 0, 1, 9, "mahler1-p4-sys0-s1-m9", +0.33),
    ("editions/brahms/symphony-1-op68/"
     "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
     1, 1, 21, 6, "brahms1-p2-sys1-s21-m6", -0.40),
    ("editions/rimsky-korsakov/scheherazade-op35/"
     "rimsky-korsakov--scheherazade-op35--eulenburg--imslp1010338.pdf",
     3, 0, 3, 0, "schehe-p4-sys0-s3-m0", +0.28),
    ("editions/beethoven/symphony-5-op67/"
     "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf",
     47, 0, 14, 0, "beet5hr-p48-sys0-s14-m0", -0.11),
    # ⚠️ The two SILENT wrong labels (FINDINGS §3) — the cells this work exists
    # to have prevented, so "it would have caught them" is run here rather than
    # inferred from the seven above. `brahms1-p2-sys1-s20-m6` is the one that
    # forced CELL_LINE_MIN_ROWS_COVERED: it fits correctly but covers only 4 of
    # 5 rows, because that staff's own MODELED spacing is irregular.
    ("editions/brahms/symphony-1-op68/"
     "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
     1, 1, 20, 6, "brahms1-p2-sys1-s20-m6 [silent]", -0.40),
    ("editions/debussy/la-mer-cd-111/"
     "debussy--la-mer-cd-111--durand-fils--imslp15420.pdf",
     4, 0, 2, 0, "lamer-p5-sys0-s2-m0 [silent]", -0.45),
]


def main() -> int:
    lib = library_root()
    cache: dict = {}
    rows = []
    for rel, page0, sysi, sti, mi, name, hand in CASES:
        key = (rel, page0)
        if key not in cache:
            img = render_page(lib / rel, page0, dpi=600)
            pws = detect_staves(img)
            _me.detect_barlines(pws)
            cache[key] = (img, pws, _me.extract_measures(pws))
        img, pws, cells = cache[key]

        cell = next((c for c in cells if c.system_index == sysi
                     and c.staff_index == sti and c.measure_index == mi), None)
        staff = next((s for s in pws.staves if s.staff_index == sti), None)
        row = {"name": name, "hand_spaces": hand}
        if staff is None or cell is None:
            row["error"] = "staff or cell not found"
            rows.append(row)
            continue
        x0, _, x1, _ = cell.bbox_page_px
        spacing = float(staff.line_spacing_px)
        row["spacing_px"] = round(spacing, 2)
        row["wander_px"] = staff.line_wander_px
        got = _me._cell_line_offset(pws, staff, x0, x1)
        if got is None:
            row["measured_spaces"] = None
            row["verdict"] = "abstained"
        else:
            offset, prov = got
            row.update(prov)
            row["measured_spaces"] = prov["offset_spaces"]
            row["delta_vs_hand"] = round(prov["offset_spaces"] - hand, 3)
            row["verdict"] = ("agrees"
                              if abs(prov["offset_spaces"] - hand) <= 0.12
                              else "DISAGREES")
        rows.append(row)

    print(f"{'cell':34s} {'hand':>6s} {'fitted':>7s} {'delta':>6s} "
          f"{'rows':>5s} {'cover':>6s}  verdict")
    for r in rows:
        m = r.get("measured_spaces")
        d = r.get("delta_vs_hand")
        m_s = "  —  " if m is None else f"{m:+7.3f}"
        d_s = "  —  " if d is None else f"{d:+6.3f}"
        print(f"{r['name']:34s} {r['hand_spaces']:+6.2f} {m_s:>7s} {d_s:>6s} "
              f"{str(r.get('rows_covered', '—')):>5s} "
              f"{str(r.get('min_row_coverage', '—')):>6s}  "
              f"{r.get('verdict', r.get('error'))}")

    out = BENCH / "probe_localization.json"
    out.write_text(json.dumps(rows, indent=1) + "\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
