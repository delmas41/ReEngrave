#!/usr/bin/env python3
"""THE GATE — restore each fault, prove the test sees it, then prove it passes.

A green suite is not evidence that a test guards anything. Every assertion in
`tools/omr/tests/test_score_language.py` that guards a real fault is exercised
here in BOTH directions: with the fault restored it must FAIL, with the shipped
table it must PASS. Five of the six faults below were live in this module's own
first revision and were caught by the corpus, not by review.

The mutation is applied to the imported module's tables at runtime, so nothing
on disk moves and the test functions run exactly as pytest runs them.

    python3 benchmarks/omr-score-language-2026-09/probe/red_check.py

Exits non-zero if any fault is invisible to its test.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr import score_language as L                      # noqa: E402
from tools.omr.tests import test_score_language as T           # noqa: E402


def _tag(alias: str, languages: set[str]) -> None:
    L._ALIAS_LANGUAGES[alias] = frozenset(languages)


#: name -> (mutate, test callable). Each mutate() restores ONE historical fault.
FAULTS = [
    ("tp re-admitted to LANGUAGE_READINGS (double-counts the clef channel)",
     lambda: L.LANGUAGE_READINGS.update(
         {"tp": {"it": "Timpani", "en": "Trumpet"}}),
     T.test_language_never_decides_an_alias_the_lexicon_declared_ambiguous),

    ("`flutes` tagged English-only (voted EN on Ravel's French head page)",
     lambda: _tag("flutes", {"en"}),
     T.test_a_spelling_two_traditions_share_casts_no_vote),

    ("`basse` tagged French-only (12 FR votes off Mahler's German `Bässe`)",
     lambda: _tag("basse", {"fr"}),
     T.test_the_german_plural_of_bass_is_not_a_french_vote),

    ("`trpt` tagged English (8 EN votes off a BREITKOPF edition)",
     lambda: _tag("trpt", {"en"}),
     T.test_a_latin_consonant_skeleton_carries_no_language),

    ("`basso` given a language reading (would break Handel's one page)",
     lambda: L.LANGUAGE_READINGS.update(
         {"basso": {"it": "Contrabass", "en": "Bass voice"}}),
     T.test_handel_is_untouched_in_every_tradition),

    ("the share gate removed (a pool of four traditions gets an answer)",
     lambda: setattr(L, "MIN_SHARE", 0.0),
     T.test_a_pool_of_many_documents_gets_no_language),

    ("`tb` tagged Italian — the decided alias voting for its own verdict, "
     "which is the evidence cycle §4.1 refuses",
     lambda: _tag("tb", {"it"}),
     T.test_a_decided_alias_never_votes_for_the_language_that_decides_it),
]


def main() -> int:
    saved = (copy.deepcopy(L.LANGUAGE_READINGS),
             copy.deepcopy(L._ALIAS_LANGUAGES), L.MIN_SHARE, L.MIN_DIAGNOSTIC_VOTES)
    failures = []

    for label, mutate, test in FAULTS:
        # shipped table: must PASS
        try:
            test()
            green = True
        except Exception as exc:                 # noqa: BLE001
            green, green_exc = False, exc

        mutate()
        try:
            test()
            red = False
        except Exception:                        # noqa: BLE001 - expected
            red = True
        finally:
            (L.LANGUAGE_READINGS.clear(), L.LANGUAGE_READINGS.update(saved[0]),
             L._ALIAS_LANGUAGES.clear(), L._ALIAS_LANGUAGES.update(saved[1]))
            L.MIN_SHARE, L.MIN_DIAGNOSTIC_VOTES = saved[2], saved[3]

        ok = green and red
        print(f"[{'ok ' if ok else 'BAD'}] {label}")
        print(f"        shipped: {'pass' if green else 'FAIL'}   "
              f"fault restored: {'FAIL (seen)' if red else 'pass (INVISIBLE)'}")
        if not green:
            print(f"        shipped arm raised: {green_exc!r}")
        if not ok:
            failures.append(label)

    print()
    if failures:
        print(f"GATE FAILED — {len(failures)} fault(s) invisible to their test")
        return 1
    print(f"GATE PASSED — {len(FAULTS)} faults, each seen by its test, "
          "each absent under the shipped tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
