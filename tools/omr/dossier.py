"""Known facts about a work, and checks that hold the OMR output against them.

The five internal-consistency checks in `transcribe.py` can only ask whether the
page agrees with ITSELF. That makes them safe — they abstain wherever detection
is blind — but it also caps them: a page where every staff reads as treble is
perfectly self-consistent. `docs/dossier-verification-plan.md` calls this out
and asks for external truth. A dossier supplies it.

Dossiers are generated from MusicXML by `tools.omr.training.build_dossiers`,
so the facts are exact rather than remembered, and they are stored as WRITTEN
pitch — what is printed on the page, which is what the reader sees.

TWO TIERS, and the difference matters.

  ALIGNMENT-FREE checks compare sets and distributions and need no join between
  a dossier part and a printed staff. They are the trustworthy tier.

  SLOT-LEVEL checks need to know which staff is which. A printed score condenses
  (Flute 1 and 2 share a staff) and splits (divisi), so part index does not equal
  staff index: Beethoven 5's first movement has 18 parts and its pages carry 22
  staves. `benchmarks/omr-mxl-autolabel/FINDINGS.md` records forcing that join
  and reaching F1 0.064. So slot-level checks here run ONLY when the counts
  match exactly, and abstain otherwise.

Every check returns a list of warning dicts and never mutates its input. A page
that agrees with its dossier produces an empty list, so a clean run is unchanged.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DOSSIER_DIR = ROOT / "data" / "dossiers"


# ── loading ──────────────────────────────────────────────────────────────────

def load_dossier(path: str | Path) -> dict[str, Any]:
    """Load a dossier JSON file."""
    data = json.loads(Path(path).read_text())
    version = data.get("schema_version")
    if version != 3:
        raise ValueError(
            f"{path}: schema_version {version!r}, expected 3. Regenerate with "
            "tools.omr.training.build_dossiers."
        )
    return data


def find_dossier(work_id: str, dossier_dir: Path | None = None) -> dict[str, Any] | None:
    """Look up a dossier by work_id; None when there isn't one."""
    d = (dossier_dir or DOSSIER_DIR) / f"{work_id}.json"
    return load_dossier(d) if d.is_file() else None


def resolve_dossier(spec: str | Path | None,
                    dossier_dir: Path | None = None) -> dict[str, Any] | None:
    """Accept either a path to a dossier or a bare work_id."""
    if spec is None:
        return None
    p = Path(spec)
    if p.is_file():
        return load_dossier(p)
    return find_dossier(str(spec), dossier_dir=dossier_dir)


# ── the meter, which is the one fact worth feeding forward ───────────────────

def expected_meter(dossier: dict[str, Any]) -> dict[str, Any] | None:
    """The meter to hold a page to, or None when the dossier can't say.

    A work with a CONSTANT meter can answer for any page without knowing where
    the page sits in the piece. A work whose meter changes cannot: transcribe's
    `measure_index` is renumbered within each system and is not a piece-global
    count (`docs/dossier-verification-plan.md`, trap 2), so there is no way to
    tell which side of a change a given page falls on. It abstains rather than
    asserting the opening meter over a page that may be past a change.
    """
    if not dossier.get("constant_meter"):
        return None
    meter = dossier.get("starting_meter")
    if not meter:
        return None
    # Shaped like every other time_signature dict in the pipeline
    # (`rhythm.parse_time_signature`), so consumers need no special case. The
    # `source` tag marks it as not independently detected, exactly as
    # `backfill_page_time_signatures` marks its own.
    return {
        "numerator": int(meter["beats"]),
        "denominator": int(meter["beat_type"]),
        "source": "dossier",
    }


def meter_beats(meter: dict[str, Any]) -> float:
    """Bar length in quarter notes — the unit `rhythm.py` sums in."""
    return float(meter["numerator"]) * 4.0 / float(meter["denominator"])


# ── alignment-free checks ────────────────────────────────────────────────────

def _page_staves(page: dict[str, Any]):
    for sys_ in page.get("systems", []):
        for staff in sys_.get("staves", []):
            yield sys_, staff


