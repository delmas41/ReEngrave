#!/usr/bin/env python3
"""WHY does the roster rule not reach a label? — a funnel, not a rate.

`docs/handoff-2026-09-21-the-fact-sheet.md` §6 ranks re-pricing
`OMR_ROSTER_LABELS` second, on the strength of a "second, independent
instance" of the truncated margin label found on Brahms 1 / Breitkopf: the
horn staff reads `'in C 1 2'` on one system, `'(C)'` / `'(Es)'` on the next
and `'Hr.'` on the third.

⚠️ **THAT IS A CLAIM ABOUT DOMAIN AND IT HAS TO BE TESTED, NOT ASSUMED.**
`work_roster.recover_truncated` matches a TOKEN of the label against the TAIL
of an alias of an instrument the work's roster admits. A survivor carrying no
instrument tail at all is outside the rule by construction — no threshold
reaches it — and saying so is a better result than a forced fit.

So this probe does not report a rate. It reports, for every label in the real
reader corpus, the FIRST GATE that stopped the rule, which is the only form in
which "it does not reach this" is actionable:

    no_work            the corpus row names no catalogued work
    no_roster          the catalog holds no `source_kind: catalog` roster
    roster_incomplete  the parse left `unparsed` fragments (recovery is gated)
    resolved_already   the lexicon answered and the family is admitted
    no_usable_token    every token is a COUNT word, a non-letter, or shorter
                       than MIN_KEPT_LETTERS
    token_is_an_alias  every usable token is a complete alias the lexicon holds
    no_tail_match      a usable token exists and is the tail of no roster alias
    under_fraction     a tail matched but kept < MIN_KEPT_FRACTION of its alias
    ambiguous          two or more roster instruments own a tail
    RECOVERED / DISAMBIGUATED / VETOED

`--focus SUBSTR` prints every distinct label of one source, with its gate.

    python3 benchmarks/omr-roster-truncation-reprice-2026-09/probe_domain.py
    python3 .../probe_domain.py --focus brahms
"""
from __future__ import annotations

import argparse
import collections
import functools
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import instruments                         # noqa: E402
from tools.omr import work_roster as wr                   # noqa: E402

LEXICON = ROOT / "benchmarks" / "omr-lexicon-2026-09"

# `instruments.lookup` costs ~0.6 s on a string it cannot match (it walks ~400
# aliases twice, compiling a regex per alias). One call per DISTINCT string.
lookup = functools.lru_cache(maxsize=None)(instruments.lookup)
roster_of = functools.lru_cache(maxsize=None)(wr.work_roster)


def _gate(text: str, roster) -> tuple[str, str]:
    """(gate, note) — the FIRST thing that stops a recovery for this label.

    Mirrors `recover_truncated`'s own control flow rather than re-deciding:
    every constant is imported, and the outcome is cross-checked against
    `wr.decide` by the caller so this cannot silently diverge from the rule.
    """
    if roster is None:
        return "no_roster", ""
    if not roster.complete:
        return "roster_incomplete", ""
    known = wr._known_aliases()
    toks = wr._tokens(text)
    usable = [t for t in toks if len(t) >= wr.MIN_KEPT_LETTERS]
    if not usable:
        return "no_usable_token", f"tokens={toks}"
    free = [t for t in usable if t not in known]
    if not free:
        return "token_is_an_alias", f"tokens={usable}"
    hits: dict[str, tuple[str, str]] = {}
    near = []
    for token in free:
        for alias, inst in wr._roster_aliases(roster):
            if len(token) >= len(alias) or not alias.endswith(token):
                continue
            if len(token) / len(alias) < wr.MIN_KEPT_FRACTION:
                near.append(f"{token!r} keeps "
                            f"{len(token)/len(alias):.2f} of {alias!r}")
                continue
            hits.setdefault(inst.name, (token, alias))
    if not hits:
        if near:
            return "under_fraction", "; ".join(sorted(set(near))[:3])
        return "no_tail_match", f"tokens={free}"
    if len(hits) > 1:
        return "ambiguous", ", ".join(sorted(hits))
    name, (token, alias) = next(iter(hits.items()))
    return "would_recover", f"{token!r} is a tail of {alias!r} -> {name}"


def classify(text: str, work_id, roster):
    hit = lookup(text)
    d = wr.decide(text, roster, hit=hit)
    if d.kind == "recovered":
        return "RECOVERED", f"{d.before or 'None'} -> {d.match.instrument.name}"
    if d.kind == "disambiguated":
        return "DISAMBIGUATED", f"{d.before} -> {d.match.instrument.name}"
    if d.kind == "vetoed":
        return "VETOED", f"{d.before} -> None"
    # unchanged: say WHY.
    if work_id is None:
        return "no_work", ""
    if roster is None:
        return "no_roster", ""
    if hit is not None and (not roster.complete
                            or roster.admits_family(hit.instrument.family)):
        return "resolved_already", hit.instrument.name
    gate, note = _gate(text, roster)
    if gate == "would_recover":
        # Unreachable if `decide` and `_gate` agree; kept so a divergence is
        # LOUD rather than silently absorbed into a bucket.
        return "DIVERGED", note
    return gate, note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", default=None)
    ap.add_argument("--out", default=str(BENCH / "out" / "domain.json"))
    args = ap.parse_args()

    pages = json.loads((LEXICON / "pages.json").read_text())
    labels = json.loads((LEXICON / "labels.json").read_text())
    work_of = {p["id"]: wr.work_id_for_pdf(p["pdf"]) for p in pages}

    rows = []
    for rec in labels:
        wid = work_of.get(rec["source"])
        ros = roster_of(wid) if wid else None
        gate, note = classify(rec["text"], wid, ros)
        rows.append({**rec, "work_id": wid, "gate": gate, "note": note})

    by_gate = collections.Counter(r["gate"] for r in rows)
    print(f"{len(rows)} labels, {len(pages)} sources\n")
    print("  gate                  n   share")
    for gate, n in by_gate.most_common():
        print(f"  {gate:20} {n:4d}  {n/len(rows):6.1%}")
    diverged = [r for r in rows if r["gate"] == "DIVERGED"]
    if diverged:
        print(f"\n(!) {len(diverged)} DIVERGED (the funnel and the rule disagree)")
        for r in diverged[:10]:
            print("   ", r["text"], r["note"])

    if args.focus:
        f = [r for r in rows if args.focus.lower() in r["source"].lower()]
        print(f"\n--- {args.focus}: {len(f)} labels, "
              f"{len({r['text'] for r in f})} distinct ---")
        seen: dict[str, dict] = {}
        cnt = collections.Counter(r["text"] for r in f)
        for r in f:
            seen.setdefault(r["text"], r)
        for text, n in cnt.most_common():
            r = seen[text]
            print(f"  {n:3d}x {text!r:28} {r['gate']:18} {r['note']}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(
        {"n_labels": len(rows), "by_gate": dict(by_gate), "rows": rows},
        indent=1))
    print(f"\nwrote {args.out}")
    return 2 if diverged else 0


if __name__ == "__main__":
    raise SystemExit(main())
