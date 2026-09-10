"""A default-ON flag must not be switchable OFF by a typo.

⚠️⚠️ THE DIRECTION OF THE TEST HAS TO FOLLOW THE DEFAULT, AND FOUR SHIPPED
FLAGS HAD IT BACKWARDS. `_carry_meter`'s rule — *"anything but an explicit 1
is off"* — is right for a default-OFF mechanism: a typo must not switch a
document ONTO something whose hazard is a whole wrong movement. Written as an
allow-list (`in ("1", "true", "yes", "on")`) it is exactly wrong for a
default-ON one, because then `OMR_X=`, `OMR_X=yess` or `OMR_X=ON!` all read as
false and SILENTLY RESTORE the bug the default exists to fix.

`OMR_SLOT_STITCH`, `OMR_MOVEMENT_REFERENCE`, `OMR_ROSTER` and
`OMR_LABEL_MERGE_QUALITY` all shipped that way. Found while flipping
`OMR_METER_SEGMENTS` on, by a test written for the flip that failed on its
first run.

⚠️ THE LIST IS DERIVED FROM THE SOURCE, NEVER WRITTEN HERE. A hand list is
the thing this repository has been bitten by repeatedly: it can only carry a
flag someone remembered to add, and a new default-ON flag is exactly what
would be forgotten.
"""

import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
TRUEY = {"1", "true", "yes", "on"}
#: ⚠️ `""` is admitted as an off word but never required. A `"1"`-defaulted
#: flag lists it (`OMR_LEFT_EDGE_SPLIT`); a `""`-defaulted one must NOT, or
#: its own default would read as off.
FALSEY = {"0", "", "false", "no", "off"}


def _string_set(node):
    """The literal strings a comparison's right-hand side names, or None."""
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        vals = {e.value for e in node.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        return vals or None
    return None


def default_on_flags():
    """Every `os.environ.get(<FLAG>, <default>)` compared to a literal set.

    Yields (file, lineno, flag, default, op, members, on).

    ⚠️ `on` IS DERIVED BY EVALUATING THE PREDICATE ON ITS OWN DEFAULT, not by
    guessing from the default string. `OMR_CHOIR_GROUPING` and
    `OMR_BRACKET_COLUMNS` are default-ON and spell it `get(FLAG, "") not in
    {"0", ...}` — an EMPTY default that means on. A first version classified
    those two as default-off because `""` is not a truthy word, and reported
    them as faults. The predicate is the only thing that knows.

    ⚠️ THE FLAG NAME MAY BE A MODULE CONSTANT. `OMR_METER_SEGMENTS` is read
    through `METER_SEGMENTS_ENV`, and a scan that only understood string
    literals silently skipped it — which is how a derived check ends up
    excluding the very flag it was written for.
    """
    for f in sorted((ROOT / "tools").rglob("*.py")):
        if "/tests/" in str(f):
            continue
        try:
            tree = ast.parse(f.read_text())
        except (SyntaxError, UnicodeDecodeError):
            continue
        consts = {}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                consts[node.targets[0].id] = node.value.value
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare) or len(node.ops) != 1:
                continue
            if not isinstance(node.ops[0], (ast.In, ast.NotIn)):
                continue
            members = _string_set(node.comparators[0])
            if not members or not (members <= TRUEY or members <= FALSEY):
                continue
            call = node.left
            while (isinstance(call, ast.Call)
                   and isinstance(call.func, ast.Attribute)
                   and call.func.attr in ("strip", "lower", "upper", "casefold")):
                call = call.func.value
            if not (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "get"
                    and isinstance(call.func.value, ast.Attribute)
                    and call.func.value.attr == "environ"):
                continue
            if not call.args:
                continue
            head = call.args[0]
            if isinstance(head, ast.Constant) and isinstance(head.value, str):
                flag = head.value
            elif isinstance(head, ast.Name) and head.id in consts:
                flag = consts[head.id]
            else:
                continue
            if not flag.startswith("OMR_"):
                continue
            d = call.args[1] if len(call.args) > 1 else None
            if d is None:
                default = ""
            elif isinstance(d, ast.Constant) and isinstance(d.value, str):
                default = d.value
            else:
                continue
            is_in = isinstance(node.ops[0], ast.In)
            probe = default.strip().lower()
            on = (probe in members) if is_in else (probe not in members)
            yield (f.relative_to(ROOT), node.lineno, flag, default,
                   "In" if is_in else "NotIn", members, on)


class TestADefaultOnFlagFailsSafe(unittest.TestCase):

    def setUp(self):
        self.rows = list(default_on_flags())

    def test_the_scan_finds_something(self):
        """⚠️ The positive control. A derived check that silently matches
        nothing passes forever — this repo has shipped exactly that twice."""
        self.assertGreater(len(self.rows), 6, "the AST scan matched too little")
        flags = {r[2] for r in self.rows}
        for expect in ("OMR_SLOT_STITCH", "OMR_METER_SEGMENTS", "OMR_ROSTER"):
            self.assertIn(expect, flags)

    def test_every_default_ON_flag_uses_a_deny_list(self):
        bad = []
        for path, line, flag, default, op, members, on in self.rows:
            if not on:
                continue                      # default-OFF: allow-list is right
            if op == "NotIn" and members <= FALSEY:
                continue                      # correct: only an off word disables
            bad.append(f"{path}:{line} {flag} (default {default!r}) "
                       f"uses {op} {sorted(members)} — a typo or an empty "
                       f"value would turn it OFF")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_every_default_OFF_flag_uses_an_allow_list(self):
        """The mirror, and it is not symmetric decoration: a default-OFF flag
        written as a deny-list would be turned ON by a typo, which is the
        hazard `_carry_meter`'s docstring is about."""
        bad = []
        for path, line, flag, default, op, members, on in self.rows:
            if on:
                continue
            if op == "In" and members <= TRUEY:
                continue
            bad.append(f"{path}:{line} {flag} (default {default!r}) "
                       f"uses {op} {sorted(members)} — a typo would turn it ON")
        self.assertEqual(bad, [], "\n".join(bad))


if __name__ == "__main__":
    unittest.main()
