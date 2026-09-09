"""What a `works.json` `staves` entry may carry — DERIVED, not typed out.

⚠️ READ `merge_additions.ARITY_FIELDS`' HISTORY FIRST. This module is the
SECOND pass over that fault, and it exists because the first pass repaired the
premise by writing a new list rather than by removing the need for one.

`e9c82c82` fixed the refusal that had made a correct `lines: 1` map
un-mergeable, validated the two fields' values, wrote the projection once, and
added `arity_problems` — which is the strongest thing in this whole area and is
untouched here: an allow-list can only ever carry a field that is PRESENT,
while asking `run_ledger.expand_lineup` at write time catches one that is
ABSENT, which is the failure that actually cost a page. What it did not do is
stop the allow-list being hand-written, and on the day it landed that list was
already incomplete: `beethoven-sym5-mvt1-984073-p1` carries `clef` and `key`
on all twelve staves and was still refused, so the only tool permitted to write
`works.json` still could not re-merge a sixth of the file it had written.

So the shape is now derived and declared instead of listed, in the shape of
`export_coverage`'s repair and of `class_aliases.py`:

  REQUIRED          `name` + `parts`, the structural invariants.
  arity_fields()    DERIVED BY AST from the consumer that reads them —
                    `run_ledger.expand_lineup`, the function that turns a
                    lineup entry into the slots the arity gate counts. Nobody
                    types these; teaching that function a new key adds it here.
  RECORDED_ONLY     hand-read facts committed to the file that no consumer
                    reads YET, each with a reason, the way
                    `class_aliases.COARSER_THAN_CANONICAL` is.
  VALIDATORS        ⚠️ ALLOWED IS NOT UNCHECKED — `e9c82c82`'s rule, kept and
                    extended to every optional key. `unvalidated()` fails on
                    any allowed key with no validator, so DERIVING a new field
                    cannot smuggle in an unchecked one.

`unaccounted()` returns every key on a committed row in none of the three, so a
new hand-read fact is a failing test rather than a silent drop.

⚠️ AND THE DERIVATION RAISES RATHER THAN RETURNING NOTHING. An empty derivation
is not a smaller schema, it is a silent one: the allow-list narrows back to
`name`+`parts`, `project()` starts dropping `lines: 1` again and `problems()`
starts refusing the committed file — both original faults, back at once,
wearing the old behaviour's face.

⚠️ WHAT THIS MODULE DELIBERATELY DOES NOT DO is derive the allow-list from
`works.json` itself. That would make the anti-drift test vacuous — the file
would be proving its own shape — and it would bless a typo the moment one was
committed. See `test_staves_schema.py`.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

SCAN = Path(__file__).resolve().parent
ROOT = SCAN.parents[1]
WORKS = SCAN / "works.json"

#: The two structural keys.  `name` is the PRINTED staff name; `parts` the
#: reference part indices it carries.  ⚠️ `parts` is ORDERED and the order is
#: not a storage convention — `page_normalise.normalise` does
#: `keep = parts[idx[0]]`, so the first index decides which reference part the
#: merged staff IS.  Nothing here may sort it.  See `merge_additions`.
REQUIRED: tuple[str, ...] = ("name", "parts")

#: The consumer whose reads ARE the arity schema.  One (file, function) pair:
#: `expand_lineup` is the function that turns a hand-read lineup entry into the
#: slots the ledger's arity gate counts, and its own docstring calls them "two
#: declared shapes, both facts about the ENGRAVING".  `arity_problems` already
#: calls that function rather than recomputing its answer; this reads the same
#: function for the same reason, one level up.
CONSUMER = ("benchmarks/omr-symbol-ledger-2026-09/run_ledger.py",
            "expand_lineup")

#: Hand-read facts a committed row carries that NO consumer reads yet.  Each
#: needs a reason, and `unaccounted()` fails on any key that is neither derived
#: nor listed here — so this table can go stale in only one direction, and that
#: direction is a failing test.
RECORDED_ONLY: dict[str, str] = {
    "clef": "the clef PRINTED on this staff, hand-read off the scan. It is "
            "there for `scan_eval`'s second governing rule — *THE PAGE IS THE "
            "TRUTH, NOT THE FILE* — which says in as many words that this is "
            "*\"why `works.json` carries HAND-READ clef and key columns rather "
            "than taking them from the reference\"*: the Beethoven print gives "
            "Trombe and Timpani no key signature and the Gradus file gives "
            "them three flats. Carried by `beethoven-sym5-mvt1-984073-p1` for "
            "all twelve staves; the same twelve readings are ALSO a Python "
            "literal in `benchmarks/omr-first-run-2026-08/eval_first_run.py` "
            "(STAVES), which scores the pipeline's clef against them. So no "
            "consumer reads the COLUMN yet — what reads it is a duplicate.",
    "key": "the key signature PRINTED on this staff as a fifths count "
           "(-3 = three flats), hand-read off the scan and therefore "
           "TRANSPOSING: the Clarinetti in B row is -1 on a page whose "
           "concert key is -3, which is the whole point of reading it off the "
           "page. Same row, same rule and same non-consumer as `clef`.",
}

#: ⚠️ ALLOWED IS NOT UNCHECKED — `e9c82c82`'s rule, and its reasoning is
#: unchanged: a typo'd `lines` silently changes how many parts the row is
#: expected to emit, which is exactly the failure the field exists to prevent.
#: Extended to every optional key, because a DERIVED allow-list would otherwise
#: let a newly-read field in unchecked. Each validator returns a complaint or
#: None, and must REFUSE bad input rather than raise on it — `int()` on an
#: arbitrary value raises, and these are reached from the merge step's own
#: error path.
def _v_lines(v) -> str | None:
    if v not in (1, 5) or isinstance(v, bool):
        return (f"`lines` is {v!r} — works.json models 1 (a percussion rule) "
                f"or 5 (an ordinary staff); anything else needs a decision, "
                f"not a default")
    return None


def _v_printed_staves(v) -> str | None:
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        return f"`printed_staves` is {v!r}, not an integer >= 1"
    return None


def _v_clef(v) -> str | None:
    if not isinstance(v, str) or not v.strip():
        return f"`clef` is {v!r}, not a printed clef name"
    return None


def _v_key(v) -> str | None:
    if not isinstance(v, int) or isinstance(v, bool) or not -7 <= v <= 7:
        return (f"`key` is {v!r} — a fifths count, -7..7, as PRINTED on this "
                f"staff (transposing, not concert)")
    return None


VALIDATORS = {"lines": _v_lines, "printed_staves": _v_printed_staves,
              "clef": _v_clef, "key": _v_key}

#: `lines: 5` and `printed_staves: 1` are the defaults and every merged row
#: omits them; writing them would make this writer's output differ from the
#: file it appends to.  ⚠️ A `RECORDED_ONLY` fact has no default — an absent
#: `clef` means "not read", not "treble".
DEFAULTS = {"lines": 5, "printed_staves": 1}


class SchemaUnreadable(RuntimeError):
    """The consumer this schema is derived FROM could not be read."""


def _consumer_path() -> Path:
    return ROOT / CONSUMER[0]


def keys_read_by(source: str, function: str) -> frozenset[str]:
    """Every string key `function` reads off a plain local, by AST.

    Collects the literal of `<name>.get("k")` and `<name>["k"]` where the
    receiver is a bare Name — inside `expand_lineup` that is the loop variable
    and nothing else.  Chained receivers (`row.get("page", {}).get("x")`) are
    deliberately not collected: those are keys of some OTHER object.

    Split out from `arity_fields` so the derivation itself is testable on a
    source string, rather than only on the one file it happens to be pointed
    at — a derivation nobody can run backwards is a hand list with extra steps.
    """
    fn = next((n for n in ast.walk(ast.parse(source))
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == function), None)
    if fn is None:
        return frozenset()
    found: set[str] = set()
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            found.add(node.args[0].value)
        elif (isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)):
            found.add(node.slice.value)
    return frozenset(found)


def arity_fields() -> tuple[str, ...]:
    """The optional keys `CONSUMER` actually reads — `merge_additions`'
    `ARITY_FIELDS`, derived.  `REQUIRED` is removed: those are structural and
    are checked separately.

    ⚠️ RAISES rather than degrading to an empty tuple.  See the module
    docstring: an empty derivation is a silent schema, not a smaller one.
    """
    path = _consumer_path()
    if not path.is_file():
        raise SchemaUnreadable(
            f"{CONSUMER[0]} is not on disk — the arity fields are derived from "
            f"it and cannot be guessed")
    keys = keys_read_by(path.read_text(), CONSUMER[1]) - set(REQUIRED)
    if not keys:
        raise SchemaUnreadable(
            f"{CONSUMER[0]}::{CONSUMER[1]} reads no entry key — either it was "
            f"renamed, or the derivation no longer matches how it reads one. "
            f"Fix the pointer; do NOT fall back to name+parts.")
    return tuple(sorted(keys))


def optional_keys() -> tuple[str, ...]:
    """Every non-structural key, derived first and declared second."""
    return arity_fields() + tuple(sorted(RECORDED_ONLY))


def allowed_keys() -> frozenset[str]:
    return frozenset(REQUIRED) | frozenset(optional_keys())


def unvalidated() -> list[str]:
    """Allowed keys with no validator — `class_aliases.unaccounted()`'s shape.

    ⚠️ THE POINT IS THE DERIVED HALF. A hand list and its validators are edited
    together; a DERIVED list can grow a field on its own, and without this that
    field would be allowed into hand-verified truth unchecked.
    """
    return sorted(set(optional_keys()) - set(VALIDATORS))


def project(entry: dict) -> tuple[dict, list[str]]:
    """One `staves` entry as `works.json` should hold it, plus what was DROPPED.

    ⚠️ THE DROPPED LIST IS THE HALF THAT WAS MISSING.  The UI's own state
    carries bookkeeping (`proposed`, `verdict`, `adopted_from`) that must NOT
    reach hand-verified truth, so a projection is right — what was wrong was
    projecting onto a hand list and saying nothing about the remainder.  Every
    caller prints what it dropped, so a misspelled `linnes: 1` is visible
    instead of being silently equivalent to no flag at all.

    `name` and `parts` are always present in the output, even when missing from
    the input, so the shape check reports "no printed name" rather than
    "unexpected shape".  `parts` is COPIED but never reordered.  A key at its
    DEFAULT is omitted, because every merged row omits it.
    """
    allowed = allowed_keys()
    out: dict = {"name": entry.get("name")}
    p = entry.get("parts")
    out["parts"] = list(p) if isinstance(p, list) else p
    for k in optional_keys():
        if entry.get(k) is not None and entry[k] != DEFAULTS.get(k, object()):
            out[k] = entry[k]
    dropped = sorted(k for k in entry if k not in allowed)
    return out, dropped


def entry_problems(k: int, s) -> list[str]:
    """`works.json`'s shape, for one entry.  Empty list means acceptable."""
    if not isinstance(s, dict):
        return [f"entry {k} is not an object"]
    out: list[str] = []
    extra = sorted(set(s) - allowed_keys())
    if extra:
        out.append(
            f"entry {k} has undeclared key(s) {extra} — a `staves` entry is "
            f"{list(REQUIRED)}, optionally {' / '.join(optional_keys())}. If "
            f"this is a new hand-read fact, declare it (a consumer that reads "
            f"it, or `staves_schema.RECORDED_ONLY` with a reason) and give it "
            f"a validator; if it is a typo, it would have been dropped in "
            f"silence.")
    for field, check in VALIDATORS.items():
        if field in s:
            bad = check(s[field])
            if bad:
                out.append(f"entry {k} {bad}")
    # A single printed rule is not also several five-line staves.
    # ⚠️ Guarded on VALIDATED values: a validator must refuse bad input, never
    # raise on it, and this comparison would raise on an arbitrary one.
    if (_v_lines(s["lines"]) is None if "lines" in s else True) and (
            _v_printed_staves(s["printed_staves"]) is None
            if "printed_staves" in s else False):
        if (s.get("lines") or 5) != 5 and s["printed_staves"] > 1:
            out.append(f"entry {k} is both a one-line rule and "
                       f"{s['printed_staves']} printed staves — contradictory")
    if not isinstance(s.get("name"), str) or not s["name"].strip():
        out.append(f"entry {k} has no printed name")
    p = s.get("parts")
    if not isinstance(p, list) or not p or not all(
            isinstance(i, int) and not isinstance(i, bool) for i in p):
        out.append(f"entry {k} `parts` is not a non-empty list of ints")
    elif len(set(p)) != len(p):
        # DUPLICATE within one entry: a real fault. The same staff cannot carry
        # one reference part twice, and `page_normalise` would merge a part
        # into itself. ⚠️ NOT sortedness — see `merge_additions`.
        out.append(f"entry {k} `parts` names a part twice: {p}")
    return out


def problems(staves) -> list[str]:
    if not isinstance(staves, list) or not staves:
        return ["`staves` is not a non-empty list"]
    out: list[str] = []
    for k, s in enumerate(staves):
        out += entry_problems(k, s)
    return out


def unaccounted(works: Path | None = None) -> dict[str, list[str]]:
    """`row_id -> keys` on the committed file that this schema does not know.

    A new hand-read fact must be declared before it is truth; this is what
    turns "declare it" from a convention into a failing test.
    """
    doc = json.loads((works or WORKS).read_text())
    allowed = allowed_keys()
    out: dict[str, list[str]] = {}
    for row in doc.get("rows", []):
        st = row.get("staves")
        if not isinstance(st, list):
            continue                      # `same-as:<row>`, or no map at all
        extra = sorted({k for s in st if isinstance(s, dict) for k in s}
                       - allowed)
        if extra:
            out[row["row_id"]] = extra
    return out
