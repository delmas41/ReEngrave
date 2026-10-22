"""Helpers the derived checks used to define once each.

`capture`, `inventory`, `trace` and `wiring` each carried a byte-for-byte copy
of the KNOWN_GAPS bookkeeping (`_gap_key`, `unaccounted`, `stale_gaps`) closing
over their own module-level table; `capture` and `gather_coverage` each carried
the same two AST one-liners (`_q_name`, `_attr_tail`). They differed only in
the table, so they take it as a parameter here and each check module keeps a
thin same-named wrapper (its callers and tests import those names).

What is NOT here, on purpose (the bodies genuinely differ):

* `_quantities` -- `capture` resolves one node (a `Q.X` or a bound name),
  `gather_coverage` resolves the first three args plus a `quantity=` keyword,
  `wiring` the first three args through `_q_literal`, and `health` collects
  every `Q.X` anywhere under a node. Four different questions.
* `gather_coverage.unaccounted` -- legacy event keys in neither of two tables,
  returns a dict; not the KNOWN_GAPS prefix test.

This module is an instrument, not a stage (`reach.NOT_A_STAGE`). It imports
nothing from the package so any check may import it without a cycle.
"""
from __future__ import annotations

import ast
from typing import Iterable, List, Optional, Sequence


def gap_key(problem: str, known_gaps: Iterable[str]) -> Optional[str]:
    """Which KNOWN_GAPS entry a problem line belongs to, by prefix (first
    entry in the table's order that matches)."""
    for key in known_gaps:
        if problem.startswith(key):
            return key
    return None


def unaccounted(problems: Sequence[str],
                known_gaps: Iterable[str]) -> List[str]:
    """Problems on no KNOWN_GAPS entry. These are what `--check` fails on."""
    keys = list(known_gaps)
    return [p for p in problems if gap_key(p, keys) is None]


def stale_gaps(problems: Sequence[str], known_gaps: Iterable[str],
               *, ordered: bool = False) -> List[str]:
    """KNOWN_GAPS entries nothing reports any more. A CLOSED gap must LEAVE.

    Sorted by default; `ordered=True` keeps the table's own order (which is
    what `trace` always returned).
    """
    keys = list(known_gaps)
    hit = {gap_key(p, keys) for p in problems}
    stale = [k for k in keys if k not in hit]
    return stale if ordered else sorted(stale)


def q_name(node: ast.AST) -> Optional[str]:
    """`Q.GLYPH_BOX` -> "GLYPH_BOX". Anything else -> None."""
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "Q"):
        return node.attr
    return None


def attr_tail(node: ast.AST) -> Optional[str]:
    """`READERS.DETECTOR` -> "DETECTOR"; `ABSTAIN.NO_INK` -> "NO_INK"."""
    return node.attr if isinstance(node, ast.Attribute) else None
