"""Find staves whose identity rests on an alias the lexicon cannot settle.

Free — it reads stored transcriptions and asks the lexicon, so it costs no
pipeline run and reaches every row the corpus has.

The fault it is looking for: `instruments.AMBIGUOUS_ALIASES` marks a handful of
words (`basso`, `basse`, `altos`, `tp`, `cor`, `tr bas`) as unsettleable by
vocabulary, to be decided by POSITION in `score_layouts.resolve_ambiguous_label`.
When that resolver abstains, the lexicon's first listed reading survives — and
for `basso`/`basse` that reading is a SINGER at the foot of an orchestral score.

⚠️ A hit is not automatically a defect. `basso` at the bottom of a string
section is the contrabass and `Bass voice` there is wrong; the same alias under
a choral system is right. What the audit reports is the pairing — the alias, the
resolution count, and the instrument that survived — for a human to read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.instruments import (AMBIGUOUS_ALIASES,  # noqa: E402
                                   candidates_for_alias, lookup)

VOICE_FAMILY = "voice"


def audit(path: Path) -> dict:
    doc = json.loads(path.read_text())
    ctx = doc.get("contextual") or {}
    roster = ctx.get("roster") or {}
    entries = roster.get("entries") or []

    staves = [st for pg in doc["pages"] for sy in pg["systems"]
              for st in sy["staves"]]
    inst_by_ordinal: dict[int, str] = {}
    # The roster's ordinal is its position within the roster SYSTEM, and
    # `staff_index` is preserved across the five-line filter, so the two share a
    # space only when the roster came off a system this run also transcribed.
    for i, st in enumerate(staves):
        inst_by_ordinal[st.get("staff_index", i)] = st.get("instrument")

    hits = []
    for e in entries:
        m = lookup(e.get("text", ""))
        alias = getattr(m, "alias", None) if m else None
        if not alias or alias not in AMBIGUOUS_ALIASES:
            continue
        cands = [c.name for c in candidates_for_alias(alias)]
        final = inst_by_ordinal.get(e["ordinal"])
        hits.append({
            "ordinal": e["ordinal"],
            "text": e.get("text"),
            "alias": alias,
            "candidates": cands,
            "final_instrument": final,
            "took_first_listed": bool(final and cands and final == cands[0]),
            "is_voice_on_orchestral": bool(
                final and any(c.name == final and c.family == VOICE_FAMILY
                              for c in candidates_for_alias(alias))),
        })
    return {
        "row": path.name,
        "ambiguous_labels_resolved": ctx.get("ambiguous_labels_resolved"),
        "layout": ctx.get("layout"),
        "layout_named_slots": ctx.get("layout_named_slots"),
        "n_slots": len(ctx.get("reference") or []),
        "hits": hits,
    }


def main() -> int:
    readings = sorted((HERE / "readings").glob("*.omr.json"))
    if not readings:
        print("REFUSING: no stored readings — run run_corpus.py first",
              file=sys.stderr)
        return 2
    print(f"auditing {len(readings)} readings\n")
    n_hit = n_voice = 0
    out = []
    for p in readings:
        rec = audit(p)
        out.append(rec)
        if not rec["hits"]:
            continue
        n_hit += 1
        print(f"{rec['row']}")
        print(f"   layout={rec['layout']} named={rec['layout_named_slots']}"
              f"/{rec['n_slots']} resolved={rec['ambiguous_labels_resolved']}")
        for h in rec["hits"]:
            flag = "  <-- VOICE ON AN ORCHESTRAL SCORE" if h[
                "is_voice_on_orchestral"] else ""
            n_voice += bool(h["is_voice_on_orchestral"])
            print(f"   ord {h['ordinal']:3d} {h['text']!r:28s} alias={h['alias']:8s}"
                  f" -> {h['final_instrument']}  of {h['candidates']}{flag}")
        print()
    print(f"rows with an ambiguous-alias staff: {n_hit}/{len(readings)}")
    print(f"staves reading as a VOICE on an orchestral score: {n_voice}")
    (HERE / "ambiguous_audit.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
