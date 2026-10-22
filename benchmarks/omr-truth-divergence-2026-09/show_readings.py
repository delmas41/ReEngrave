"""Print what the pipeline read, per staff, for a human to look at.

Optimised for reading, not for parsing: one block per row, staves in printed
order, with the PROVENANCE of every instrument name beside it — because
`label` (the page said so), `roster` (the document said so) and `score_order`
(the prior said so) are very different warrants for the same string, and a name
that is plausible but wrong for its position is exactly what this is for.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

VOICES = {"Bass voice", "Alto", "Soprano", "Tenor", "Baritone"}


def block(path: Path) -> str:
    doc = json.loads(path.read_text())
    ctx = doc.get("contextual") or {}
    roster = ctx.get("roster") or {}
    text_by_ord = {e["ordinal"]: e.get("text") for e in
                   (roster.get("entries") or [])}

    out = [f"### {path.name.replace('.omr.json', '')}"]
    rt = roster.get("n_staves")
    out.append(f"    layout={ctx.get('layout')}  "
               f"named={ctx.get('layout_named_slots')}/{len(ctx.get('reference') or [])}  "
               f"roster: {roster.get('named')}/{rt} staves named "
               f"(page {roster.get('page_index')}, system {roster.get('system_index')})")
    out.append("")
    out.append("    sys  idx  slot  instrument        via            clef      "
               "key   time    bars   margin text")
    for pg in doc["pages"]:
        for si, sy in enumerate(pg["systems"]):
            for st in sy["staves"]:
                ks = st.get("key_signature") or {}
                sh, fl = ks.get("sharps", 0), ks.get("flats", 0)
                key = f"{sh}#" if sh else (f"{fl}b" if fl else "-")
                ts = (st.get("time_signature") or {}).get("raw") or "-"
                inst = st.get("instrument")
                idx = st.get("staff_index")
                flag = "  <-- VOICE" if inst in VOICES else ""
                txt = text_by_ord.get(idx, "")
                out.append(
                    f"    {si:3d}  {idx:3d}  {str(st.get('slot_index')):>4s}  "
                    f"{str(inst):17s} {str(st.get('instrument_source')):14s} "
                    f"{str(st.get('clef')):9s} {key:5s} {ts:7s} "
                    f"{str(st.get('n_measures')):>4s}   {txt!r}{flag}")
    return "\n".join(out)


def main() -> int:
    pats = sys.argv[1:] or ["*"]
    paths = []
    for p in pats:
        paths += sorted((HERE / "readings").glob(f"*{p}*.omr.json"))
    if not paths:
        print("no readings matched", file=sys.stderr)
        return 2
    for p in dict.fromkeys(paths):
        print(block(p))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
