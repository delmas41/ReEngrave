"""The staged pipeline's entry point — GATHER, then ADJUDICATE, then EVALUATE.

⚠️ ALONGSIDE. Nothing in this module is reachable from `transcribe.py`. With
`OMR_ADJUDICATE` unset or "0" the existing pipeline is what runs, and this
file is never imported by it.

    OMR_ADJUDICATE=0        (default) the existing pipeline. Byte-identical.
    OMR_ADJUDICATE=shadow   both paths, ONE gather, ONE process, plus a
                            divergence table. The legacy half stays
                            authoritative.
    OMR_ADJUDICATE=1        the staged path is authoritative.

⚠️ WHY SHADOW IS ONE PROCESS ON ONE GATHER, and it is not a convenience.
Three failure modes this project has actually been bitten by all disappear:

  * THE CACHED A/B. `scan_eval.run_pipeline` returns early if the prediction
    file exists, so two arms sharing a fixtures dir with an empty `--tag`
    reuse the first arm's transcriptions and the second arm never runs --
    reporting "identical on every bucket and every row", which is exactly the
    clean result a flag-guarded change hopes for. The only tell was wall
    time. Here there is no second arm to cache.
  * DETECTOR JITTER. A from-scratch rebuild of the hairpin fix reproduced the
    categorical result and NOT the edit count: the same four boxes'
    confidences moved between runs on byte-identical code. Here both paths
    consume the same detections and jitter cancels exactly.
  * THE WORKTREE VENV TRAPS. Four symlinks, three of which fail on the scan
    side only. The divergence table needs no venv, no scorer, no benchmark.

⚠️ NOTHING IN HERE HAS BEEN MEASURED. Not one accuracy arm has been run.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import consequences  # noqa: F401  -- registers the EVALUATE rules
from . import adjudicators  # noqa: F401  -- registers the decisions
from . import adjudicate, evaluate, gather, groups
from .record import Kind, Log, Outcome, Q, State, Subject

MODE_OFF = "0"
MODE_SHADOW = "shadow"
MODE_ON = "1"


def mode() -> str:
    """Read the flag. Anything unrecognised is OFF -- a typo must not silently
    switch a user onto an unmeasured pipeline."""
    raw = os.environ.get("OMR_ADJUDICATE", MODE_OFF).strip().lower()
    return raw if raw in (MODE_OFF, MODE_SHADOW, MODE_ON) else MODE_OFF


def enabled() -> bool:
    return mode() in (MODE_SHADOW, MODE_ON)


# ─────────────────────────────────────────────────────────────────────────────
# Preparing pages -- the existing phase 1, called and not rewritten
# ─────────────────────────────────────────────────────────────────────────────


def prepare_pages(pdf_path: str, pages: Sequence[int], *,
                  dpi: int = 600) -> List[Tuple[Any, List[Any]]]:
    """Render, detect staves, group systems, cut cells — all existing code.

    ⚠️ This is the FIRST of the three hard gathering edges: a measure cell is
    DEFINED by `staff.line_ys`, so nothing has coordinates until this has
    run. `extract_measures` enforces it itself (`measure_extractor.py:
    1441-1442`: `if not pws.barlines: detect_barlines(pws)`).
    """
    from ..preprocessing import render_page
    from ..staff_detector import detect_staves
    from ..measure_extractor import extract_measures
    from ..staff_line_removal import remove_staff_lines

    out: List[Tuple[Any, List[Any]]] = []
    for p in pages:
        pws = detect_staves(render_page(pdf_path, p, dpi=dpi))
        cells = extract_measures(pws)
        # ⚠️ THE SECOND IMAGE, AND IT IS NOT OPTIONAL. `extract_measures`
        # leaves `image_no_staff=None`; `line_detection` PREFERS that variant
        # and SILENTLY FALLS BACK to `cell.image` when it is missing
        # (`:265-267`, `:599-601`). So omitting this does not fail -- it
        # degrades the CV rung quietly, which is the exact shape this whole
        # architecture exists to make impossible.
        #
        # ⚠️ AND THE TWO IMAGES GO TO DIFFERENT CONSUMERS ON PURPOSE. Erasing
        # staff lines before YOLO costs 7-13 pooled reading points, takes
        # noteheads to 0.774 on Mozart 41, and MANUFACTURES beam confusion
        # (YOLO beams 46 -> 105, precision 0.783 -> 0.343, firing on staff-line
        # residue). The rule is: ERASE FOR THE CV CONSUMER, BOUND THE SEARCH
        # FOR EVERYONE ELSE, NEVER ERASE FOR THE DETECTOR.
        remove_staff_lines(cells)
        out.append((pws, cells))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The three stages
# ─────────────────────────────────────────────────────────────────────────────


def run_staged(pdf_path: str, pages: Sequence[int], *,
               detector: Any = None, dpi: int = 600,
               conf_threshold: float = 0.25, imgsz: Optional[int] = None,
               dossier: Any = None, roster: Any = None,
               legacy: Optional[Dict[str, Dict[str, Any]]] = None,
               progress: bool = False) -> Dict[str, Any]:
    """GATHER -> ADJUDICATE -> EVALUATE, once, in that order.

    `legacy` is `{quantity: {subject_key: value}}` from `legacy.load`. Pass it
    here rather than gathering a second time to build the divergence table --
    see `run_staged_on`.
    """
    prepared = prepare_pages(pdf_path, pages, dpi=dpi)
    return run_staged_on(prepared, detector=detector,
                         conf_threshold=conf_threshold, imgsz=imgsz,
                         dossier=dossier, roster=roster, legacy=legacy,
                         progress=progress)


def run_staged_on(prepared: Sequence[Tuple[Any, Sequence[Any]]], *,
                  detector: Any = None, conf_threshold: float = 0.25,
                  imgsz: Optional[int] = None, dossier: Any = None,
                  roster: Any = None,
                  legacy: Optional[Dict[str, Dict[str, Any]]] = None,
                  progress: bool = False) -> Dict[str, Any]:
    """The stages, over pages someone else prepared.

    Split out so a test can drive the whole pipeline on a synthesized page
    with no PDF, no weights and no venv -- which is what makes the coherence
    tests cheap enough to run every time.

    ⚠️ `legacy` BUILDS THE DIVERGENCE TABLE FROM *THIS* LOG, and that is the
    whole point of the parameter. Until 2026-09-08 the CLI called this
    function and then, under `--against`, ran `prepare_pages` -> `gather` ->
    `adjudicate` A SECOND TIME and compared against that second log. So
    `result["adjudication"]` and `result["divergence"]` described two
    different passes -- which contradicts this module's own docstring, where
    "both paths consume the same detections and jitter cancels exactly" is
    given as a reason shadow mode is one process on one gather. Detector
    jitter is documented and real here: a from-scratch rebuild of the hairpin
    fix reproduced the categorical result and not the edit count, the same
    four boxes' confidences moving between runs on byte-identical code. It
    also doubled the runtime of every `--against` run.

    ⚠️ COMPUTED IMMEDIATELY AFTER ADJUDICATE, BEFORE GROUPS AND EVALUATE, and
    the position is the claim -- the same reasoning `groups` states for its
    own position. A consequence may RESTATE a value in the log, so a table
    built after EVALUATE would compare the legacy path against post-
    consequence values while calling them decisions. That is a different
    measurement, and a defensible one, but it is not the one the old code
    took and it must not change silently.
    """
    if progress:
        print("GATHER")
    log = gather.gather(prepared, detector=detector,
                        conf_threshold=conf_threshold, imgsz=imgsz,
                        dossier=dossier, roster=roster, progress=progress)

    if progress:
        print("ADJUDICATE")
    verdicts = adjudicate.run(log, progress=progress)

    # On THIS log, before any consequence can restate a value. See the
    # docstring -- the position is load-bearing, not incidental.
    divergence_report = None if legacy is None else divergence(log, legacy)

    # ⚠️ BETWEEN ADJUDICATE AND EVALUATE, and the position is the claim: the
    # verdict-sourced groups need the decisions to have run, and running
    # before EVALUATE means the report describes what was ADJUDICATED rather
    # than what a consequence later restated.
    if progress:
        print("GROUPS")
    agreement = groups.run(log, progress=progress)

    if progress:
        print("EVALUATE")
    report = evaluate.run(log, progress=progress)

    return {
        "record": log.to_json(),
        "summary": log.summary(),
        "adjudication": _adjudication_report(log, verdicts),
        # ⚠️ Redundant groups: several witnesses to ONE fact, and whether they
        # agree. It has NO CONSUMER today, deliberately -- seeing that
        # witnesses disagree is one job and acting on it is another. Surfaced
        # here rather than kept internal so it cannot become the ninth
        # complete recorder that recorded nothing.
        "agreement": agreement.to_json(),
        "evaluation": report.to_json(),
        "stubs": {
            "decisions": list(adjudicate.stubs()),
            "consequences": sorted(set(report.stubs)),
        },
        **({} if divergence_report is None
           else {"divergence": divergence_report}),
    }


def _adjudication_report(log: Log, verdicts: Sequence[Any]) -> Dict[str, Any]:
    """What ADJUDICATE did, split the way the design says to read it.

    ⚠️ DECIDED and ABSTAINED are reported APART, and abstentions are reported
    beside the REASON they carry rather than as a shortfall. A quantity with
    0 decided and 400 abstained is a decision working correctly on evidence
    it does not have; a quantity with 0 of both never ran. A single
    "coverage" number hides which one you are looking at -- and this project
    has already read one completeness figure as an accuracy figure
    (`slot_index` "193 of 193", cited as evidence the fact was RIGHT, from a
    probe that counts `len(slots)` and never which staff landed in which
    slot).
    """
    decided: Dict[str, int] = {}
    abstained: Dict[str, Dict[str, int]] = {}
    excluded: List[List[str]] = []
    missing: Dict[str, int] = {}

    for v in verdicts:
        if v.outcome is Outcome.DECIDED:
            decided[v.quantity] = decided.get(v.quantity, 0) + 1
        else:
            bucket = abstained.setdefault(v.quantity, {})
            bucket[v.reason] = bucket.get(v.reason, 0) + 1
        for q in v.missing:
            missing[q] = missing.get(q, 0) + 1
        for row_id, why in v.excluded:
            excluded.append([v.quantity, row_id, why])

    return {
        "decided": {k: decided[k] for k in sorted(decided)},
        "abstained": {k: abstained[k] for k in sorted(abstained)},
        "missing_evidence": {k: missing[k] for k in sorted(missing)},
        "excluded_as_circular": excluded,
        "n_verdicts": len(verdicts),
    }


# ─────────────────────────────────────────────────────────────────────────────
# The A/B
# ─────────────────────────────────────────────────────────────────────────────

#: How a (subject, quantity) pair compares between the two paths.
AGREE = "agree"
DIFFER = "differ"
NEW_ABSTENTION = "new_abstention"
NEW_DECISION = "new_decision"
LEGACY_ONLY = "legacy_only"
#: ⚠️ The two sides state the same fact in shapes that cannot be compared.
#: NOT folded into DIFFER -- see `_canonical`.
NOT_COMPARABLE = "not_comparable"

#: The mirror of `LEGACY_ONLY`: a staged verdict the legacy extractor carries
#: no counterpart for, so the comparison loop never reached it.
#:
#: ⚠️ THIS IS NOT A RESULT, IT IS A MEASURE OF THE TABLE'S OWN BLINDNESS.
#: A large number here means the divergence table is describing a fraction of
#: what the staged path decided, and the fraction is now stated instead of
#: being left for a reader to discover by counting quantities by hand.
STAGED_ONLY = "staged_only"


def _fifths_from_legacy_key(v: Any) -> Any:
    """`{'sharps': 0, 'flats': 2, ...}` -> `-2`, the staged path's own unit.

    ⚠️ THE TWO PATHS STATE THE KEY IN DIFFERENT UNITS AND `==` NEVER NOTICED.
    `transcribe` writes a dict; `adjudicators.header` returns `int(fifths)`.
    A dict never equals an int, so before 2026-09-08 EVERY key-signature row
    where both sides decided was reported DIFFER **by construction** --
    including perfect agreement. Measured on Beethoven 5 / Litolff p1: 4 of 4
    decided rows reported `differ`, and adjudicated against the dossier's
    written keys the staged path was RIGHT on 3 of them, so the table was
    accidentally telling the truth for the wrong reason.
    """
    if isinstance(v, dict) and ("sharps" in v or "flats" in v):
        return int(v.get("sharps") or 0) - int(v.get("flats") or 0)
    return v


def _instrument_name(v: Any) -> Any:
    """Compare instruments on the field BOTH sides carry, and only that.

    Legacy emits `{"name": ...}`; the staged path emits name plus family and
    more. Two dicts with different key sets are never equal, so this would
    have reported DIFFER on every decided row the day `instrument` stopped
    abstaining -- latent rather than observed, and found by asking what each
    adjudicator returns rather than by reading a table.

    ⚠️ Comparing on the shared field NARROWS the claim: agreement here means
    the two paths named the same instrument, NOT that they agree about family
    or transposition. The row keeps both raw values so that is checkable.
    """
    return v.get("name") if isinstance(v, dict) else v


#: Per-quantity adapters onto a shared representation. A quantity absent here
#: is compared as-is.
#:
#: ⚠️ THIS IS AN ADAPTER, NOT A COERCION. It may only re-express a value in
#: the other side's unit. It must never make two genuinely different readings
#: look equal -- that would manufacture agreement, which is worse than the
#: false disagreement it replaces, because a false DIFFER gets investigated
#: and a false AGREE does not.
_CANONICAL = {
    Q.KEY_SIGNATURE: _fifths_from_legacy_key,
    Q.INSTRUMENT: _instrument_name,
}


def _canonical(quantity: str, legacy_value: Any, staged_value: Any):
    """`(legacy, staged, comparable)` in a shared representation."""
    fn = _CANONICAL.get(quantity)
    if fn is not None:
        legacy_value, staged_value = fn(legacy_value), fn(staged_value)
    # ⚠️ A shape mismatch no adapter handles is its OWN outcome, counted, not
    # absorbed into DIFFER. The symbol ledger settled this principle already:
    # `uncorresponded` and `not_assessable` are first-class and are COUNTED.
    # Reporting "these disagree" about two things that were never comparable
    # is a claim the data does not support.
    scalar = (str, int, float, bool, type(None))
    if isinstance(legacy_value, dict) != isinstance(staged_value, dict):
        return legacy_value, staged_value, False
    if isinstance(legacy_value, scalar) and isinstance(staged_value, scalar):
        if isinstance(legacy_value, bool) != isinstance(staged_value, bool):
            return legacy_value, staged_value, False
    return legacy_value, staged_value, True



def _staves_touched(sub: Subject, legacy: Dict[str, Any]) -> int:
    """How many staves a disagreement at this subject reaches.

    The ranking key Step 2 asks for. A wrong clef on one staff is one staff
    wrong; a wrong staff COUNT on a system is wrong about every staff in it,
    and ranking them equally would put the cheap fix above the expensive one.

    ⚠️ The system's width is taken from the LEGACY extractor's own
    `system_staff_count`, not from the staged log -- because on exactly the
    rows where that quantity DIFFERS the two disagree about the answer, and
    ranking a disagreement by the staged side's number would let a decision
    inflate its own importance. Where legacy has no count the row falls back
    to 1, which under-ranks rather than over-ranks it.
    """
    if sub.kind in (Kind.STAFF, Kind.CELL, Kind.GLYPH):
        return 1
    if sub.kind is Kind.SYSTEM:
        n = legacy.get(Q.SYSTEM_STAFF_COUNT, {}).get(sub.to_key())
        return int(n) if isinstance(n, int) and n > 0 else 1
    # PAGE / DOCUMENT: every staff underneath it.
    total = 0
    for key, n in legacy.get(Q.SYSTEM_STAFF_COUNT, {}).items():
        other = Subject.from_key(key)
        if sub.contains(other) and isinstance(n, int):
            total += n
    return total or 1


def _basis_summary(log: Log, v: "Verdict | None") -> Dict[str, Any] | None:
    """What this verdict RESTED ON, as quantities rather than row ids.

    `Verdict.basis` is the ancestor closure -- the whole point of the record,
    and the thing that makes a divergence traceable to the decision that caused
    it ("this note is B" back through the clef, the key and the notehead
    position). Raw it is a list of opaque ids; translated into the quantities
    they carry it is readable, and the ids stay for anyone who wants to walk it.
    """
    if v is None or not v.basis:
        return None
    quantities: Dict[str, int] = {}
    for rid in v.basis:
        row = log.row(rid)
        if row is not None:
            quantities[row.quantity] = quantities.get(row.quantity, 0) + 1
    return {"rests_on": quantities, "n_rows": len(v.basis),
            "used": list(v.used), "ids": list(v.basis)}


def _coverage(log: Log, legacy: Dict[str, Any]) -> Dict[str, Any]:
    """Which quantities each side speaks about -- the table's own blind spots.

    ⚠️ Written because the shape of this failure is not a wrong number but a
    MISSING ONE, and a missing number looks like agreement. Stating both
    vocabularies makes "the extractor does not carry this" a fact on the
    record rather than something a reader has to notice.
    """
    staged = sorted({v.quantity for v in log.all_verdicts()})
    old = sorted(legacy)
    return {"legacy_quantities": old, "staged_quantities": staged,
            "compared": sorted(set(old) & set(staged)),
            "staged_not_extracted": sorted(set(staged) - set(old)),
            "legacy_not_decided": sorted(set(old) - set(staged))}


def divergence(log: Log, legacy: Dict[str, Any]) -> Dict[str, Any]:
    """Compare the staged verdicts against the legacy path's values.

    `legacy` is `{quantity: {subject_key: value}}` -- whatever the old
    pipeline concluded, extracted by the caller.

    ⚠️ `new_abstention` IS COUNTED SEPARATELY BECAUSE IT IS A FEATURE THAT
    SCORES AS A LOSS. musicdiff charges an absent element, so a decision that
    correctly declines to guess makes the pooled number WORSE. The precedent
    is already in the tree: `OMR_SLOT_STITCH` is structurally right, doubles
    its named bucket 715 -> 1,632, and ships default-off with the reason
    recorded. Read this column before reading any score.
    """
    rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {AGREE: 0, DIFFER: 0, NEW_ABSTENTION: 0,
                              NEW_DECISION: 0, LEGACY_ONLY: 0,
                              NOT_COMPARABLE: 0}

    for quantity, by_subject in sorted(legacy.items()):
        for subject_key, old in sorted(by_subject.items()):
            sub = Subject.from_key(subject_key)
            v = log.verdict(quantity, sub)
            if v is None:
                outcome = LEGACY_ONLY
                new = None
            elif v.outcome is Outcome.ABSTAINED:
                outcome = NEW_ABSTENTION
                new = None
            elif old is None:
                outcome = NEW_DECISION
                new = v.value
            else:
                new = v.value
                lc, sc, comparable = _canonical(quantity, old, new)
                if not comparable:
                    outcome = NOT_COMPARABLE
                else:
                    outcome = AGREE if lc == sc else DIFFER
            counts[outcome] += 1
            rows.append({"quantity": quantity, "subject": subject_key,
                         "legacy": old, "staged": new, "outcome": outcome,
                         "reason": v.reason if v is not None else None,
                         "staves_touched": _staves_touched(sub, legacy),
                         "basis": _basis_summary(log, v)})

    # ── the other direction ─────────────────────────────────────────────────
    # ⚠️ A STAGED VERDICT WITH NO LEGACY COUNTERPART WAS INVISIBLE, AND THIS
    # COMMENT USED TO BE THE WHOLE OF IT -- an unfinished sentence directly
    # above `return`. The loop above iterates `legacy.items()`, so a quantity
    # the extractor does not carry produced NO ROW AT ALL: not an agreement,
    # not a divergence, not a `legacy_only`, nothing. `LEGACY_ONLY` covers only
    # the opposite direction. Six of the fifteen wired decisions were in that
    # state -- `staff_group`, `group_symbol`, `part_partition`, `glyph_owner`,
    # `tuplet_ratio`, `duration` -- so a reader could total the table, find it
    # coherent, and never learn that 40% of the decisions were not in it.
    #
    # ⚠️ SUMMARISED PER QUANTITY RATHER THAN EMITTED AS ROWS, deliberately.
    # `duration` alone decides 113 subjects on ONE page and `glyph_owner` 60;
    # as rows they would swamp a table whose purpose is to be READ, and rank
    # above every real disagreement while comparing against nothing. A count
    # that says "113 duration verdicts have no legacy counterpart" is the
    # honest form of the same fact.
    staged_only: Dict[str, Dict[str, Any]] = {}
    for v in log.all_verdicts():
        if v.subject.to_key() in legacy.get(v.quantity, {}):
            continue
        e = staged_only.setdefault(v.quantity, {"decided": 0, "abstained": 0,
                                                "narrowed": 0, "kinds": {}})
        if v.outcome is Outcome.ABSTAINED:
            e["abstained"] += 1
        elif v.outcome is Outcome.NARROWED:
            e["narrowed"] += 1
        else:
            e["decided"] += 1
        k = v.subject.kind.value
        e["kinds"][k] = e["kinds"].get(k, 0) + 1
    counts[STAGED_ONLY] = sum(
        e["decided"] + e["abstained"] + e["narrowed"]
        for e in staged_only.values())

    # ── the ranking Step 2 actually asks for ────────────────────────────────
    # "a divergence list ranked by how many staves each disagreement touches,
    # each traceable to the decision that caused it". Rank the rows where the
    # two paths genuinely say different things -- an abstention is a separate
    # column on purpose (see the docstring) and does not belong in a list of
    # disagreements.
    ranked = sorted(
        (r for r in rows if r["outcome"] in (DIFFER, NOT_COMPARABLE)),
        key=lambda r: (-r["staves_touched"], r["quantity"], r["subject"]))

    return {"counts": counts, "rows": rows, "ranked": ranked,
            "staged_only": staged_only,
            "coverage": _coverage(log, legacy)}