def check_clef_vocabulary(page: dict[str, Any],
                          dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """A clef the work never prints is a misread, wherever it appeared.

    Needs no join: it is a membership test against the set of clefs the score
    actually uses.
    """
    allowed = set(dossier.get("clefs_used") or [])
    if not allowed:
        return []
    out = []
    for sys_, staff in _page_staves(page):
        clef = staff.get("clef")
        # A clef nothing read is the positional default, not a reading; holding
        # a default against the dossier would flag the pipeline's own fallback.
        if not clef or not staff.get("clef_source"):
            continue
        base = clef.split("_")[0]
        if base not in {c.split("_")[0] for c in allowed}:
            out.append({
                "check": "dossier_clef_vocabulary",
                "system_index": sys_.get("system_index"),
                "staff_index": staff.get("staff_index"),
                "read": clef,
                "source": staff.get("clef_source"),
                "allowed": sorted(allowed),
                "detail": (f"read clef {clef!r}, which {dossier['work_id']} "
                           f"never prints"),
            })
    return out


def check_key_vocabulary(page: dict[str, Any],
                         dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """A written key signature the work never prints is a misread."""
    allowed = set(dossier.get("written_fifths_used") or [])
    if not allowed:
        return []
    out = []
    for sys_, staff in _page_staves(page):
        ks = staff.get("key_signature") or {}
        fifths = ks.get("fifths")
        if fifths is None:
            continue
        # 0 is what a staff reports when nothing was read, so it cannot be
        # distinguished from a genuine C major and is never flagged.
        if fifths == 0 or fifths in allowed:
            continue
        out.append({
            "check": "dossier_key_vocabulary",
            "system_index": sys_.get("system_index"),
            "staff_index": staff.get("staff_index"),
            "read_fifths": fifths,
            "source": staff.get("key_signature_source", "detector"),
            "allowed": sorted(allowed),
            "detail": (f"read {abs(fifths)} "
                       f"{'sharp' if fifths > 0 else 'flat'}(s), which "
                       f"{dossier['work_id']} never prints"),
        })
    return out


def expected_clef_mix(dossier: dict[str, Any]) -> Counter:
    """How many parts are written in each clef."""
    return Counter(
        p["written_clef"] for p in dossier.get("parts", [])
        if p.get("written_clef")
    )


def check_clef_distribution(page: dict[str, Any],
                            dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """A page of an orchestral work should show a MIX of clefs.

    This is the check that sees the failure the self-consistency layer cannot:
    a page where every staff reads treble is entirely self-consistent, and
    entirely wrong. Scaled by staff count rather than asserting a join, so
    condensation and divisi do not break it.
    """
    mix = expected_clef_mix(dossier)
    n_parts = sum(mix.values())
    if n_parts == 0 or len(mix) < 2:
        return []  # a single-clef work has nothing to say here

    out = []
    for sys_ in page.get("systems", []):
        staves = sys_.get("staves", [])
        if len(staves) < 4:
            continue  # too few staves for a distribution to mean anything
        read = Counter(
            (s.get("clef") or "").split("_")[0] for s in staves
            if s.get("clef") and s.get("clef_source")
        )
        n_read = sum(read.values())
        if n_read == 0:
            continue
        for clef, count in mix.items():
            base = clef.split("_")[0]
            expected = count / n_parts * len(staves)
            # Only speak when the work leans on this clef enough that its total
            # absence cannot be a rounding artefact of a short system.
            if expected >= 1.5 and read.get(base, 0) == 0:
                out.append({
                    "check": "dossier_clef_absent",
                    "system_index": sys_.get("system_index"),
                    "clef": base,
                    "expected_at_least": round(expected, 1),
                    "staves_in_system": len(staves),
                    "clefs_read": dict(read),
                    "detail": (f"{dossier['work_id']} writes {count} of "
                               f"{n_parts} parts in {base} clef, so a system of "
                               f"{len(staves)} staves should show about "
                               f"{expected:.1f}; none were read"),
                })
    return out


def apply_meter(page: dict[str, Any],
                dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """Put the work's meter on the page, and report what it displaced.

    The dossier meter is not a vote — for a constant-meter work it is simply
    what the meter IS, so a detected meter that disagrees with it is a misread
    and gets replaced rather than merely flagged. Measured on an engraved
    Beethoven 5 excerpt, the detector read 4/4, 4/24 and 7/24 across a 2/4
    movement; two of those are not meters at all. Leaving them in place to
    preserve "detector independence" would mean knowingly shipping a bar length
    of 7/24 into the rhythm check that is about to use it.

    Every displacement is still returned as a warning, so overriding costs no
    visibility: the run reports exactly what it overruled.
    """
    meter = expected_meter(dossier)
    if meter is None:
        return []
    want = (meter["numerator"], meter["denominator"])
    displaced: list[dict[str, Any]] = []

    def _keep_symbol(ts: dict[str, Any] | None) -> dict[str, Any]:
        """The dossier's meter, carrying the page's own glyph where it agrees.

        THE NUMBERS COME FROM THE WORK; THE GLYPH COMES FROM THE PAGE. A work
        is in 2/2 in every edition of it, which is what a dossier can say. But
        whether THIS edition set that 2/2 as a stroked C or as two digits is a
        fact about the engraving, and only the page carries it — the dossier is
        built from one MusicXML file and cannot answer for the print in hand.

        So the override keeps `symbol` when the detector read the same meter the
        dossier asserts. It cannot travel on disagreement: a `timeSigCommon`
        read on a 3/4 movement is a misread, and its glyph is as wrong as its
        numbers. Absent a reading nothing is added and the export falls back to
        digits, exactly as before.

        Measured on the widened corpus: `symbol` was dropped on 5 of 9 works
        (Mozart 40/41, Brahms 4, Bruckner 5, Dvorak 9) at a flat 3 edits per
        staff, 270 edits total — and on none of the three works the benchmark
        used to consist of, all of which print digit meters.
        """
        out = dict(meter)
        if ts and ts.get("symbol") and (
            int(ts.get("numerator", 0)), int(ts.get("denominator", 0))
        ) == want:
            out["symbol"] = ts["symbol"]
        return out

    def _apply(container: dict[str, Any], sys_idx, staff_idx, measure_idx):
        ts = container.get("time_signature")
        if not ts:
            container["time_signature"] = dict(meter)
            return
        if ts.get("source"):
            # Already ours, or back-filled by a later pass; nothing detected.
            # A propagated reading may still carry the glyph it was read from.
            container["time_signature"] = _keep_symbol(ts)
            return
        got = (int(ts.get("numerator", 0)), int(ts.get("denominator", 0)))
        if got == want or not got[0] or not got[1]:
            container["time_signature"] = _keep_symbol(ts)
            return
        # 6/8 against an inferred 3/4 is the same bar length; the beat-sum path
        # cannot separate them and must not be called wrong for it.
        same_length = abs(
            meter_beats({"numerator": got[0], "denominator": got[1]})
            - meter_beats(meter)
        ) < 1e-6
        if not same_length:
            displaced.append({
                "check": "dossier_meter_disagreement",
                "system_index": sys_idx,
                "staff_index": staff_idx,
                "measure_index": measure_idx,
                "read": f"{got[0]}/{got[1]}",
                "expected": f"{want[0]}/{want[1]}",
                "detail": (f"detected {got[0]}/{got[1]} where "
                           f"{dossier['work_id']} is {want[0]}/{want[1]}; "
                           f"the dossier meter was used instead"),
            })
        container["time_signature"] = dict(meter)

    for sys_ in page.get("systems", []):
        for staff in sys_.get("staves", []):
            _apply(staff, sys_.get("system_index"),
                   staff.get("staff_index"), None)
            for m in staff.get("measures", []):
                _apply(m, sys_.get("system_index"), staff.get("staff_index"),
                       m.get("measure_index"))

    page["dossier_time_signature"] = dict(meter)
    return displaced


def check_meter(page: dict[str, Any],
                dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """Hold the page's meter against the work's, without changing it.

    Retained for callers that want the disagreement without the override —
    `apply_meter` is what the pipeline uses.
    """
    meter = expected_meter(dossier)
    if meter is None:
        return []
    want = (meter["numerator"], meter["denominator"])
    out = []
    for sys_, staff in _page_staves(page):
        for m in staff.get("measures", []):
            ts = m.get("time_signature")
            if not ts:
                continue
            # A meter this pipeline back-filled or seeded is not independent
            # evidence; only a genuinely detected one can disagree. Detected
            # meters are the ones carrying no `source` tag.
            if ts.get("source"):
                continue
            got = (int(ts.get("numerator", 0)), int(ts.get("denominator", 0)))
            if got == want:
                continue
            if not got[0] or not got[1]:
                continue
            # 6/8 and 3/4 are the same bar length; the beat-sum path cannot
            # tell them apart and must not be called wrong for it.
            if abs(meter_beats({"numerator": got[0], "denominator": got[1]})
                   - meter_beats(meter)) < 1e-6:
                continue
            out.append({
                "check": "dossier_meter_disagreement",
                "system_index": sys_.get("system_index"),
                "staff_index": staff.get("staff_index"),
                "measure_index": m.get("measure_index"),
                "read": f"{got[0]}/{got[1]}",
                "expected": f"{want[0]}/{want[1]}",
                "detail": (f"detected {got[0]}/{got[1]} where "
                           f"{dossier['work_id']} is {want[0]}/{want[1]}"),
            })
    return out


# ── slot-level checks, which run only when the join is safe ──────────────────

def check_slot_alignment(page: dict[str, Any],
                         dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-staff clef and key checks, when staff count equals part count.

    Abstains otherwise. Condensation and divisi mean the counts usually differ
    on real orchestral pages, and a forced join measured F1 0.064.
    """
    parts = dossier.get("parts") or []
    if not parts:
        return []
    out = []
    for sys_ in page.get("systems", []):
        staves = sys_.get("staves", [])
        if len(staves) != len(parts):
            continue
        for staff, part in zip(staves, parts):
            clef = staff.get("clef")
            if clef and staff.get("clef_source"):
                if clef.split("_")[0] != (part["written_clef"] or "").split("_")[0]:
                    out.append({
                        "check": "dossier_slot_clef",
                        "system_index": sys_.get("system_index"),
                        "staff_index": staff.get("staff_index"),
                        "part": part["name"],
                        "read": clef,
                        "expected": part["written_clef"],
                        "detail": (f"staff aligns to {part['name']}, written in "
                                   f"{part['written_clef']}, but read {clef}"),
                    })
            ks = (staff.get("key_signature") or {}).get("fifths")
            want = part.get("written_fifths")
            if ks is not None and want is not None and ks != 0 and ks != want:
                out.append({
                    "check": "dossier_slot_key",
                    "system_index": sys_.get("system_index"),
                    "staff_index": staff.get("staff_index"),
                    "part": part["name"],
                    "read_fifths": ks,
                    "expected_fifths": want,
                    "detail": (f"staff aligns to {part['name']}, written with "
                               f"fifths {want}, but read {ks}"),
                })
    return out


# ── seeding: the dossier as an INPUT, not only a judge ──────────────────────

def join_parts_to_slots(
    n_slots: int,
    dossier: dict[str, Any],
    labels: dict[int, str] | None = None,
) -> list[dict[str, Any] | None]:
    """Join this work's PARTS to a page's SLOTS, and say where to trust it.

    `slot_facts_for_system` requires part count == staff count, which is right
    for slot-level checking but silent on the pages that need the dossier most:
    a printed score condenses, so Beethoven 5's 18 parts reach a page as 11
    staves and the gate never opens.

    Score order is monotone, so the join is an alignment — the same one
    `score_layouts` runs against a standard layout, with gaps on both sides, a
    continuation move for a part printed on several staves, and a condensation
    move for several parts printed on one.

    **The evidence is the margin labels, deliberately, and never the clefs.**
    Clefs are what this join exists to supply, and scoring the join on them
    would be circular exactly where it matters. Labels come from `staff_labels`
    via slots, so a name read in one system reaches every system of the page.

    A label does more than score a pair. Where it resolves unambiguously it PINS
    its part, and the alignment runs only on the spans between pins — because the
    monotone path is right about score order and wrong about a particular
    engraving, and it is the margin that knows which. Beethoven 5 p.48 prints the
    timpani above the trombones where the part list has them below, and without
    pinning the three trombone staves are unreachable: 12 of 17 staves, against
    17 of 17 with. See `score_layouts.align_to_layout_pinned` and
    `benchmarks/omr-part-staff-join-2026-08/RESULTS.md`.

    Each entry carries `anchored`: whether that slot lies BETWEEN two labelled
    slots. Measured on Beethoven 5 p.2 and the Pastoral p.2, the join is right
    on 7 of 7 wind staves — including an unlabelled bassoon, pinned by the
    clarinets above and the horns below — and wrong on the string section,
    where there are no labels at all and nothing says whether the fifth string
    part is dropped or condensed onto the fourth staff. Between anchors the
    alignment has no room to slip; past the last one it is guessing.
    """
    from .score_layouts import ScoreLayout, align_to_layout_pinned
    from .instruments import AMBIGUOUS_ALIASES, lookup

    parts = dossier.get("parts") or []
    if not parts or n_slots <= 0:
        return [None] * max(0, n_slots)

    def canonical(name: str | None) -> str:
        match = lookup(name or "")
        return match.instrument.name if match else (name or "")

    # Canonical names on both sides, so "Bb Clarinet" from the work and
    # "Clarinetti" from the margin are the same instrument to the aligner.
    names = tuple(canonical(p.get("name")) for p in parts)
    layout = ScoreLayout(name=dossier.get("work_id", "dossier"), parts=names)
    # Which labels may PIN. An ambiguous alias may not: `Tp.` is Timpani or
    # Trumpet and `Basso` is a voice or the contrabasses, and POSITION is what
    # settles those — which is the one thing a pin takes off the table. The raw
    # text is the only place that judgement can be made, because canonicalising
    # has already picked a reading by the time the aligner sees it.
    #
    # It is the ALIAS that matched that must be tested, not the label. A margin
    # reads "Cor. 1. 2." as often as "Cor.", and the two are the same ambiguity;
    # testing the whole label lets the numbered form through and pins a staff on
    # a reading the lexicon itself will not commit to. "Corni 1. 2." is left
    # pinnable, because `corni` is not ambiguous — only the abbreviation is.
    def unambiguous(text: str | None) -> bool:
        match = lookup(text or "")
        return match is not None and match.alias not in AMBIGUOUS_ALIASES

    pinnable = {i for i, v in (labels or {}).items() if unambiguous(v)}
    absorbed: dict[int, list[int]] = {}
    assignment, _pins = align_to_layout_pinned(
        layout, n_slots,
        labels={i: canonical(v) for i, v in (labels or {}).items()},
        part_clefs=[p.get("written_clef") for p in parts],
        allow_merge=True,
        pinnable=pinnable,
        absorbed=absorbed,
    )
    # The assignment is part INDICES, not names: this work's parts repeat their
    # names — "Violin 1" and "Violin 2" are one instrument and two parts — and
    # only the index says which slot got which.

    anchored: set[int] = set()
    if labels:
        last = max(labels)
        anchored = set(range(min(labels), last + 1))
        anchored |= _determined_tail(absorbed, last, n_slots, len(parts))

    out: list[dict[str, Any] | None] = []
    for slot, index in enumerate(assignment):
        part = parts[index] if index is not None and 0 <= index < len(parts) else None
        out.append(
            {"clef": part.get("written_clef"), "fifths": part.get("written_fifths"),
             "part": part.get("name"), "anchored": slot in anchored}
            if part else None
        )
    return out


# Whether the staves BELOW the last label may be trusted too. Off by default is
# not an option here — the question is which rule, and there are three, two of
# which have been measured and lost.
# `OMR_TAIL_RULE` overrides it, so the arms can be compared without editing.
TAIL_RULE = os.environ.get("OMR_TAIL_RULE", "exact")   # "none" | "exact" | "all"


def _determined_tail(absorbed: dict[int, list[int]], last_label: int,
                     n_slots: int, n_parts: int) -> set[int]:
    """The staves below the last label, when the arithmetic leaves them no freedom.

    Past the last label the alignment is guessing, which is why `anchored` has
    always stopped there — and why the obvious fix of trusting to the foot of the
    system was measured and rejected at 50/52 -> 44/52.

    But "guessing" is not one thing. Count what is left: if the staves below the
    last label are exactly as many as the parts still unassigned above them, a
    monotone alignment has **one** option. It cannot merge (that would leave a
    staff empty), extend (same), or skip a part (same). There is nothing left to
    get wrong, and the earlier rejection was of trusting the tail
    UNCONDITIONALLY — where the count has slack, the guess is real.

    Measured on the three ground-truth pages: the two exact tails are right on
    11 of 11 staves (Beethoven 5 p.48's seven, the Pastoral's four), and
    Beethoven 5 p.2 — whose tail has five staves for seven parts, so two merges
    are free to land anywhere — is right on four of five and stays gated.

    `absorbed` rather than the assignment, because the count is the whole rule
    and the assignment cannot express a condensed staff: it reports one part per
    staff, so the second of a pair looks unconsumed and every tail below a
    condensation is reported as having one more part available than it has.
    """
    tail = list(range(last_label + 1, n_slots))
    if not tail or TAIL_RULE == "none":
        return set()
    if TAIL_RULE == "all":
        return set(tail)
    # Every part the staves above the tail actually took — including the ones a
    # CONDENSED staff absorbed, which the assignment alone does not report. The
    # Pastoral is the case: its horn staff takes both horn parts, and counting
    # from the assignment leaves the second one looking available.
    used = {part for slot, taken in absorbed.items() if slot <= last_label
            for part in taken}
    if not used:
        return set()
    free = [p for p in range(max(used) + 1, n_parts) if p not in used]
    return set(tail) if len(tail) == len(free) else set()


def slot_facts_for_system(n_staves: int,
                          dossier: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Per-staff written clef and key signature, or None when the join is unsafe.

    Same gate as `check_slot_alignment`, and for the same reason: a printed
    score condenses and splits, so part index equals staff index only when the
    two counts agree. Everything else abstains.

    This is what turns the dossier from a checker into a source. Clef DETECTION
    is the documented ceiling on the whole header layer — 2% coverage on
    orchestral scans — and it has already resisted a fine-tune (which collapsed
    dense-page noteheads), ensemble voting, and a CV locator. None of that
    matters if the clef is simply known.
    """
    parts = dossier.get("parts") or []
    if not parts or len(parts) != n_staves:
        return None
    return [
        {"clef": p.get("written_clef"), "fifths": p.get("written_fifths"),
         "part": p.get("name")}
        for p in parts
    ]


def slot_facts_for_page(n_staves_on_page: int,
                        dossier: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The same join, made against the whole PAGE rather than one system.

    Needed because system grouping is unreliable: measured on an engraved
    Brahms 1 excerpt, one musical system of 21 staves was reported as TWELVE
    systems of 1–5 staves, so a per-system join can never match a 21-part
    dossier even though the page is a perfect 1:1. Beethoven 5 splits 18 staves
    across 4 systems the same way.

    A conductor's page normally carries exactly one system, so page staff count
    equalling part count is the same evidence the per-system test was reaching
    for, and it survives the grouping being wrong. A page holding two real
    systems would count 2 × parts and fail this, which is the desired answer.

    Prefer `slot_facts_for_system` where it applies; this is the fallback.
    """
    return slot_facts_for_system(n_staves_on_page, dossier)


# ── whole-run check ──────────────────────────────────────────────────────────

def check_total_measures(result: dict[str, Any],
                         dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """Only meaningful when the whole work was transcribed.

    A partial run legitimately reads fewer measures, so this reports only the
    case that cannot be explained by partiality: MORE distinct measures than
    the work contains.
    """
    total = dossier.get("total_measures")
    if not total:
        return []
    per_page = []
    for page in result.get("pages", []):
        counts = [
            len(staff.get("measures", []))
            for _sys, staff in _page_staves(page)
        ]
        per_page.append(max(counts) if counts else 0)
    read = sum(per_page)
    if read <= total:
        return []
    return [{
        "check": "dossier_measure_overcount",
        "read_measures": read,
        "work_measures": total,
        "pages": len(per_page),
        "detail": (f"read {read} measures across {len(per_page)} page(s) but "
                   f"{dossier['work_id']} has only {total} in total — Phase 1 "
                   f"is splitting measures that are not there"),
    }]


# ── the entry point transcribe calls ─────────────────────────────────────────

# `check_meter` is deliberately absent: the meter is settled earlier by
# `apply_meter`, which reports its own disagreements. Running it again here
# would report nothing, because by this point the page carries the dossier's
# meter — the checks below are the ones that still have something to compare.
ALIGNMENT_FREE_CHECKS = (
    check_clef_vocabulary,
    check_key_vocabulary,
    check_clef_distribution,
)


def verify_page(page: dict[str, Any], dossier: dict[str, Any],
                *, slot_level: bool = True) -> list[dict[str, Any]]:
    """Run every page-scoped check and return the warnings."""
    out: list[dict[str, Any]] = []
    for check in ALIGNMENT_FREE_CHECKS:
        out.extend(check(page, dossier))
    if slot_level:
        out.extend(check_slot_alignment(page, dossier))
    return out


def summarize(warnings: list[dict[str, Any]]) -> dict[str, int]:
    """Counts by check name — what a run should print."""
    return dict(Counter(w["check"] for w in warnings))
