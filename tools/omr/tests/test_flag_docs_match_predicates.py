"""The flag table (docs/flags-2026-09.md since 2026-09-22; CLAUDE.md before) must agree with the PREDICATES they describe.

⚠️⚠️ **WHY THIS EXISTS: A FLAG FLIPPED TO DEFAULT-ON AND SIX LEDGERS KEPT
SAYING OFF, AND THE TABLE IS THE FIRST THING AN AGENT READS.** `OMR_INK` went
default-ON on 2026-09-17 (Sean's call, correctly re-spelled as a deny-list per
CLAUDE.md's own *"A flag's OFF test must follow its DEFAULT"*), and both
CLAUDE.md tables still read `` `0` (off) `` — one of them arguing *"the
standing argument for the flag being off until a consumer exists"*. On
2026-09-17 that cost a session a killed 15-minute gather: it read the table,
concluded a handoff's command was missing `OMR_INK=1`, and relaunched a run
that had been correct. `fixed-then-kept-open-in-prose` inverted —
**flipped-then-kept-off-in-prose** — and worse than a stale claim about the
past, because a wrong DEFAULT reads as a fact about the run you are about to
make.

⚠️ **The instrument already existed and nothing compared it to the prose.**
`test_flag_default_direction.default_on_flags()` derives every flag, its
default and its list kind from the AST and settles the direction by
EVALUATING the predicate on its own default. That roster is imported here,
never restated: two copies of a derived list is the drift this file is about.

**TWO TIERS, because the repairs differ and one must be able to pass.**

* a **CONTRADICTION** — a flag the tables document with the WRONG default — is
  a hard failure. There are zero once `OMR_INK` is corrected, which is what
  lets this be a gate at all. ⚠️ A check that can never pass cannot be one:
  this file's sibling `no_producer --check` is recorded in CLAUDE.md as
  exiting 1 while reporting its findings as `RECORDED`, and is therefore
  unusable as a gate.
* a flag **absent from both tables** is recorded in `UNDOCUMENTED`, with its
  reason, so the check passes while NAMING the gap. Documenting one must
  REMOVE it from that list -- the `KNOWN_GAPS` discipline, enforced below, so
  the list describes the tables rather than their history.
"""

import ast
import importlib.util
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
CLAUDE_MD = ROOT / "docs" / "flags-2026-09.md"   # the flag table since 2026-09-22


