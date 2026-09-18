"""HOW WIDE IS EVERY `notehead*` BOX ON THE PLATE, in staff spaces?

The crop pass measured, against the print, that a floor at **width < 1.0 staff
spaces** catches 39 of the 46 non-noteheads it found at a cost of 0 of 63 real
stems -- and said in terms that the figure is measured ONLY on heads the
rejection census already abstains on. This asks the other side: what does that
floor do to the population the pipeline reads CORRECTLY?

⚠️ TWO RULERS, BOTH REPORTED, BECAUSE THE TWO BOX CONVENTIONS DIFFER.
`glyph_box.value[1:5]` is a CANONICAL **width-box** `(x, y, w, h)`;
`glyph_box.detail.bbox_page_px` is a PAGE **corner-box** `(x0, y0, x1, y1)`.
The handoff records a session losing time to exactly that confusion, and a
fixture at the origin cannot tell them apart. So each box is measured twice --
canonical `w / cell_staff_space`, and page `(x1 - x0) / staff_spacing` -- and
the agreement between the two is itself an output. A disagreement is the
finding; it is not averaged away.

⚠️ THE PAGE RULER IS THE ONE TO QUOTE. `cell_staff_space` is a property of the
cell's own rescaling and `_upscale_to_canonical` scales a too-wide cell by
WIDTH rather than by the staff span, so the canonical ruler inherits whatever
that did. The page ruler divides two page-pixel quantities and is the honest
one. Both are printed; where they disagree the page ruler wins and the
disagreement is reported.

⚠️ NOTHING IS CLASSIFIED HERE. A width is a ruler reading, and this probe
never says "that is not a notehead" -- only "that box is N spaces wide". The
print said what the narrow ones are, on 180 boxes, in the crop pass.

Writes one row per notehead box so every downstream table joins on the subject
address rather than on a box (the page-pixel frame error a sibling probe
already paid for).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402


def cell_of(subject: str) -> str:
    """`glyph/P/S/T/C/G` -> `cell/P/S/T/C`."""
    p = subject.split("/")
    return "cell/" + "/".join(p[1:5])


def staff_of(subject: str) -> str:
    p = subject.split("/")
    return "staff/" + "/".join(p[1:4])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    cell_space: dict[str, float] = {}
    staff_space: dict[str, float] = {}
    heads: dict[str, dict] = {}

    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "cell_staff_space":
            v = o.get("value")
            if isinstance(v, (int, float)) and v > 0:
                cell_space[o["subject"]] = float(v)
        elif q == "staff_spacing":
            v = o.get("value")
            if isinstance(v, (int, float)) and v > 0:
                staff_space[o["subject"]] = float(v)
        elif q == "glyph_box":
            v = o.get("value")
            if not (isinstance(v, list) and len(v) == 5):
                continue
            cls = str(v[0])
            if not cls.startswith("notehead"):
                continue
            d = o.get("detail") or {}
            heads[o["subject"]] = {
                "subject": o["subject"],
                "cls": cls,
                "conf": o.get("score"),
                "canon": [float(x) for x in v[1:]],
                "page": d.get("bbox_page_px"),
            }

    verdict: dict[str, tuple[str, str | None]] = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") != "stem_direction":
            continue
        verdict[v["subject"]] = (str(v.get("outcome")), v.get("reason"))

    rows = []
    no_cell_space = no_page_box = no_staff_space = 0
    for s, h in sorted(heads.items()):
        ck, sk = cell_of(s), staff_of(s)
        cs = cell_space.get(ck)
        ss = staff_space.get(sk)
        pb = h["page"]
        w_canon = h_canon = None
        if cs:
            w_canon = h["canon"][2] / cs
            h_canon = h["canon"][3] / cs
        else:
            no_cell_space += 1
        w_page = h_page = None
        if isinstance(pb, list) and len(pb) == 4 and ss:
            w_page = (float(pb[2]) - float(pb[0])) / ss
            h_page = (float(pb[3]) - float(pb[1])) / ss
        else:
            if not (isinstance(pb, list) and len(pb) == 4):
                no_page_box += 1
            elif not ss:
                no_staff_space += 1
        out, reason = verdict.get(s, ("(no verdict)", None))
        rows.append({
            "subject": s, "cls": h["cls"], "conf": h["conf"],
            "w_canon": w_canon, "h_canon": h_canon,
            "w_page": w_page, "h_page": h_page,
            "outcome": out, "reason": reason,
            "cell_staff_space": cs, "staff_spacing": ss,
        })

    # ⚠️ REACH FIRST. A probe that measured nothing must say so and DIE, not
    # report a clean zero -- the shape every sibling arm in this thread pays.
    n_both = sum(1 for r in rows if r["w_canon"] is not None
                 and r["w_page"] is not None)
    print(f"{a.label}: {len(rows)} notehead boxes; "
          f"{n_both} measurable by BOTH rulers")
    print(f"  no cell_staff_space {no_cell_space}   "
          f"no page bbox {no_page_box}   no staff_spacing {no_staff_space}")
    if not rows or n_both == 0:
        print("DEAD: no notehead box is measurable by both rulers",
              file=sys.stderr)
        return 2

    Path(a.json).write_text(json.dumps(
        {"label": a.label, "record": a.record, "n": len(rows),
         "n_both_rulers": n_both, "rows": rows}, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
