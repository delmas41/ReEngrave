"""The DYNAMICS half alone, in seconds: re-run ONLY `Q.DYNAMIC`.

⚠️ WHY THIS IS SOUND AND NOT A SHORTCUT. `adjudicate_dynamic` reads exactly two
things: `Q.DYNAMIC_LETTER` rows (GATHER, in the saved record) and
`Q.GLYPH_OWNER` VERDICTS (ADJUDICATE, also in the saved record). Nothing it
reads depends on any other decision being re-run, so replaying the saved
ownership verdicts into the rebuilt Log and running that one decision gives
byte-for-byte what a full re-adjudication would — for this decision.

⚠️ ITS CONTROL IS THE BASE ARM ITSELF. With the repair switched off, every
`Q.DYNAMIC` verdict must match the one the pipeline wrote. If it does not, the
replay is wrong and nothing below means anything — so that comparison is
printed FIRST and exits non-zero.

⚠️ IT PRICES ONLY THE DYNAMICS. `export_only_arm.py` prices the notes;
`ab_arm.py` does both at once and is the slow instrument.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate as A                 # noqa: E402
from tools.omr.staged import adjudicators                    # noqa: E402,F401
from tools.omr.staged.adjudicators import text as TEXT       # noqa: E402
from tools.omr.staged.record import Log, Q, Subject          # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab_arm import rebuild                                    # noqa: E402


def replay_owner_verdicts(log, rec):
    """Put the saved `Q.GLYPH_OWNER` verdicts back, so the one decision under
    test sees exactly the ownership the pipeline decided."""
    n = 0
    for v in rec["verdicts"]:
        if v["quantity"] != Q.GLYPH_OWNER:
            continue
        log._vrd[v["id"]] = _VerdictShim(v)
        log._index(v["quantity"], Subject.from_key(v["subject"]), v["id"])
        n += 1
    return n


class _VerdictShim:
    """Just enough of a Verdict for `Evidence.verdict` to read it."""

    def __init__(self, v):
        self.id = v["id"]
        self.subject = Subject.from_key(v["subject"])
        self.quantity = v["quantity"]
        self.outcome = v["outcome"]
        self.value = v["value"]
        self.reason = v["reason"]
        self.detail = v.get("detail") or {}
        self.candidates = ()
        self.basis = ()
        self.supersedes = v.get("supersedes")
        self.margin = v.get("margin")
        self.decider = v.get("decider")
        self.considered = tuple(v.get("considered") or ())
        self.used = tuple(v.get("used") or ())
        self.missing = tuple(v.get("missing") or ())
        self.declined = tuple(v.get("declined") or ())
        self.excluded = tuple(v.get("excluded") or ())
        self.correlated = ()


def words_of(log):
    out = collections.Counter()
    per_cell = {}
    for v in log._vrd.values():
        if v.quantity != Q.DYNAMIC or v.outcome != "decided":
            continue
        if isinstance(v.value, list):
            per_cell[v.subject.to_key()] = list(v.value)
            for w in v.value:
                out[w] += 1
    return out, per_cell


def run(rec, *, relocate):
    real = TEXT.is_relocated_copy
    if relocate:
        TEXT.is_relocated_copy = lambda *a, **k: False
    try:
        log = rebuild(rec)
        replay_owner_verdicts(log, rec)
        log.freeze()
        A.run(log, order=(Q.DYNAMIC,))
        return log
    finally:
        TEXT.is_relocated_copy = real


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rec = json.load(open(args.record))["record"]

    base = run(rec, relocate=True)
    base_words, base_cells = words_of(base)

    saved = {}
    for v in rec["verdicts"]:
        if v["quantity"] == Q.DYNAMIC and v["outcome"] == "decided" \
                and isinstance(v["value"], list):
            saved[v["subject"]] = list(v["value"])
    agree = sum(1 for k in set(saved) | set(base_cells)
                if saved.get(k) == base_cells.get(k))
    total = len(set(saved) | set(base_cells))
    print(f"CONTROL — base arm vs the pipeline's own Q.DYNAMIC verdicts: "
          f"{agree} of {total} identical")
    if agree != total:
        print("⚠️ THE REPLAY DOES NOT REPRODUCE THE PIPELINE. Nothing below "
              "means anything.")
        for k in sorted(set(saved) | set(base_cells)):
            if saved.get(k) != base_cells.get(k):
                print(f"   {k}: saved={saved.get(k)} replay={base_cells.get(k)}")
                break
        return 1

    fix = run(rec, relocate=False)
    fix_words, _ = words_of(fix)

    print("\nspelled dynamic words (the page prints only `ff`, per Sean):")
    print(f"  {'word':<8} {'base':>6} {'fix':>6}")
    for w in sorted(set(base_words) | set(fix_words),
                    key=lambda w: -(base_words[w] + fix_words[w])):
        print(f"  {w:<8} {base_words[w]:>6} {fix_words[w]:>6}")

    def dropped(log):
        n = 0
        for v in log._vrd.values():
            if v.quantity == Q.DYNAMIC:
                n += int((v.detail or {}).get("letters_dropped_as_duplicate", 0))
        return n
    print(f"\nletters refused as this staff's own duplicate: "
          f"base {dropped(base)}  fix {dropped(fix)}")

    (out / "dynamics-summary.json").write_text(json.dumps(
        {"control": {"agree": agree, "total": total},
         "base": dict(base_words), "fix": dict(fix_words),
         "letters_dropped_as_duplicate": {"base": dropped(base),
                                          "fix": dropped(fix)}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