def _default_on_flags():
    """Import the SIBLING guard's derivation rather than re-deriving it."""
    path = pathlib.Path(__file__).resolve().parent / \
        "test_flag_default_direction.py"
    spec = importlib.util.spec_from_file_location("_fdd", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.default_on_flags()


#: Flags in NO CLAUDE.md table, with the reason each is out. ⚠️ These are
#: reasons a gap EXISTS, never reasons one is acceptable -- the rule
#: `staged/capture.py` states for its own `KNOWN_GAPS`.
UNDOCUMENTED = {
    # Empty since 2026-09-22: docs/flags-2026-09.md gives EVERY flag a row
    # (roadmap 0.2). A flag added without a row fails
    # `test_undocumented_is_exact_no_stale_entries` below, which is the point.
}


def table_defaults(text):
    """{flag: [default-column text, ...]} over every markdown table row.

    The DEFAULT COLUMN only -- the second cell. The prose bodies say many
    things about many flags and are not a claim about this run's default;
    the column is.
    """
    out = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 4:
            continue
        m = re.search(r"`(OMR_[A-Z_0-9]+)`", cells[1])
        if m:
            out.setdefault(m.group(1), []).append(cells[2])
    return out


def states_on(cell):
    """Does this default-column cell claim the flag is ON by default?

    ⚠️ DELIBERATELY NARROW, and it ABSTAINS rather than guessing. The column
    is written half a dozen ways (`` `1` (on) ``, `` **`1` (on)** ``,
    `` `0` off (default) ``, `` `move` (on) ``, `` **`1` ON since
    2026-09-08** ``), so this reads the first backticked token and the words
    `on`/`off`, and returns None when the two disagree or neither appears --
    a cell it cannot read must not be scored as either.
    """
    low = cell.lower()
    tok = re.search(r"`([^`]+)`", low)
    token = tok.group(1).strip() if tok else ""
    by_token = {"1": True, "0": False, "on": True, "off": False,
                "move": True}.get(token)
    has_on = re.search(r"\bon\b", low) is not None
    has_off = re.search(r"\boff\b", low) is not None
    by_word = True if (has_on and not has_off) else \
        (False if (has_off and not has_on) else None)
    if by_token is None:
        return by_word
    if by_word is None or by_word == by_token:
        return by_token
    return None                       # the cell contradicts itself: abstain


def contradictions(text=None):
    """(flag, predicate_on, cell) for every table row stating the wrong default."""
    text = CLAUDE_MD.read_text() if text is None else text
    tables = table_defaults(text)
    predicate = {}
    for _f, _ln, flag, _d, _op, _m, on in _default_on_flags():
        predicate.setdefault(flag, set()).add(on)
    bad = []
    for flag, ons in predicate.items():
        if len(ons) != 1:             # two read sites disagreeing is the
            continue                  # SIBLING guard's business, not ours
        on = next(iter(ons))
        for cell in tables.get(flag, []):
            said = states_on(cell)
            if said is not None and said != on:
                bad.append((flag, on, cell))
    return bad


class TestTheTablesMatchThePredicates(unittest.TestCase):

    def test_no_table_row_states_the_wrong_default(self):
        bad = contradictions()
        self.assertEqual(bad, [], "\n".join(
            f"CLAUDE.md says {flag} defaults "
            f"{'OFF' if on else 'ON'} — the predicate says "
            f"{'ON' if on else 'OFF'}: {cell!r}" for flag, on, cell in bad))

    def test_the_check_can_fail(self):
        """⚠️ THE POSITIVE CONTROL. A check of prose against code is exactly
        the kind that passes vacuously -- this file's own subject matter is a
        claim nobody re-asked. Inject a row stating the opposite of a
        predicate and require it to be caught."""
        flag, on = next((f, o) for _a, _b, f, _c, _d, _e, o
                        in _default_on_flags())
        wrong = "`0` (off)" if on else "`1` (on)"
        injected = CLAUDE_MD.read_text() + \
            f"\n\n| `{flag}` | {wrong} | an injected row |\n"
        found = [c for c in contradictions(injected) if c[0] == flag]
        self.assertTrue(found, f"the check did not catch a planted {flag} row")

    def test_undocumented_is_exact_no_stale_entries(self):
        """⚠️ A FLAG THAT GAINS A TABLE ROW MUST LEAVE `UNDOCUMENTED`, or the
        list stops describing the tables and starts describing their
        history -- `export_coverage`'s stale-entry rule, one family over."""
        tables = table_defaults(CLAUDE_MD.read_text())
        documented = {f for f in tables
                      if any(states_on(c) is not None for c in tables[f])}
        stale = sorted(set(UNDOCUMENTED) & documented)
        self.assertEqual(stale, [], f"documented now; remove from "
                                    f"UNDOCUMENTED: {stale}")
        seen = {flag for _a, _b, flag, _c, _d, _e, _f in _default_on_flags()}
        missing = sorted(f for f in seen
                         if f not in documented and f not in UNDOCUMENTED)
        self.assertEqual(missing, [], f"undocumented and unaccounted: "
                                      f"{missing}")

    def test_it_reads_a_real_roster(self):
        """A derivation over an EMPTY roster would pass everything."""
        seen = {flag for _a, _b, flag, _c, _d, _e, _f in _default_on_flags()}
        self.assertGreater(len(seen), 15, "the flag roster came back tiny — "
                                          "the sibling derivation is broken, "
                                          "and this check is then vacuous")
        self.assertIn("OMR_INK", seen)

    def test_states_on_abstains_rather_than_guessing(self):
        self.assertIs(states_on("`1` (on)"), True)
        self.assertIs(states_on("**`1` ON since 2026-09-08 (Sean's call)**"),
                      True)
        self.assertIs(states_on("`0` off (default) → staged pipeline only"),
                      False)
        self.assertIs(states_on("`move` (on)"), True)
        self.assertIsNone(states_on("_(unset)_"))
        # ⚠️ TOKEN BEATS AMBIGUOUS WORDS, because the first backticked token
        # in a default column IS the default value; only a token that
        # CONTRADICTS the words abstains.
        self.assertIs(states_on("`1` on, or off when unset"), True)
        self.assertIsNone(states_on("`0` (on)"))


if __name__ == "__main__":
    unittest.main()
