"""Is a BRAKE still calibrated for the architecture it stops? — the sixth
derived question.

    python3 -m tools.omr.staged.brakes            # the five tables
    python3 -m tools.omr.staged.brakes --json
    python3 -m tools.omr.staged.brakes --check    # non-zero on anything
                                                  # not on ACCOUNTED
    python3 -m tools.omr.staged.brakes --run rec.json   # the two RECORD
                                                        # questions, measured

⚠️⚠️ **THE QUESTION, AND WHY A LIST OF BRAKES IS NOT THE ANSWER.** Sean,
2026-09-17: *"We have rules that are stopping things too soon or disregarding
the information or the process ... when those statements were made we didn't
have everything we have now."* The target is NOT every refusal. **A refusal
that prevents a GUESS is load-bearing and must survive.** What this asks is
narrower and mechanical: *was this brake's stated premise written against a
capability the staged architecture has since grown?*

Sean again, and this is the yardstick: *"Every brake should be evaluated
against the conceptual possibilities of the new staged architecture."* Most
brakes predate the record entirely — they were written for a single pass whose
only two options were ANSWER or DISCARD.

## The capabilities a premise may have been written against

Named here so a finding must CITE one. "This looks over-cautious" is not a
finding; *"this refuses X while Y is on the record"* is.

  ABSTENTION_IS_DATA   `Ruling.abstain(reason)` is recorded with its basis, so
                       silence is typed, reasoned and countable. Dissolves
                       *"silence would be indistinguishable from an answer"*.
  PARTIAL_HAS_A_HOME   `Ruling.narrow(candidates, support)`. Dissolves *"we
                       cannot express 'it is one of these'"*.
  EVIDENCE_CONTRIBUTES `Mode.ADDITIVE` with weighted terms. Dissolves *"there
                       was no way to weigh a weak witness"*.
  PROVENANCE_IS_KEPT   `Verdict.basis` / `decider` / the circularity filter.
                       Dissolves *"a guess would be indistinguishable from a
                       reading"*.
  CORRELATION_IS_SAYABLE  `Verdict.correlated` / `independent_groups`.
                       Dissolves *"two agreeing readers might not be
                       independent"* as a reason to REFUSE — it is now a
                       reason to RECORD.
  A_FOURTH_STAGE       `OMR_INFER`, `INFERABLE = {NARROWED, ABSTAINED}`,
                       supersedes visibly, may never overturn a DECIDED
                       reading. Dissolves *"acting here would launder a
                       guess"* — the guess has a legal, LABELLED home.

⚠️ A brake whose premise is *"the page does not say"* is untouched by every
one of those and STAYS. That is most of them, and this module's own run
proves it rather than assuming it.

## ⚠️⚠️ THE COROLLARY THAT IS PROBABLY THE LARGER FINDING

A brake whose reason was *"no stage may do this"*, where a stage now exists,
is **not a brake to remove — it is a HANDOFF THAT MAY NOT BE WIRED.** The
refusal stays exactly as written; the question is whether the declined work
REACHES the stage now permitted to take it. Question 1 asks precisely that,
and on both shared records the answer is mostly no.

## The five questions, and why none is a sixth copy of an existing tool

Six derived instruments already stand, and each asks something else:

  `gather_coverage`   is it OBSERVED at all?
  `inventory --check` is a `wants` entry actually READ?
  `wiring --check`    can a declared read REACH it (frame / detail / roundtrip)?
  `no_producer`       is a threaded PARAMETER ever supplied?
  `reach`             does anything read a quantity AT ALL?
  `capture`           is the ink's shape / position / raster recorded?

**None of them asks what a REFUSAL passed over.** They are all about the
plumbing between declarations; these five are about the moment a decision
stops. `git log --all -S` finds no prior implementation of any of them.

  1. HANDOFF   an unresolved verdict whose quantity NO INFER rule targets.
  2. BLIND     an abstention whose `considered` is EMPTY — it looked at
               nothing. ⚠️ Not automatically a fault: a flag-gated decision
               correctly looks at nothing. It is a fault when evidence stood
               there, which Q3 then says.
  3. UNCONSULTED  a quantity the decision DECLARES in `wants`, PRESENT at the
               subject or an ancestor, and absent from the verdict's own
               `considered`/`used`/`missing`/`declined`/`excluded`. **This
               needs no new declaration to fix** — the decision already said
               it wanted it.
  4. READINGS  a DIRECT READING of a quantity, named by `adjudicate.READINGS`,
               that the owning decision does not declare. READINGS is the
               repo's OWN table of what reads what; disagreeing with it is a
               statement by the tree against itself.
  5. VOCABULARY  a declared `reason` no `Ruling` site can return — CLAUDE.md's
               *"a vocabulary word with no branch"*, which names an evidence
               channel the decision does not have.

## ⚠️ DERIVED, AND EVERY QUESTION CARRIES A POSITIVE CONTROL

This module's own first drafts had, in order: an empty `REGISTRY` (the
recorded hazard — `adjudicate.REGISTRY` is EMPTY on a bare import and only the
`adjudicators` package populates it); an empty `infer.RULES` for the SAME
reason one question later, which reported *zero* INFER targets and would have
made Q1 read 100%; a Q3 that compared ROW IDS in `considered` against QUANTITY
NAMES in `wants`, so a want that WAS consulted read as untouched and the table
was 30× too large; and a Q5 regex that matched docstring prose and reported
nothing at all. Four vacuity faults in one session, in a module written to
catch vacuity.

So `controls()` counts what each question found to be HEALTHY, and `--check`
exits non-zero when any control is zero — a question that can only answer
"nothing wrong" is not a question.
"""
from __future__ import annotations

