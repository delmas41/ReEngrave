#!/usr/bin/env python3
"""REACH BEFORE ACCURACY — what a per-document language signal can even touch.

Three questions, in the order that decides whether the rest is worth writing:

1. **Reach.** How many labels are ambiguous *and* sit on a document whose
   language its other labels reveal? A lever that reaches nothing is a lever
   this project has bought several times already (the written-range veto has
   never fired on a scan; `clef_correction`'s fill reaches 8.6% of staves).
2. **Determinability.** Do a document's unambiguous labels AGREE about the
   tradition, and how often are they genuinely mixed?
3. **What changes.** Which labels a language reading re-decides, per document.

Runs off the committed 1422-label margin dump — no transcription, no weights,
no venv, no network.

    python3 benchmarks/omr-score-language-2026-09/probe/measure_reach.py
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import instruments as I            # noqa: E402
from tools.omr import score_language as L         # noqa: E402

LEXICON = ROOT / "benchmarks/omr-lexicon-2026-09"


def load_documents(path: Path) -> dict[str, list[str]]:
    """`source` -> its labels. `source` IS the document — one PDF, one reader."""
    raw = json.loads(path.read_text())
    if raw and isinstance(raw[0], str):
        return {path.stem: list(raw)}
    docs: dict[str, list[str]] = collections.defaultdict(list)
    for rec in raw:
        docs[rec["source"]].append(rec["text"])
    return dict(docs)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", type=Path, default=LEXICON / "labels.json")
    ap.add_argument("--json", type=Path, help="write the per-document rows")
    ap.add_argument("--head-fallback", type=int, default=0, metavar="N",
                    help="ESCALATION, cheapest first — where the margin labels "
                         "cast fewer than MIN_DIAGNOSTIC_VOTES, read the left "
                         "margin of the document's first N pages instead. "
                         "⚠️ Only as a fallback: a modern edition's front "
                         "matter is in the EDITOR's language, and Handel's "
                         "lead-sheet contents page casts 9 English votes off "
                         "the word `Chorus:` while the score's own margins say "
                         "Italian.")
    ap.add_argument("--pages", type=Path, default=LEXICON / "pages.json")
    args = ap.parse_args(argv)

    docs = load_documents(args.labels)
    head: dict[str, list[str]] = {}
    if args.head_fallback:
        sys.path.insert(0, str(BENCH / "probe"))
        from language_from_head import head_strings     # noqa: PLC0415
        for row in json.loads(args.pages.read_text()):
            pdf = Path(row["pdf"])
            if pdf.is_file():
                head[row["id"]] = head_strings(
                    pdf, list(range(args.head_fallback)))
    rows = []
    total = amb = amb_reachable = changed = 0
    change_detail: collections.Counter = collections.Counter()

    print(f"corpus: {args.labels.name}  documents={len(docs)}  "
          f"labels={sum(len(v) for v in docs.values())}\n")

    hdr = (f"{'document':34s} {'lbl':>5s} {'diag':>5s} {'lang':>5s} "
           f"{'share':>6s} {'mix':>4s} {'amb':>4s} {'chg':>4s}")
    print(hdr)
    print("-" * len(hdr))

    for src in sorted(docs):
        labels = docs[src]
        reading = L.detect(labels)
        escalated = False
        if reading.language is None and head.get(src):
            head_reading = L.detect(head[src])
            if head_reading.language is not None:
                reading, escalated = head_reading, True
        reading, decisions = L.resolve_document(labels, reading)
        # Ambiguity is read off the alias each decision already carries, so the
        # expensive `lookup` runs once per distinct string for the whole row.
        n_amb = sum(1 for d in decisions
                    if d.alias is not None and len(L.candidates(d.alias)) > 1)
        n_chg = sum(1 for d in decisions if d.changed)
        for d in decisions:
            if d.changed:
                change_detail[(src, d.alias, d.lexicon, d.language)] += 1

        total += len(labels)
        amb += n_amb
        if reading.language is not None:
            amb_reachable += n_amb
        changed += n_chg

        mix = "yes" if reading.is_mixed else "-"
        lang = (reading.language or "--") + ("*" if escalated else "")
        print(f"{src:34s} {len(labels):5d} {reading.n_diagnostic:5d} "
              f"{lang:>6s} {reading.share:6.2f} "
              f"{mix:>4s} {n_amb:4d} {n_chg:4d}")
        rows.append({
            "document": src, "labels": len(labels),
            "diagnostic_votes": reading.n_diagnostic, "votes": reading.votes,
            "language": reading.language, "share": round(reading.share, 4),
            "mixed": reading.is_mixed, "ambiguous_labels": n_amb,
            "changed": n_chg, "from_head_pages": escalated,
        })

    print("-" * len(hdr))
    named = [r for r in rows if r["language"]]
    mixed = [r for r in rows if r["mixed"]]
    print(f"\nDETERMINABILITY  language read on {len(named)} of {len(rows)} "
          f"documents ({len(named)/len(rows):.3f})")
    print(f"                 votes genuinely MIXED on {len(mixed)} of {len(rows)} "
          f"({len(mixed)/len(rows):.3f})")
    for r in mixed:
        v = {k: n for k, n in r["votes"].items() if n}
        print(f"                   {r['document']:32s} {v}  -> {r['language']}")

    print(f"\nREACH            ambiguous labels          {amb:5d} of {total} "
          f"({amb/total:.4f})")
    print(f"                 …on a language-read doc   {amb_reachable:5d} "
          f"({amb_reachable/total:.4f} of corpus, "
          f"{amb_reachable/amb if amb else 0:.4f} of ambiguous)")
    print(f"                 …the reading RE-DECIDES   {changed:5d} "
          f"({changed/total:.4f} of corpus)")

    if change_detail:
        print("\nWHAT CHANGES")
        for (src, alias, lex, lang), n in change_detail.most_common():
            print(f"  {n:4d}  {src:32s} {alias!r:10s} {lex} -> {lang}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"corpus": str(args.labels), "documents": rows,
             "totals": {"labels": total, "ambiguous": amb,
                        "ambiguous_on_read_document": amb_reachable,
                        "changed": changed},
             "changes": [{"document": s, "alias": a, "lexicon": lx,
                          "language": lg, "n": n}
                         for (s, a, lx, lg), n in change_detail.most_common()]},
            indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
