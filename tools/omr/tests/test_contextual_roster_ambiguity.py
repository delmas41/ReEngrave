"""The roster must not refill a slot the lexicon cannot settle.

⚠️ THE BUG THIS PINS SHIPPED FOR A DAY AND THE METRIC COULD NOT SEE IT.
`OMR_ROSTER` went default-on 2026-09-05 having measured **exactly 0 edits**, an
argument that was correct — musicdiff does not score `<part-name>` — and that
same blindness hid this: 12 staves across 9 orchestral rows exported as a
SINGER (`Bass voice`) at the foot of the string section, 7 of them caused by
the roster. One was `'mbone Basso'`, a truncated bass TROMBONE.

The mechanism is one line. `contextual` withholds an ambiguous slot from the
score-order prior on purpose — that slot is what the prior exists to decide, and
`score_layouts` documents the same reason for withdrawing a PIN from an
ambiguous alias. The roster refill then put it straight back with
`setdefault`, because a roster name IS a label and the code said so.

⚠️ The exception is not a special case, it is the same rule: **the ambiguity
lives in the LEXICON, not in the reading.** `Basso.` resolves to `Bass voice`
no matter which page it was read from, so a roster inherits the unsettleable
answer rather than settling it. Fed that, no orchestral layout can place the
staff at all, every voter abstains, and `resolve_ambiguous_label` returns None.

Controlled A/B on the affected rows, roster off: support
`Contrabass 0.643 / Cello 0.357` — reproducing `_ambiguous_label_slots`' own
docstring figure to the digit.

A source-level assertion, following the precedent of `test_export.py`'s
anti-drift check on the two MusicXML emitters: the guard is one `continue`
inside a loop in a long function, and a behavioural test would have to stand up
the whole contextual pass to reach it. **Verified to fail when the guard is
removed.**
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from tools.omr import contextual


SOURCE = Path(contextual.__file__).read_text()


def _roster_refill_loop() -> ast.For:
    """The `for slot_index, instrument in roster_by_slot.items():` loop."""
    tree = ast.parse(SOURCE)
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        it = node.iter
        if (isinstance(it, ast.Call)
                and isinstance(it.func, ast.Attribute)
                and it.func.attr == "items"
                and isinstance(it.func.value, ast.Name)
                and it.func.value.id == "roster_by_slot"):
            return node
    raise AssertionError(
        "the roster refill loop over `roster_by_slot` is gone — if it was "
        "renamed, re-point this test rather than deleting it: it guards a "
        "regression the accuracy metric is structurally unable to catch")


def test_the_roster_refill_skips_ambiguous_slots():
    loop = _roster_refill_loop()
    guards = [
        n for n in ast.walk(loop)
        if isinstance(n, ast.If)
        and any(isinstance(c, ast.Name) and c.id == "ambiguous_slots"
                for c in ast.walk(n.test))
        and any(isinstance(b, ast.Continue) for b in n.body)
    ]
    assert guards, (
        "the roster refill no longer skips `ambiguous_slots`. Restoring the "
        "roster name at an ambiguous slot hands the score-order prior the very "
        "reading the prior exists to overturn: measured 2026-09-06 as 7 "
        "orchestral staves exported as `Bass voice`, a singer, including a "
        "truncated bass trombone. The metric cannot see this — the roster "
        "prices at 0 edits because musicdiff does not score <part-name>."
    )


def test_the_ambiguity_is_in_the_lexicon_not_the_reading():
    """The premise of the guard, asserted against the lexicon itself.

    If `Basso` ever became unambiguous this guard would be unnecessary for it —
    so state the dependency rather than leaving it implicit.
    """
    from tools.omr.instruments import candidates_for_alias
    assert len(candidates_for_alias("basso")) >= 2, (
        "`Basso` is no longer ambiguous in the lexicon. That is a change worth "
        "welcoming, but check what else `_ambiguous_label_slots` still needs to "
        "withhold before relaxing anything around it."
    )


def test_the_withholding_and_the_refill_read_the_same_set():
    """Both sites must consult `ambiguous_slots`, or they can drift apart."""
    src = inspect.getsource(contextual.apply_contextual_analysis)
    assert src.count("ambiguous_slots") >= 3, (
        "apply_contextual_analysis should compute `ambiguous_slots`, withhold "
        "them from `fit_labels`, and skip them in the roster refill. Fewer "
        "than three mentions means one of those three is gone."
    )
