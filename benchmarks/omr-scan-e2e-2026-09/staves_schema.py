"""What a `works.json` `staves` entry may carry — DERIVED, not hand-listed.

`works.json` is hand-verified truth and its `staves` entries are the part
correspondence seven other benchmarks read.  Every step between a human's
keystroke and the file used to project an entry down to a hand-written
`{"name": ..., "parts": ...}`, and each of those hand lists went stale the day
the data model grew a third fact.  There were **five** such projections and
they disagreed with each other:

  * `build_cache.research_proposal`   kept `lines`, dropped `printed_staves`;
  * `server.Store.row` (the seed)     kept neither;
  * `server.api_adopt`                kept neither;
  * `server.api_done`                 kept neither;
  * `merge_additions.check_row`       kept neither, on its fallback branch.

And `merge_additions.shape_problems` refused, in words, anything that was not
exactly `name`+`parts` — a premise **six of the twenty committed rows already
violated**, so the writer could not re-merge the file it had written.

⚠️ THE TWO FAULTS ARE NOT THE SAME AND ONLY ONE OF THEM IS LOUD.  A stale
allow-list REFUSES, which is visible and annoying.  A stale PROJECTION DROPS,
which is silent: `mahler-sym5-mvt1-local-p2` landed in `works.json` with a
correct 21-entry lineup and no `lines: 1` flags, which moved its part join from
cause D ("no lineup at all") to cause B ("the lineup names one-line percussion
staves") rather than closing it, and left two tests failing until the four
flags were typed back in by hand (`981cbc41`).

So there is now ONE definition of the shape, here, and one `project()` that
every step calls.  It is the shape of `export_coverage`'s repair and of
`class_aliases.py`: derive what the code will tell you, DECLARE the small
remainder with a reason, and fail loudly on anything in neither.

  REQUIRED          `name` + `parts`, the structural invariants.
  consumed_keys()   DERIVED BY AST from the consumer that reads them —
                    `run_ledger.expand_lineup`, the function that turns a
                    lineup entry into the slots the arity gate counts.  Nobody
                    types these; teaching that function a new key adds it here.
  RECORDED_ONLY     hand-read facts committed to `works.json` that no consumer
                    reads YET.  Declared with a reason, the way
                    `class_aliases.COARSER_THAN_CANONICAL` is.

`unaccounted()` returns every key on a committed row that is in none of the
three, so a new fact is a failing test rather than a silent drop.

⚠️ AND THE DERIVATION RAISES RATHER THAN RETURNING NOTHING.  An empty
derivation is not a smaller schema, it is a silent one: the allow-list narrows
back to `name`+`parts`, `project()` starts dropping `lines: 1` again and
`problems()` starts refusing the committed file — both original faults, back at
once, looking exactly like the behaviour this replaced.

⚠️ WHAT THIS MODULE DELIBERATELY DOES NOT DO is derive the allow-list from
`works.json` itself.  That would make the anti-drift test vacuous — the file
would be proving its own shape — and it would bless a typo the moment one was
committed.  See `test_staves_schema.py`.
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

#: The consumer whose reads ARE the optional schema.  One (file, function)
#: pair: `expand_lineup` is the function that turns a hand-read lineup entry
#: into the slots the ledger's arity gate counts, and its own docstring calls
#: them "two declared shapes, both facts about the ENGRAVING".
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
            "them three flats. Carried by "
            "`beethoven-sym5-mvt1-984073-p1` for all twelve staves; the same "
            "twelve readings are ALSO a Python literal in "
            "`benchmarks/omr-first-run-2026-08/eval_first_run.py` (STAVES), "
            "which scores the pipeline's clef against them. So no consumer "
            "reads the column YET — what reads it is a duplicate of it.",
    "key": "the key signature PRINTED on this staff as a fifths count "
           "(-3 = three flats), hand-read off the scan and therefore "
           "TRANSPOSING: the Clarinetti in B row is -1 on a page whose "
           "concert key is -3, which is the whole point of reading it off the "
           "page. Same row, same rule and same non-consumer as `clef`.",
}


def _consumer_path() -> Path:
    return ROOT / CONSUMER[0]


def keys_read_by(source: str, function: str) -> frozenset[str]:
    """Every string key `function` reads off a plain local, by AST.

    Collects the literal of `<name>.get("k")` and `<name>["k"]` where the
    receiver is a bare Name — inside `expand_lineup` that is the loop variable
    and nothing else.  Chained receivers (`row.get("page", {}).get("x")`) are
    deliberately not collected: those are keys of some OTHER object.

    Split out from `consumed_keys` so the derivation itself is testable on a
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


class SchemaUnreadable(RuntimeError):
    """The consumer this schema is derived FROM could not be read."""


def consumed_keys() -> frozenset[str]:
    """The optional keys `CONSUMER` actually reads.  `REQUIRED` is removed:
    those are structural and are checked separately.

    ⚠️ RAISES rather than degrading to an empty set, and that is deliberate.
    An empty derivation is not a smaller schema, it is a SILENT one: the
    allow-list narrows back to `name`+`parts`, so `project()` starts dropping
    `lines: 1` again and `problems()` starts refusing the committed file — the
    two faults this module exists to end, arriving together and looking
    exactly like the old behaviour. A missing consumer is a broken checkout,
    not a configuration, and nothing may write hand-verified truth through a
    schema it could not derive.
    """
    path = _consumer_path()
    if not path.is_file():
        raise SchemaUnreadable(
            f"{CONSUMER[0]} is not on disk — the optional `staves` keys are "
            f"derived from it and cannot be guessed")
    keys = keys_read_by(path.read_text(), CONSUMER[1])
    if not keys:
        raise SchemaUnreadable(
            f"{CONSUMER[0]}::{CONSUMER[1]} reads no entry key — either it was "
            f"renamed, or the derivation no longer matches how it reads one. "
            f"Fix the pointer; do NOT fall back to name+parts.")
    return keys - set(REQUIRED)


def optional_keys() -> tuple[str, ...]:
    """The optional keys, derived first and declared second, in a stable order."""
    return tuple(sorted(consumed_keys())) + tuple(sorted(RECORDED_ONLY))


def allowed_keys() -> frozenset[str]:
    return frozenset(REQUIRED) | frozenset(optional_keys())


def project(entry: dict) -> tuple[dict, list[str]]:
    """One `staves` entry as `works.json` should hold it, plus what was DROPPED.

    ⚠️ THE DROPPED LIST IS HALF THE POINT.  The UI's own state carries
    bookkeeping (`proposed`, `verdict`, `adopted_from`) that must NOT reach
    hand-verified truth, so a projection is right — what was wrong was
    projecting onto a hand list and saying nothing about the remainder.  Every
    caller prints what it dropped, so a misspelled `linnes: 1` is visible
    instead of being silently equivalent to no flag at all.

    `name` and `parts` are always present in the output, even when missing from
    the input, so the shape check reports "no printed name" rather than
    "unexpected shape".  `parts` is COPIED but never reordered.
    """
    allowed = allowed_keys()
    out: dict = {"name": entry.get("name")}
    p = entry.get("parts")
    out["parts"] = list(p) if isinstance(p, list) else p
    for k in optional_keys():
        if k in entry:
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
            f"{list(REQUIRED)} plus {list(optional_keys())}. If this is a new "
            f"hand-read fact, declare it (a consumer that reads it, or "
            f"`staves_schema.RECORDED_ONLY` with a reason); if it is a typo, "
            f"it would have been dropped in silence.")
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