import argparse
import ast
import collections
import inspect
import json
import pathlib
import sys
from typing import Dict, List, Optional, Sequence, Tuple

from . import adjudicate, infer
from . import adjudicators as _adjudicators   # POPULATES adjudicate.REGISTRY
from . import inferences as _inferences       # POPULATES infer.RULES
from .record import ABSTAIN, Subject

#: ⚠️ This module NAMES quantities in order to audit them and READS none of
#: them at run time. `wiring`'s DETAIL question and `reach`'s reader scan must
#: not count a mention here as a consumer — CLAUDE.md records that committing
#: `capture.py` turned two live gaps STALE for exactly this reason.
DERIVED_CHECK = True

_ = (_adjudicators, _inferences)   # imported for effect; named so linters keep them


# ─────────────────────────────────────────────────────────────────────────────
# The capability vocabulary a finding must cite
# ─────────────────────────────────────────────────────────────────────────────

CAPABILITIES: Dict[str, str] = {
    "ABSTENTION_IS_DATA":
        "`Ruling.abstain(reason)` is recorded with its basis: silence is "
        "typed, reasoned and countable.",
    "PARTIAL_HAS_A_HOME":
        "`Ruling.narrow(candidates, support)` — 'it is one of these' is a "
        "first-class outcome and INFER's declared input.",
    "EVIDENCE_CONTRIBUTES":
        "`Mode.ADDITIVE` with weighted terms: a weak witness can ADD without "
        "gating.",
    "PROVENANCE_IS_KEPT":
        "`Verdict.basis` / `decider`: a DERIVED answer is distinguishable "
        "from a READ one.",
    "CORRELATION_IS_SAYABLE":
        "`Verdict.correlated` / `independent_groups`: correlated witnesses "
        "are representable, so correlation is recorded rather than refused.",
    "A_FOURTH_STAGE":
        "`OMR_INFER` — `INFERABLE = {NARROWED, ABSTAINED}`, supersedes "
        "visibly, may never overturn a DECIDED reading.",
    "THE_PAGE_DOES_NOT_SAY":
        "⚠️ NOT a capability — the marker for a brake NO capability reaches. "
        "A premise citing this STAYS.",
}


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNTED — an inventory, never a suppression list
#
# ⚠️ Same contract as `reach.KNOWN_GAPS` and `export_coverage.KNOWN_GAPS`:
# `--check` fails on anything NOT here, **and on an entry nothing reports any
# more**. A closed finding must LEAVE this list or the list stops describing
# the tree and starts describing its history.
#
# ⚠️⚠️ Every entry is a reason the gap EXISTS. None is a reason it is
# ACCEPTABLE. That distinction is `capture.py`'s, and it is the thing that
# stops an inventory becoming an excuse.
# ─────────────────────────────────────────────────────────────────────────────

