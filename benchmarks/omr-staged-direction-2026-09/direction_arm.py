"""The direction arm: REACH FIRST, then the numbers, on ONE gather.

⚠️⚠️ REACH IS PRINTED BEFORE ANYTHING ELSE AND IT IS NOT A FORMALITY. A change
that moves nothing because it is INERT and one that moves nothing because the
page holds nothing to move are the same number, and this family has two
separate ways of being empty:

  * the CV proposed no word-shaped ink (the page prints nothing readable), and
  * no OCR rung exists on this machine (`.venv-surya` and Tesseract both
    absent), in which case EVERY page reads zero and the zero means nothing.

So the reach block names the readers that ran, and the arm exits non-zero
declaring itself DEAD when no rung ran -- a dead instrument must not read as a
clean result.

    python3 benchmarks/omr-staged-direction-2026-09/direction_arm.py staged.json
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged.record import ABSTAIN, Q                # noqa: E402
from tools.omr.staged.export import Record                    # noqa: E402


def main(path: str) -> int:
    result = json.loads(pathlib.Path(path).read_text())
    rec = Record(result)

    obs = rec.obs_of(Q.DIRECTION_WORD)
    refs = [a for a in result["record"].get("abstentions", [])
            if a.get("quantity") == Q.DIRECTION_WORD]
    by_reason = collections.Counter(str(a.get("reason")) for a in refs)

    # ⚠️ A CANDIDATE is a piece of word-shaped ink; the per-CELL rows are the
    # page-state partition and are NOT candidates. They are told apart by the
    # subject kind, because a candidate is filed on a GLYPH and a page state
    # on a CELL -- counting the two together would report every bar of the
    # page as a refused word.
    cand_refusals = [a for a in refs
                     if str(a.get("subject", "")).startswith("glyph/")]
    readers = set()
    for a in refs:
        for r in (a.get("detail") or {}).get("readers") or ():
            readers.add(str(r))
    for o in obs:
        for r in (o.get("detail") or {}).get("readers_run") or ():
            readers.add(str(r))

    n_candidates = len(obs) + len(cand_refusals)
    blind = by_reason.get(ABSTAIN.READER_UNAVAILABLE, 0)

    print("=" * 72)
    print(f"REACH: {n_candidates} word-shaped candidates, "
          f"{len(obs)} accepted by the lexicon")
    print(f"  rungs that ran  : {sorted(readers) or 'NONE'}")
    print(f"  refusal reasons : {dict(by_reason)}")
    prov = result.get("provenance") or {}
    print(f"  provenance      : {prov.get('commit')}, "
          f"dirty={prov.get('dirty')}")
    print("=" * 72)

    if blind:
        print("DEAD INSTRUMENT: at least one page had NO OCR rung "
              f"({blind} `reader_unavailable` rows). Every figure below is "
              "a property of this machine, not of the document.")
        return 2
    if n_candidates == 0:
        print("DEAD INSTRUMENT: the CV proposed no candidate anywhere. "
              "Nothing here says anything about the rule.")
        return 2

    # ── what was accepted ────────────────────────────────────────────────
    print("\nACCEPTED WORDS")
    texts = collections.Counter(str(o["value"]) for o in obs)
    cats = collections.Counter(
        str((o.get("detail") or {}).get("category")) for o in obs)
    place = collections.Counter(
        str((o.get("detail") or {}).get("placement")) for o in obs)
    rungs = collections.Counter(
        str((o.get("detail") or {}).get("winning_reader")) for o in obs)
    pages = collections.Counter(
        str(o["subject"]).split("/")[1] for o in obs)
    print(f"  texts     : {texts.most_common()}")
    print(f"  category  : {dict(cats)}")
    # ⚠️ `above` / `below` is the only placement split there is, and the
    # MARGIN question is answered BY CONSTRUCTION rather than by a count:
    # `direction_text.find_candidates` clamps every band to the staff's own
    # `x_start..x_end` because "left of `x_start` is the margin, where the
    # instrument name is printed -- a reader let loose there returns
    # `Contrabassoon` as a direction". So no candidate is ever in a margin.
    print(f"  placement : {dict(place)}   (margin: 0 by construction)")
    print(f"  won by    : {dict(rungs)}")
    print(f"  per page  : {dict(pages)}")

    # ── the decision ─────────────────────────────────────────────────────
    print("\nDECISION")
    vs = list(rec.verdicts_of(Q.DIRECTION))
    out = collections.Counter(
        (v["outcome"], str(v["reason"])) for v in vs)
    words = sum(len(v["value"] or ()) for v in vs
                if v["outcome"] == "decided")
    print(f"  {len(vs)} verdicts, {words} words decided")
    for (outcome, reason), n in sorted(out.items(), key=lambda kv: -kv[1]):
        print(f"    {outcome:10s} {reason:24s} {n}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(64)
    raise SystemExit(main(sys.argv[1]))
