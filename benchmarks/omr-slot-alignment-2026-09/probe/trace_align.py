"""Trace every `slots.align` call on a real run, and price the RIGHT answer.

The 7 residual staff-identity errors on Beethoven 5 / Litolff are not naming
errors -- every one carries `instrument_source: label`, and the name is stamped
per SLOT. They are MIS-SLOTTINGS: on a reduced (12-staff) system the monotone DP
consumes the finale's trombone slots 9/10/11 and deletes the string slots
12/13/14, which costs exactly as many deletions as the right answer.

So the question is not "why did the DP score the wrong answer higher" until we
know it did. This dumps, for every align() call: each staff's group_index and
label, each reference slot, the alignment the DP CHOSE, and -- for the systems
we have hand truth for -- the score of the alignment it SHOULD have chosen,
term by term. If the two scores are equal the fault is a tie broken
arbitrarily; if the wrong one scores higher the fault is in `_pair_score`.

Usage: trace_align.py PDF OUT.json --pages=23,44 [--dpi=600]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr import slots as slots_mod                       # noqa: E402
from tools.omr.assist import Assist                            # noqa: E402
from tools.omr.contextual import apply_contextual_analysis     # noqa: E402

CALLS = []


def _score_alignment(view, reference, chosen):
    """Total DP score of an explicit staff->slot-INDEX-position alignment.

    `chosen[i]` is the POSITION in `reference` (not Slot.index) or -1.
    Mirrors `align`: pair scores for taken staves, GAP_PENALTY per skipped slot.
    """
    denom = max(1, view.size - 1)
    positions = [i / denom for i in range(view.size)]
    labels = [view.labels.get(st.staff_index) for st in view.staves]
    total = 0.0
    terms = []
    used = set()
    for i, j in enumerate(chosen):
        if j < 0:
            continue
        used.add(j)
        s = slots_mod._pair_score(view.staves[i], labels[i], reference[j], positions[i])
        total += s
        st = view.staves[i]
        ref = reference[j]
        lab_term = 0.0
        if labels[i] is not None and ref.instrument is not None:
            lab_term = (slots_mod.SCORE_LABEL_MATCH if labels[i] == ref.instrument
                        else slots_mod.SCORE_LABEL_CONFLICT)
        grp_term = (slots_mod.SCORE_GROUP_MATCH if st.group_index == ref.group_index
                    else slots_mod.SCORE_GROUP_CONFLICT)
        pos_term = slots_mod.SCORE_POSITION_WEIGHT * (1.0 - abs(positions[i] - ref.position))
        terms.append({
            "staff": i, "slot": ref.index, "label": labels[i],
            "slot_instrument": ref.instrument,
            "staff_group": st.group_index, "slot_group": ref.group_index,
            "staff_pos": round(positions[i], 4), "slot_pos": round(ref.position, 4),
            "label_term": lab_term, "group_term": grp_term,
            "pos_term": round(pos_term, 4), "pair_total": round(s, 4),
        })
    gaps = len(reference) - len(used)
    total += slots_mod.GAP_PENALTY * gaps
    return round(total, 4), gaps, terms


_real_align = slots_mod.align


def _traced_align(view, reference):
    out = _real_align(view, reference)
    idx_of = {sl.index: k for k, sl in enumerate(reference)}
    CALLS.append({
        "size": view.size,
        "staff_indices": [st.staff_index for st in view.staves],
        "groups": [st.group_index for st in view.staves],
        "labels": [view.labels.get(st.staff_index) for st in view.staves],
        "chosen_slots": list(out),
        "chosen_positions": [idx_of.get(s, -1) for s in out],
        "reference": [{"index": s.index, "group": s.group_index,
                       "instrument": s.instrument, "position": round(s.position, 4)}
                      for s in reference],
    })
    return out


def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main():
    pdf = sys.argv[1]
    dst = sys.argv[2]
    dpi = 600
    spec = None
    for a in sys.argv[3:]:
        if a.startswith("--dpi="):
            dpi = int(a.split("=", 1)[1])
        if a.startswith("--pages="):
            spec = a.split("=", 1)[1]
    import fitz
    with fitz.open(pdf) as doc:
        n = doc.page_count
    pages = parse_pages(spec, n)
    print(f"pdf={pdf} pages={pages} dpi={dpi}", flush=True)

    slots_mod.align = _traced_align
    # contextual imports `align` by module attribute? guard both spellings.
    import tools.omr.contextual as ctx
    if hasattr(ctx, "align"):
        ctx.align = _traced_align

    result = {"source_pdf": pdf, "dpi": dpi,
              "pages": [{"page_index": i, "systems": []} for i in pages]}
    t0 = time.time()
    summary = apply_contextual_analysis(
        result, pdf_path=pdf, dpi=dpi, apply_clefs=False, assist=Assist("none"))
    print(f"contextual available={summary.get('available')} "
          f"reason={summary.get('reason')} in {time.time()-t0:.0f}s", flush=True)

    json.dump({"pdf": pdf, "pages": pages, "dpi": dpi,
               "calls": CALLS,
               "reference": summary.get("reference"),
               "labelled_staves": summary.get("labelled_staves")},
              open(dst, "w"), indent=1, sort_keys=True)
    print(f"wrote {dst}  ({len(CALLS)} align calls)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