#: Q4 — a READINGS entry the owning decision does not declare.
ACCOUNTED_READINGS: Dict[Tuple[str, str], str] = {
    ("instrument", "text_layer"): (
        "OPEN. `READINGS` names the PDF text layer a direct reading of the "
        "instrument and `adjudicate_instrument` does not declare it. ⚠️ REACH "
        "IS ZERO on both shared records (0 `text_layer` rows on either), so "
        "this costs nothing measurable here and must not be ranked as though "
        "it did — 18 of 65 IMSLP PDFs carry a text layer and neither of ours "
        "is one."),
    ("slot_index", "text_layer"): "OPEN — same zero reach as instrument's.",
    ("slot_index", "margin_label"): (
        "OPEN, and NOT zero reach: 50 and 97 `margin_label` rows. "
        "`adjudicate_slot_index` reaches the label only THROUGH `instrument`, "
        "so a staff whose instrument abstains loses the label too — the "
        "cascade Q2/Q3 measure at 25 of 25 on Beethoven."),
    ("part_partition", "text_layer"): "OPEN — same zero reach.",
    ("part_partition", "margin_label"): (
        "OPEN — same shape as slot_index's: reached only through `instrument` "
        "and `slot_index`, both of which can abstain first."),
    ("staff_group", "systemic_column"): (
        "OPEN. ⚠️ REACH IS ZERO — `systemic_column` has 0 rows on both shared "
        "records, so nothing is currently lost."),
    ("system_membership", "systemic_column"): "OPEN — same zero reach.",
    ("group_symbol", "bracket_block"): (
        "OPEN, and reach is NOT zero (75 and 97 rows). `group_symbol` reads "
        "`staff_group`, which reads `bracket_block` — so the reading is "
        "consulted one remove away, and this may be a correct indirection "
        "rather than a gap. NOT adjudicated here: it needs the decision read, "
        "not a table compared."),
    ("arc_owner", "notehead_staff_position"): (
        "OPEN. `arc_owner` builds its per-staff head sets from `glyph_owner` "
        "verdicts rather than from the position rows `READINGS` names."),
    ("pitch", None): (
        "SOUND, and reported so the entry is not silent. `Q.PITCH` has no "
        "ADJUDICATE owner because it is an EVALUATE CONSEQUENCE — "
        "`consequences.RESTATE_PITCH`, cause `Q.CLEF`, effect `Q.PITCH`. A "
        "pitch is ENTAILED by position plus clef, not read; `READINGS` naming "
        "`notehead_staff_position` as its reading is correct and so is the "
        "absence of a decision. Nothing to do."),
}

#: Q5 — a declared `reason` no `Ruling` site can return.
#:
#: ⚠️ ONLY modules with NO dynamically-computed reason expression are judged
#: here. Where a module builds a reason at run time this cannot resolve it,
#: and the honest answer is UNRESOLVED, not a finding — an earlier draft
#: reported ten decisions and eight were that confusion.
ACCOUNTED_VOCABULARY: Dict[Tuple[str, str], str] = {
    ("clef", "margin_below_floor"): (
        "OPEN, and it is a RENAME that left the word behind: `clef.py:330`'s "
        "own comment says the code now reports something else *'instead of "
        "the old bare `margin_below_floor`'*. ⚠️ The word is still REACHED on "
        "the record (3 narrowed clefs carry it), so the vocabulary and the "
        "code disagree about which of them is current — this is a finding "
        "about the DECLARATION, and the tree must be read before either is "
        "changed."),
    ("clef", "all_candidates_excluded"): (
        "OPEN — declared in the same tuple, returned by no site, and NOT "
        "reached on either shared record."),
}


# ─────────────────────────────────────────────────────────────────────────────
# Static questions
# ─────────────────────────────────────────────────────────────────────────────


def infer_targets() -> frozenset:
    """Quantities a registered INFER rule can act on.

    ⚠️ `infer.RULES` is EMPTY on a bare import — only `inferences` registers
    them, exactly as `adjudicate.REGISTRY` needs `adjudicators`. This module
    imports both at the top, and `controls()` asserts both are non-empty,
    because a silent zero here makes question 1 read 100%.
    """
    return frozenset(r.target for r in infer.RULES)


