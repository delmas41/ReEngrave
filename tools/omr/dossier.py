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

    def _apply(container: dict[str, Any], sys_idx, staff_idx, measure_idx):
        ts = container.get("time_signature")
        if not ts:
            container["time_signature"] = dict(meter)
            return
        if ts.get("source"):
            # Already ours, or back-filled by a later pass; nothing detected.
            container["time_signature"] = dict(meter)
            return
        got = (int(ts.get("numerator", 0)), int(ts.get("denominator", 0)))
        if got == want or not got[0] or not got[1]:
            container["time_signature"] = dict(meter)
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
