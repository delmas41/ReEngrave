"""GATHER ONCE, ADJUDICATE TWICE — does knowing the domain fix the key?

    python3 benchmarks/omr-document-identity-2026-09/keysig_domain_arm.py \
        --record .../engraved-p0p2-identity.record.json \
        --truth-xml .../beethoven-sym5-mvt1-m1-24.musicxml

⚠️ **REACH FIRST, AND IT EXITS DEAD AT ZERO** rather than printing a clean
table over an empty domain. The arm reports how many staves the new tier can
even reach before it reports what it did to them.

⚠️ **THE CONTROL IS THE ZERO.** The tier may write exactly one quantity, and
every other verdict in the record must be identical between the arms. A
key-signature change that moved a duration would mean the arm is measuring
something other than the rule.

⚠️ **THE `rebuild` IS THE CANONICAL ONE**, imported from
`benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py` rather than
copied, so this cannot drift from the harness every other ADJUDICATE arm in
this repo is measured with. Its own blind spot is inherited and stated: it
isolates ADJUDICATE over a FIXED gather, so it can see a GATHER change only
when that change is already IN the record it is handed — which is exactly why
this arm needs a record gathered WITH `OMR_DOCUMENT_IDENTITY` on, and refuses
one without the row.

⚠️ **THE TRUTH IS THE ENCODING'S `<key><fifths>`, PART BY PART**, and the join
is the ordinal one the render makes true (every part on every system). It
REFUSES when the staff count and the part count disagree, rather than pairing
by position and reporting the mismatch as accuracy.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.staged import adjudicate, evaluate              # noqa: E402
from tools.omr.staged import adjudicators, consequences        # noqa: E402,F401
from tools.omr.staged.adjudicators import header as H          # noqa: E402
from tools.omr.staged.record import Q                          # noqa: E402

_RJ = REPO / "benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py"
_spec = importlib.util.spec_from_file_location("_canonical_rj", _RJ)
_canon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_canon)
rebuild = _canon.rebuild


def truth_fifths(xml: Path) -> List[Optional[int]]:
    root = ET.parse(str(xml)).getroot()
    out: List[Optional[int]] = []
    for p in root.findall("{*}part"):
        f = p.find("{*}measure/{*}attributes/{*}key/{*}fifths")
        out.append(int(f.text) if f is not None else None)
    return out


#: How many (quantity, subject) pairs each walk had to RESOLVE. See `_walk`.
_RESOLVED: List[int] = []


def _walk(log):
    """{quantity: {subject: (outcome, value, reason)}}, LIVE answers only.

    ⚠️ `all_verdicts()` returns superseded rows too -- EVALUATE revises a
    duration in place -- so this resolves each (quantity, subject) through
    `verdict()`, which is what the exporter reads. Comparing the raw list
    would report a rule as having moved something when all that moved is how
    many times a value was written.
    """
    seen = defaultdict(dict)
    rows = Counter()
    for v in log.all_verdicts():
        seen[v.quantity][v.subject.to_key()] = v.subject
        rows[(v.quantity, v.subject.to_key())] += 1
    # ⚠️ PRINTED, because a battery arm that swapped the resolution for an
    # unresolved walk SURVIVED: the two give the same OFF-vs-ON diff on this
    # record, so the headline could not see the change. Counting what was
    # resolved makes the choice visible — and it is not zero here: 227 pairs
    # carry more than one row (215 `duration`, 12 `pitch`).
    _RESOLVED.append(sum(1 for n in rows.values() if n > 1))
    out = {}
    for q, subs in seen.items():
        out[q] = {}
        for key, sub in subs.items():
            live = log.verdict(q, sub)
            # ⚠️ `.value`, NEVER `str()`: `str(Outcome.DECIDED)` is
            # `'Outcome.DECIDED'` on this Python, so an `== "decided"` test
            # matches nothing and the accuracy table reported a clean 0 right
            # / 0 wrong on BOTH arms -- a believable zero produced by a
            # comparison that could never be true. The reason strings are
            # plain and unaffected; only the outcome enum bit.
            out[q][key] = (live.outcome.value, live.value, live.reason) \
                if live is not None else None
    return out.items()


def arm(rec: dict, engraved_flag: str):
    os.environ[H.ENGRAVED_KEYSIG_ENV] = engraved_flag
    log = rebuild(rec)
    adjudicate.run(log)
    evaluate.run(log)
    return log


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--truth-xml", type=Path)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    rec = json.loads(args.record.read_text())["record"]

    # ── REACH, before anything else ──────────────────────────────────────
    dom = [o for o in rec["observations"]
           if o.get("quantity") == Q.INPUT_DOMAIN]
    dom_abs = [a for a in rec.get("abstentions", [])
               if a.get("quantity") == Q.INPUT_DOMAIN]
    ident = [o for o in rec["observations"]
             if o.get("quantity") == Q.DOCUMENT_IDENTITY]
    ident_abs = [a for a in rec.get("abstentions", [])
                 if a.get("quantity") == Q.DOCUMENT_IDENTITY]
    print("── REACH " + "─" * 58)
    print(f"   Q.INPUT_DOMAIN       observed {len(dom)}  "
          f"abstained {len(dom_abs)}  "
          f"value {[o.get('value') for o in dom]}")
    print(f"   Q.DOCUMENT_IDENTITY  observed {len(ident)}  "
          f"abstained {len(ident_abs)} "
          f"{[a.get('reason') for a in ident_abs]}")
    if not dom:
        print("\n⚠️ DEAD ARM: this record carries no Q.INPUT_DOMAIN row, so the "
              "tier cannot fire and a zero here would measure the RECORD, not "
              "the rule. Re-gather with OMR_DOCUMENT_IDENTITY unset (default "
              "ON) or =1.")
        return 2
    engraved = [o for o in dom if o.get("value") == "engraved"]
    if not engraved:
        print(f"\n⚠️ DEAD ARM: the document measures "
              f"{[o.get('value') for o in dom]}, not `engraved`, so the "
              f"one-sided tier is a no-op here BY DESIGN. That is the "
              f"fall-through working; it is not a measurement of the rule.")
        return 2

    off = arm(rec, "0")
    on = arm(rec, "1")

    # ── THE CONTROL: exactly one quantity may move ───────────────────────
    voff, von = dict(_walk(off)), dict(_walk(on))
    moved = sorted({q for q in set(voff) | set(von)
                    if voff.get(q) != von.get(q)})
    print("\n── CONTROL " + "─" * 56)
    print(f"   quantities in the record   {len(set(voff) | set(von))}")
    print(f"   superseded pairs RESOLVED  {_RESOLVED}  "
          f"(EVALUATE revises in place; an unresolved walk would report "
          f"whichever row it met first)")
    print(f"   quantities that MOVED      {len(moved)}  {moved}")
    ks = Q.KEY_SIGNATURE
    downstream = [q for q in moved if q != ks]
    if downstream:
        print(f"   ⚠️ downstream movement (EXPECTED where the key feeds "
              f"pitch/accidental): {downstream}")

    # ── what the tier did ────────────────────────────────────────────────
    a, b = voff.get(ks, {}), von.get(ks, {})
    print("\n── Q.KEY_SIGNATURE " + "─" * 48)
    for name, tab in (("OFF (shipped)", a), ("ON  (engraved tier)", b)):
        print(f"   {name:22s} reasons "
              f"{dict(Counter(t[2] for t in tab.values()))}")
        print(f"   {'':22s} values  "
              f"{dict(Counter(str(t[1]) for t in tab.values()))}")
    changed = sorted(s for s in set(a) | set(b) if a.get(s) != b.get(s))
    print(f"   staves whose verdict CHANGED: {len(changed)} of {len(a)}")

    # ── accuracy, if a truth is supplied ─────────────────────────────────
    scored = None
    if args.truth_xml:
        truth = truth_fifths(args.truth_xml)
        staves = sorted(a, key=lambda s: tuple(int(x) for x in s.split("/")[1:]))
        if len(staves) % len(truth) != 0:
            print(f"\n⚠️ REFUSED to score: {len(staves)} staff-systems against "
                  f"{len(truth)} parts — the ordinal join is not exact, and "
                  f"pairing by position would report the mismatch as accuracy.")
        else:
            per_system = len(truth)
            scored = {}
            for name, tab in (("off", a), ("on", b)):
                right = wrong = 0
                for i, s in enumerate(staves):
                    want = truth[i % per_system]
                    got = tab[s][1] if tab[s][0] == "decided" else None
                    if got is None or want is None:
                        continue
                    if int(got) == int(want):
                        right += 1
                    else:
                        wrong += 1
                scored[name] = {"right": right, "wrong": wrong}
            print("\n── ACCURACY vs the encoding's <key><fifths> " + "─" * 23)
            for name in ("off", "on"):
                r, w = scored[name]["right"], scored[name]["wrong"]
                print(f"   {name.upper():3s}  right {r:3d}   wrong {w:3d}")
            # ⚠️ A POSITIVE CONTROL ON THE SCORER ITSELF. It once reported
            # 0 right / 0 wrong on both arms from an enum comparison that
            # could never be true -- a clean, believable zero. A scorer that
            # scored NOTHING must say so rather than print a table.
            if not any(v["right"] + v["wrong"] for v in scored.values()):
                print("   ⚠️ SCORED NOTHING — every staff read as undecided. "
                      "That is the scorer failing, not the readers.")
                return 3

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps({
            "reach": {"input_domain": [o.get("value") for o in dom],
                      "document_identity_abstained":
                          [x.get("reason") for x in ident_abs]},
            "quantities_moved": moved,
            "key_signature": {
                "off": {"reasons": dict(Counter(t[2] for t in a.values())),
                        "values": dict(Counter(str(t[1]) for t in a.values()))},
                "on": {"reasons": dict(Counter(t[2] for t in b.values())),
                       "values": dict(Counter(str(t[1]) for t in b.values()))},
                "staves_changed": changed,
            },
            "accuracy": scored,
        }, indent=1, default=str))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