def readings_gap() -> List[dict]:
    """Q4 — a direct reading named by `READINGS` its owner does not declare."""
    out: List[dict] = []
    for quantity, reads in sorted(adjudicate.READINGS.items()):
        spec = adjudicate.REGISTRY.get(quantity)
        if spec is None:
            out.append({"quantity": quantity, "reading": None,
                        "note": "no decision owns this quantity"})
            continue
        for reading in reads:
            if reading not in spec.wants:
                out.append({"quantity": quantity, "reading": reading,
                            "decision": spec.fn.__name__})
    return out


_ABSTAIN_VALUES = {n: getattr(ABSTAIN, n) for n in dir(ABSTAIN) if n.isupper()}


def _reasons_constructible(module) -> Tuple[set, bool]:
    """Every literal reason a `Ruling` in this module can carry, and whether
    any site computes one dynamically.

    ⚠️ AST over the actual `Ruling` construction sites, never a regex over the
    source: the first draft's regex matched prose inside docstrings and
    reported no findings at all.
    """
    src = pathlib.Path(module.__file__).read_text()
    tree = ast.parse(src)
    literals: set = set()
    dynamic = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else (
            func.id if isinstance(func, ast.Name) else None)
        if name not in ("abstain", "narrow", "Ruling"):
            continue
        slots: List[ast.AST] = []
        if name == "abstain":
            slots = list(node.args[:1])
        elif name == "narrow":
            slots = list(node.args[1:2])
        slots += [kw.value for kw in node.keywords if kw.arg == "reason"]
        for slot in slots:
            if isinstance(slot, ast.Constant) and isinstance(slot.value, str):
                literals.add(slot.value)
            elif (isinstance(slot, ast.Attribute)
                  and isinstance(slot.value, ast.Name)
                  and slot.value.id == "ABSTAIN"):
                value = _ABSTAIN_VALUES.get(slot.attr)
                if value:
                    literals.add(str(value))
            else:
                dynamic = True
    return literals, dynamic


def vocabulary_gap() -> Tuple[List[dict], List[dict]]:
    """Q5 — (findings, unresolved). A reason declared and never returned.

    ⚠️ A module that computes any reason at run time is UNRESOLVED as a whole
    and reported apart. Reporting it as a finding is how the first draft
    accused eight decisions of a fault only two have.
    """
    cache: Dict[object, Tuple[set, bool]] = {}
    findings: List[dict] = []
    unresolved: List[dict] = []
    for quantity, spec in sorted(adjudicate.REGISTRY.items()):
        module = inspect.getmodule(spec.fn)
        if module not in cache:
            cache[module] = _reasons_constructible(module)
        literals, dynamic = cache[module]
        missing = [r for r in spec.reasons
                   if r != ABSTAIN.NOT_IMPLEMENTED and r not in literals]
        if not missing:
            continue
        row = {"quantity": quantity, "decision": spec.fn.__name__,
               "reasons": missing, "module": pathlib.Path(module.__file__).name}
        (unresolved if dynamic else findings).append(row)
    return findings, unresolved


# ─────────────────────────────────────────────────────────────────────────────
# Record questions
# ─────────────────────────────────────────────────────────────────────────────

UNRESOLVED_OUTCOMES = ("abstained", "narrowed")


def measure(record: dict) -> dict:
    """Q1/Q2/Q3, from a saved staged record.

    ⚠️ `considered` and `used` hold ROW IDS; `missing`, `declined` and
    `excluded` hold QUANTITY NAMES. Mixing the two is not a style point — the
    first draft did, and reported 3,674 unconsulted cells where there are 125.
    """
    body = record.get("record", record)
    observations = body["observations"]
    verdicts = body["verdicts"]
    abstentions = body.get("abstentions", [])

    quantity_of: Dict[str, str] = {}
    for row in observations:
        quantity_of[row["id"]] = row["quantity"]
    for row in verdicts:
        quantity_of[row["id"]] = row["quantity"]
    for row in abstentions:
        quantity_of[row["id"]] = row["quantity"]

    observed_at = collections.defaultdict(set)
    for row in observations:
        observed_at[row["subject"]].add(row["quantity"])
    decided_at = collections.defaultdict(set)
    for row in verdicts:
        if row["outcome"] == "decided":
            decided_at[row["subject"]].add(row["quantity"])

    pool_cache: Dict[str, set] = {}

    def pool(key: str) -> set:
        """Everything a decision at `key` could legally reach upward."""
        hit = pool_cache.get(key)
        if hit is None:
            hit = set(observed_at.get(key, ())) | set(decided_at.get(key, ()))
            for ancestor in Subject.from_key(key).ancestors():
                akey = ancestor.to_key()
                hit |= set(observed_at.get(akey, ()))
                hit |= set(decided_at.get(akey, ()))
            pool_cache[key] = hit
        return hit

    targets = infer_targets()
    handoff = collections.Counter()
    blind = collections.Counter()
    unconsulted = collections.Counter()
    touched_mentions = 0
    total = 0

    for verdict in verdicts:
        if verdict["outcome"] not in UNRESOLVED_OUTCOMES:
            continue
        quantity = verdict["quantity"]
        spec = adjudicate.REGISTRY.get(quantity)
        if spec is None:
            continue
        total += 1
        key = (quantity, verdict["reason"])
        handoff[(quantity, verdict["reason"], quantity in targets)] += 1
        if not verdict["considered"]:
            blind[key] += 1
        touched = {quantity_of.get(i) for i in verdict["considered"]}
        touched |= {quantity_of.get(i) for i in verdict["used"]}
        touched |= set(verdict["missing"]) | set(verdict["declined"])
        touched |= set(verdict["excluded"])
        touched.discard(None)
        touched_mentions += len(touched)
        available = pool(verdict["subject"])
        for want in spec.wants:
            if want in available and want not in touched:
                unconsulted[(quantity, verdict["reason"], want)] += 1

    reaches = sum(n for (_q, _r, ok), n in handoff.items() if ok)
    return {
        "unresolved_verdicts": total,
        "reaches_infer": reaches,
        "stops_with_no_stage": total - reaches,
        "handoff": {f"{q}/{r}": {"n": n, "reaches_infer": ok}
                    for (q, r, ok), n in handoff.most_common()},
        "blind": {f"{q}/{r}": n for (q, r), n in blind.most_common()},
        "unconsulted": {f"{q}/{r}/{w}": n
                        for (q, r, w), n in unconsulted.most_common()},
        "controls": {
            "unresolved_verdicts_examined": total,
            "touched_quantity_mentions": touched_mentions,
            "subjects_with_a_reachable_pool": len(pool_cache),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Controls and the check
# ─────────────────────────────────────────────────────────────────────────────


def controls() -> Dict[str, int]:
    """What each question found to be HEALTHY. A zero means it did not run."""
    findings, unresolved = vocabulary_gap()
    reason_total = sum(len(s.reasons) for s in adjudicate.REGISTRY.values())
    return {
        "decisions_registered": len(adjudicate.REGISTRY),
        "infer_rules_registered": len(infer.RULES),
        "readings_entries": len(adjudicate.READINGS),
        "readings_entries_fully_declared":
            len(adjudicate.READINGS) - len({r["quantity"] for r in readings_gap()}),
        "declared_reasons": reason_total,
        "decisions_with_every_reason_reachable":
            len(adjudicate.REGISTRY) - len(findings) - len(unresolved),
        "capability_vocabulary": len(CAPABILITIES),
    }


def check() -> Tuple[int, List[str]]:
    """(exit code, lines). Non-zero on an unaccounted finding, a STALE entry,
    or a zero control."""
    lines: List[str] = []
    bad = 0

    ctl = controls()
    for name, value in sorted(ctl.items()):
        if value == 0:
            lines.append(f"CONTROL AT ZERO: {name} — the question did not run")
            bad = 1

    seen_readings = set()
    for row in readings_gap():
        pair = (row["quantity"], row.get("reading"))
        seen_readings.add(pair)
        if pair not in ACCOUNTED_READINGS:
            what = "has no owning decision" if pair[1] is None \
                else f"omits {pair[1]}"
            lines.append(f"UNACCOUNTED (readings): {pair[0]} {what}")
            bad = 1
    for pair in ACCOUNTED_READINGS:
        if pair not in seen_readings:
            lines.append(f"STALE (readings): {pair[0]}/{pair[1]} is no longer "
                         f"reported — the entry must LEAVE the list")
            bad = 1

    findings, unresolved = vocabulary_gap()
    seen_vocab = set()
    for row in findings:
        for reason in row["reasons"]:
            pair = (row["quantity"], reason)
            seen_vocab.add(pair)
            if pair not in ACCOUNTED_VOCABULARY:
                lines.append(f"UNACCOUNTED (vocabulary): {pair[0]} declares "
                             f"'{pair[1]}' and no Ruling site returns it")
                bad = 1
    for pair in ACCOUNTED_VOCABULARY:
        if pair not in seen_vocab:
            lines.append(f"STALE (vocabulary): {pair[0]}/{pair[1]} is no "
                         f"longer reported — the entry must LEAVE the list")
            bad = 1

    for row in unresolved:
        lines.append(f"UNRESOLVED (vocabulary): {row['quantity']} — "
                     f"{row['module']} computes a reason at run time, so "
                     f"{row['reasons']} cannot be judged statically")
    return bad, lines


def _render(record_path: Optional[str]) -> List[str]:
    out: List[str] = []
    targets = infer_targets()
    out.append("1. HANDOFF — which quantities can INFER take at all?")
    out.append(f"   INFER rules: {len(infer.RULES)}   targets: "
               f"{sorted(targets) or '(none)'}")
    reachable = sorted(q for q in adjudicate.REGISTRY if q in targets)
    stopped = sorted(q for q in adjudicate.REGISTRY if q not in targets)
    out.append(f"   decisions whose unresolved verdicts CAN reach INFER: "
               f"{len(reachable)} {reachable}")
    out.append(f"   decisions whose unresolved verdicts STOP: {len(stopped)}")
    out.append("")

    out.append("4. READINGS — a direct reading the owning decision omits")
    for row in readings_gap():
        if row.get("reading") is None:
            out.append(f"   ⚠️ {row['quantity']:<22} {row['note']}")
            continue
        mark = "   " if (row["quantity"], row["reading"]) in ACCOUNTED_READINGS \
            else " ⚠️"
        out.append(f"  {mark} {row['quantity']:<22} omits {row['reading']}")
    out.append("")

    findings, unresolved = vocabulary_gap()
    out.append("5. VOCABULARY — a declared reason no Ruling site returns")
    for row in findings:
        out.append(f"   ⚠️ {row['quantity']:<22} {row['reasons']}")
    for row in unresolved:
        out.append(f"   ·  {row['quantity']:<22} UNRESOLVED "
                   f"({row['module']} computes a reason)")
    out.append("")

    if record_path:
        from .record_io import load_record
        record = load_record(record_path)
        m = measure(record)
        out.append(f"── measured on {pathlib.Path(record_path).name}")
        out.append(f"   unresolved verdicts        {m['unresolved_verdicts']:>6}")
        out.append(f"   reach a registered rule    {m['reaches_infer']:>6}")
        out.append(f"   STOP, no stage may take it {m['stops_with_no_stage']:>6}")
        out.append("")
        out.append("   2. BLIND — abstained with `considered` EMPTY")
        for key, n in list(m["blind"].items())[:12]:
            out.append(f"      {n:>6}  {key}")
        out.append("")
        out.append("   3. UNCONSULTED — a DECLARED want, present, not touched")
        for key, n in list(m["unconsulted"].items())[:16]:
            out.append(f"      {n:>6}  {key}")
        out.append("")
        out.append("   POSITIVE CONTROLS (a zero means it did not run)")
        for name, value in sorted(m["controls"].items()):
            out.append(f"      {name:<36} {value}")
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--run", metavar="RECORD.json")
    args = ap.parse_args(argv)

    if args.json:
        payload = {
            "controls": controls(),
            "capabilities": CAPABILITIES,
            "infer_targets": sorted(infer_targets()),
            "readings_gap": readings_gap(),
            "vocabulary_gap": vocabulary_gap()[0],
            "vocabulary_unresolved": vocabulary_gap()[1],
        }
        if args.run:
            from .record_io import load_record
            payload["measured"] = measure(load_record(args.run))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    for line in _render(args.run):
        print(line)

    print("── POSITIVE CONTROLS (a zero means the question did not run) ──")
    for name, value in sorted(controls().items()):
        print(f"   {name:<40} {value}")
    print()

    if args.check:
        bad, lines = check()
        for line in lines:
            print(line)
        problems = sum(1 for l in lines if l.startswith(("UNACCOUNTED",
                                                         "STALE", "CONTROL")))
        print(f"── {problems} unaccounted/stale, "
              f"{len(lines) - problems} reported-and-accounted")
        return bad
    return 0


if __name__ == "__main__":
    sys.exit(main())
