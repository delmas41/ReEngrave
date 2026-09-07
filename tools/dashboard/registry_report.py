#!/usr/bin/env python3
"""Render `metric-registry.json` as one page: **% of achievable, higher is better.**

    python3 -m tools.dashboard.registry_report            # write HTML + MD
    python3 -m tools.dashboard.registry_report --check    # non-zero if stale
    python3 -m tools.dashboard.registry_report --strict   # warnings are errors
    python3 -m tools.dashboard.registry_report --serve    # preview on :8601

STANDALONE. `tools/dashboard/generate.py` and `docs/progress-dashboard.*` are
NOT touched — the dashboard integration is a proposal, and the diff for it is in
the report accompanying this build, unapplied.

────────────────────────────────────────────────────────────────────────────────
WHY THIS EXISTS, in Sean's words (2026-09-07): *"a single internal measurement
system … a quick read on the dashboard. Currently sometimes 1.000 is what we are
aiming for and other times it would be a horrible score."*

So: one unit, one direction, every row. The native value stays beside it — the
transform is reversible and the registry stores both — but the number a reader's
eye lands on always means the same thing.

⚠️ THE FAILURE THIS REBUILD EXISTS TO NOT REPEAT. A first renderer was rejected
for solving the INSTANCE rather than the CLASS: it hand-authored a section for
the one pair described to it in prose and never read `mandatory_caption`, the
generic mechanism the registry's author had built as a schema rule — the field
appeared zero times in 826 lines. Meanwhile the registry moved 0.2.0 → 0.3.0
beneath it with no version gate, so `ceiling.edition` — a field that did not
exist when it was written — was dropped in silence, and `Breitkopf` vanished
from a page a standing rule says must always carry it.

So every rule below is keyed on a SCHEMA PROPERTY and never on a row id. This
module contains no metric's name. Grep it: the only literal row identifiers here
are in nothing, by design.

SIX RULES, EACH ENFORCED IN CODE AND EACH WITH A TEST THAT FAILS WHEN IT IS
VIOLATED (`tools/dashboard/tests/test_registry_report.py`):

  R1 **`mandatory_caption` is rendered beside the number, in the same element.**
     Not a tooltip, not `title=`, not `<details>`. A row that REQUIRES a caption
     and cannot be given one is SKIPPED, loudly. Requirement is derived from the
     schema — the key being present and non-None, or `ceiling.edition` being set
     — never from a list of ids, so a caption cannot be deleted into compliance.

  R2 **The schema version is gated.** This consumer declares what it understands
     and refuses anything else with a non-zero exit naming the version. It also
     refuses a registry naming a `fields_a_consumer_may_never_drop` entry this
     build does not handle — which is the Breitkopf failure caught by mechanism
     rather than by luck.

  R3 **The edition clause is verified, not assumed.** A row with `ceiling.edition`
     must name that edition inside its caption. The build enforces it; this
     re-checks it, because the whole point of the clause is that a consumer
     cannot be trusted to read a field it does not know about.

  R4 **`--strict` gates.** Every warning — missing evidence file, skipped row,
     unhandled contract field — becomes a non-zero exit. A live WARN beside a
     zero exit is how the first build reported its own missing evidence.

  R5 **Head-to-head groups on `comparable_as.head_to_head` and nothing else.**
     Never on `ceiling.kind`: that is what filed a pre-registered admission bar
     under a heading reading "different system". A fallback exists for rows with
     no key and is LABELLED as a fallback; a keyless row is never filed under a
     declared group.

  R6 **The page cannot end on a flattering number.** Rows are only ever adjacent
     inside an era group whose header states the sample, cross-cutting rows
     (`family: "both"`) are met FIRST and never terminate the document, and the
     last section is always the inventory of what nothing measures. A green
     97.07 landing immediately after a red 1.01 is the worst available last
     impression and is now structurally unreachable.

AND THE UNIT'S OWN TRAP, handled generically: `scoreable: false` NEVER renders as
a number and never as 100. It gets no bar at all — a zero-length bar reads as 0%
and a fabricated 100 is the worst outcome available here.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "benchmarks" / "omr-pipeline-audit-2026-09"
REGISTRY = AUDIT / "metric-registry.json"
OUT_HTML = AUDIT / "registry-report.html"
OUT_MD = AUDIT / "registry-report.md"

# ── R2: what this consumer declares ──────────────────────────────────────────

#: Bump ONLY together with a read of `changes_since_*`. Silent forward
#: compatibility is the failure family this page exists to expose.
UNDERSTOOD_SCHEMA_VERSIONS = ("0.5.0",)

#: `consumer_contract.fields_a_consumer_may_never_drop`, as this build handles
#: them. A registry naming a field NOT in this set is refused — that is the
#: mechanism that would have caught `ceiling.edition` arriving in 0.3.0.
HANDLED_NEVER_DROP_FIELDS = {
    "mandatory_caption",
    "ceiling.edition (via the edition clause)",
    "render_with",
}

GREEN, AMBER = 90.0, 60.0

#: A ceiling with evidence behind it. Everything else is drawn hatched, because
#: a row scored against a guess and one scored against a corroborated ceiling
#: must not look alike.
TRUSTED_CEILING_STATUS = {
    "measured", "measured_directly", "measured_and_corroborated",
    "measured_single_source", "pre_registered", "bounded_above", "bounded_below",
}

FAMILY_ORDER = ["both", "engraved", "scan"]
FAMILY_TITLE = {
    "both": "Cross-cutting — belongs to neither family",
    "engraved": "Digitally engraved input",
    "scan": "Scanned input",
}
FAMILY_NOTE = {
    "both": "⚠️ Rendered FIRST and never last. A cross-cutting row shares no ceiling, "
            "no era and no sample with either family below it, so it may not be read "
            "against them — and a high one placed after a low one reads as a verdict "
            "on the low one.",
    "engraved": "Fixtures we render ourselves, so the ink is known by construction. "
                "Says nothing about scan robustness.",
    "scan": "Real printed pages. ⚠️ Every scan row is <b>% of achievable under page "
            "fidelity</b> (<code>ceiling.constraint</code>) — the metric's unconstrained "
            "floor is zero, reachable by emitting the encoding instead of the page, "
            "which this project calls an anti-feature.",
}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def prose(s) -> str:
    """Registry prose, display-normalised.

    ⚠️ Four `why_not` strings arrive with a doubled `%%` from a format string in
    the builder. Repairing that belongs to the registry's author (reported, not
    patched here — the file is frozen); rendering `6.9%%` at a reader would be
    the renderer inventing a defect of its own.
    """
    return str(s).replace("%%", "%")


# ── loading, and the refusals that come before any rendering ─────────────────

class Refused(SystemExit):
    def __init__(self, msg: str, code: int = 3):
        print("REFUSING TO RENDER: " + msg, file=sys.stderr)
        super().__init__(code)


def load_registry(path: Path = REGISTRY) -> dict:
    if not path.exists():
        raise Refused(
            f"no registry at {path}.\n"
            "  Regenerate with probe/build_metric_registry.py — see "
            "benchmarks/omr-pipeline-audit-2026-09/README-metric-registry.md", 2)
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise Refused(f"{path} is not valid JSON: {exc}", 2)


def gate_schema_version(reg: dict) -> None:
    """R2. Refuse anything this build was not written against, by NAME."""
    got = reg.get("schema_version")
    if got not in UNDERSTOOD_SCHEMA_VERSIONS:
        raise Refused(
            f"registry schema_version is {got!r}; this consumer understands "
            f"{list(UNDERSTOOD_SCHEMA_VERSIONS)}.\n"
            "  A renderer that reads a schema it was not written against drops "
            "the fields it does not know about IN SILENCE — that is exactly how "
            "`ceiling.edition` was lost when 0.2.0 met 0.3.0, taking the "
            "publisher off a ceiling a standing rule says must always carry it.\n"
            "  Read `changes_since_*` in the registry, handle what changed, then "
            "add the version to UNDERSTOOD_SCHEMA_VERSIONS.")

    contract = reg.get("consumer_contract")
    if not contract:
        raise Refused(
            "the registry declares no `consumer_contract`. A conforming registry "
            "always carries one; without it there is nothing to gate on and this "
            "consumer cannot tell what it is required to render.")
    current = contract.get("current")
    if current is not None and current != got:
        raise Refused(
            f"consumer_contract.current is {current!r} but schema_version is "
            f"{got!r} — the registry disagrees with itself; refusing rather than "
            "picking one.")

    declared = contract.get("understood_by_a_conforming_consumer")
    if declared is not None and got not in declared:
        raise Refused(
            f"the registry's own contract does not list {got!r} as understandable "
            f"by a conforming consumer ({declared!r}).")

    # ⚠️ ABSENCE IS NOT AN EMPTY LIST. Reading a missing key as `[]` made the
    # whole clause vanish: a registry that simply omitted
    # `fields_a_consumer_may_never_drop` sailed through and exited 0. The one
    # thing this check exists to catch is a consumer not knowing what it is
    # required to render — and "the list is gone" is the loudest form of that.
    if "fields_a_consumer_may_never_drop" not in contract:
        raise Refused(
            "the contract carries no `fields_a_consumer_may_never_drop` list. "
            "That list IS the mechanism by which a consumer learns what it must "
            "not silently drop; its absence defeats the check rather than "
            "passing it.")
    unhandled = [f for f in (contract.get("fields_a_consumer_may_never_drop") or [])
                 if f not in HANDLED_NEVER_DROP_FIELDS]
    if unhandled:
        raise Refused(
            "the contract names fields a consumer may never drop that this build "
            f"does not handle: {unhandled}.\n"
            "  Refusing is the whole mechanism: a field a consumer does not know "
            "about is a field it drops silently.")


# ── R1 + R3: the caption rules, keyed on the schema and never on an id ───────

def caption_required(row: dict) -> tuple[bool, str]:
    """Does this row REQUIRE a caption beside its number, and why?

    Derived from the schema so that a caption cannot be deleted into compliance:
      * the key is present and non-None  → the registry declared one;
      * `ceiling.edition` is set         → the 0.4.0 edition clause.
    """
    reasons = []
    if "mandatory_caption" in row and row["mandatory_caption"] is not None:
        reasons.append("the row declares `mandatory_caption`")
    if (row.get("ceiling") or {}).get("edition"):
        reasons.append("`ceiling.edition` is set (edition clause)")
    return bool(reasons), " and ".join(reasons)


def _edition_terms(edition: str) -> list[str]:
    """The words a caption must contain to have named the edition.

    The head of the field, before its first em dash, is the edition itself
    ("Breitkopf & Härtel, Brahms 1 mvt 1"); anything after it is commentary.
    Capitalised words of four letters or more are the identifying ones.
    """
    head = re.split(r"\s[—–-]\s", str(edition), maxsplit=1)[0]
    return [w for w in re.findall(r"[^\W\d_]{4,}", head, flags=re.UNICODE)
            if w[:1].isupper()]


def caption_problem(row: dict) -> str | None:
    """None if the row may be rendered; a sentence naming the fault otherwise.

    ⚠️ The registry's rule: *a renderer that cannot show the caption MUST NOT
    show the row.* So this returns a reason to SKIP, never a reason to degrade.
    """
    required, why = caption_required(row)
    if not required:
        return None
    text = row.get("mandatory_caption")
    if not (isinstance(text, str) and text.strip()):
        return (f"{why}, but `mandatory_caption` is "
                f"{'absent' if text is None else 'empty'} — there is nothing to "
                "place beside the number, so the row is withheld rather than "
                "rendered bare.")
    edition = (row.get("ceiling") or {}).get("edition")
    if edition:
        missing = [t for t in _edition_terms(edition)
                   if t.lower() not in text.lower()]
        if missing:
            return ("`ceiling.edition` is set and the caption does not name it "
                    f"(missing {missing!r}). A publisher-scoped ceiling quoted "
                    "without its publisher is the exact defect the edition "
                    "clause exists to prevent.")
    return None


# ── grouping ─────────────────────────────────────────────────────────────────

def bind_groups(rows: list[dict]) -> tuple[list[list[dict]], list[tuple[str, str, str]]]:
    """`render_with` — rows that must be READ TOGETHER, per the schema.

    ⚠️ WHY THIS IS NOT `era_key`. An earlier build of this renderer held the
    ledger screen/defect pair together by grouping on `era_key`, and reported
    that as the rule working. It was not: `era_key` says two numbers were MADE
    under the same conditions, `render_with` says they may only be READ
    together, and the two coincided here for one run only. Measured on that
    page the pair sat 200 px apart with a full metadata row between them, and
    the flattering number rendered ABOVE the caveat. Re-measure either row on
    another corpus and the era key changes and the pair separates with nothing
    failing. A rule whose enforcement evaporates when an unrelated field moves
    is not a rule.

    (The era grouping is KEPT, for what it is actually good at: it puts the
    five blind engraved stages inside the era that produces the 88.78 %
    headline. That contextualises a family; this binds a pair.)

    Returns the groups (transitively closed) and any symmetry faults. Symmetry
    is build-enforced upstream; it is re-checked here for the same reason the
    edition clause is — the point of a never-drop field is that a consumer
    cannot be trusted to have read it.
    """
    by_id = {r["id"]: r for r in rows}
    faults: list[tuple[str, str, str]] = []

    parent: dict[str, str] = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for r in rows:
        for other in (r.get("render_with") or []):
            if other not in by_id:
                faults.append((r["id"], "render_with names a row that is not in "
                                        "the registry", other))
                continue
            if r["id"] not in (by_id[other].get("render_with") or []):
                faults.append((r["id"], "render_with is one-sided — the named row "
                                        "does not name it back", other))
                continue
            union(r["id"], other)

    clusters: dict[str, list[dict]] = {}
    for rid in list(parent):
        clusters.setdefault(find(rid), []).append(by_id[rid])

    # ⚠️ ANTI-FLATTERING ORDER, and it is the defect that was measured: an
    # unscoreable member carries the caveat and a scoreable one carries the
    # number, so the caveat goes FIRST. Within each half, worst first.
    out = []
    for members in clusters.values():
        members.sort(key=lambda m: (bool(m.get("scoreable")),
                                    m.get("pct_of_achievable") if m.get("scoreable")
                                    else 0))
        out.append(members)
    out.sort(key=lambda g: g[0]["id"])
    return out, faults


def era_groups(rows: list[dict]) -> list[dict]:
    """Rows measured on the same sample, kept together.

    ⚠️ THE CLASS, not the instance. The registry's showcase pair — a screening
    rate that is NOT a defect rate, beside the defect rate it is seven times
    larger than — shares one `era_key`, one `n` and one source. So does every
    other pair whose scopes a reader could confuse, including five stages whose
    harness is blind sitting inside the era that yields the headline. Grouping
    on the era key makes ALL of them adjacent; naming the one pair in prose
    would have made only that one adjacent.
    """
    by_key: dict[str, list[dict]] = {}
    order: list[str] = []
    for r in rows:
        k = r.get("era_key") or "(no era key declared)"
        if k not in by_key:
            by_key[k] = []
            order.append(k)
        by_key[k].append(r)

    groups = []
    for k in order:
        members = by_key[k]
        scored = [m for m in members if m.get("scoreable") and m.get("pct_of_achievable") is not None]
        # Worst first: a section that opens on its best figure flatters.
        rank = min((m["pct_of_achievable"] for m in scored), default=-1.0)
        members = (sorted(scored, key=lambda m: -m["pct_of_achievable"])
                   + [m for m in members if m not in scored])
        groups.append({
            "era_key": k,
            "rows": members,
            "rank": rank,
            "mixed": bool(scored) and len(scored) != len(members),
            "n_scored": len(scored),
            "n_blind": sum(1 for m in members
                           if (m.get("ceiling") or {}).get("kind") == "visibility"),
        })
    groups.sort(key=lambda g: (g["rank"], g["era_key"]))
    return groups


def head_to_head(rows: list[dict]) -> tuple[list[tuple[str, list[dict]]], list[dict]]:
    """R5. Declared groups first, then a LABELLED fallback.

    Grouping on `ceiling.kind` is refused outright: `competitive` means another
    system and nothing else, and a kind-keyed group once swallowed a
    pre-registered human admission bar under a heading reading "different
    system". The fallback below collects rows whose kind says competitive but
    which declare NO key — it is never merged into a declared group.
    """
    declared: dict[str, list[dict]] = {}
    for r in rows:
        k = (r.get("comparable_as") or {}).get("head_to_head")
        if k:
            declared.setdefault(k, []).append(r)
    fallback = [r for r in rows
                if (r.get("ceiling") or {}).get("kind") == "competitive"
                and not (r.get("comparable_as") or {}).get("head_to_head")]
    return sorted(declared.items()), fallback


# ── presentation helpers ─────────────────────────────────────────────────────

def band(pct) -> str:
    if pct is None:
        return "none"
    return "green" if pct >= GREEN else ("amber" if pct >= AMBER else "red")


def trusted(row: dict) -> bool:
    return (row.get("ceiling") or {}).get("status") in TRUSTED_CEILING_STATUS


def native_str(row: dict) -> str:
    v, m = row.get("value"), row.get("raw_metric")
    if v is None:
        return f"{m}: not a point value"
    d = "lower is better" if row.get("native_direction") == "lower_is_better" else "higher is better"
    return f"native {v:.4g} — {m} ({d})"


def noise_str(row: dict) -> str:
    nf = row.get("noise_floor")
    if not nf:
        return ("no repeat-run noise floor — <b>a delta on this row cannot be "
                "gated</b>")
    st = nf.get("status", "?")
    return f"noise floor ±{nf.get('value_edits')} edits ({esc(st)})"


def ceiling_str(row: dict) -> str:
    c = row.get("ceiling") or {}
    kind, status = c.get("kind"), c.get("status")
    val = c.get("value")
    bits = [f"ceiling {esc(kind or 'none')}"]
    if val is not None:
        bits.append(f"= {val:g}")
    bits.append(f"· {esc(status or 'unstated')}")
    return " ".join(bits)


def comparability_chips(row: dict) -> str:
    ca = row.get("comparable_as") or {}
    out = []
    if ca.get("time_series"):
        out.append('<span class="chip ts" title="may be differenced over time">Δ '
                   + esc(ca["time_series"]) + "</span>")
    else:
        out.append('<span class="chip no">no time-series key — may not be differenced</span>')
    if ca.get("head_to_head"):
        out.append('<span class="chip h2h" title="same fixtures, same scorer, '
                   'different SYSTEM — not a delta">vs ' + esc(ca["head_to_head"]) + "</span>")
    return "".join(out)


# ── row rendering ────────────────────────────────────────────────────────────

def row_html(row: dict) -> str:
    """One row. R1 lives here: the caption is a CHILD OF THE HEADLINE BLOCK,
    the same element that holds the number, and there is no code path that
    places it anywhere else."""
    rid = esc(row["id"])
    scoreable = bool(row.get("scoreable"))
    pct = row.get("pct_of_achievable")
    cap = row.get("mandatory_caption")
    kind = (row.get("ceiling") or {}).get("kind")

    badges = []
    if kind == "visibility":
        badges.append('<span class="badge blind">HARNESS BLIND</span>')
    if scoreable:
        badges.append('<span class="badge %s">%s CEILING</span>'
                      % ("measured" if trusted(row) else "assumed",
                         esc((row.get("ceiling") or {}).get("status", "?")).upper()))

    if scoreable and pct is not None:
        number = ('<div class="pct %s">%.2f<span class="pctunit">%% of achievable</span></div>'
                  % (band(pct), pct))
    else:
        # ⚠️ No bar, no number, no zero. A zero-length bar reads as 0% and a
        # fabricated 100 is the worst outcome available on this page.
        number = '<div class="pct unscoreable">unscoreable</div>'

    caption_html = ""
    if cap:
        caption_html = ('<p class="mandatory-caption"><span class="capmark">'
                        'MUST BE READ WITH THIS NUMBER</span> %s</p>' % esc(prose(cap)))

    bar = ""
    if scoreable and pct is not None:
        bar = ('<div class="bar"><div class="fill %s %s" style="width:%.2f%%"></div></div>'
               % (band(pct), "solid" if trusted(row) else "hatched", max(0.0, min(100.0, pct))))

    why = ""
    if not scoreable:
        why = '<p class="whynot">%s</p>' % esc(prose(row.get("why_not") or "no reason recorded"))

    # `companions` are the counts the ratio was computed FROM. Rendered
    # generically for every row that has them, because a ratio whose companion
    # moves the other way is dilution rather than improvement — and because on
    # one row the companion IS the neighbouring figure a reader must see.
    comp = row.get("companions") or {}
    comp_html = ""
    if comp:
        comp_html = ('<div class="companions"><span class="complabel">measured '
                     'alongside</span>%s</div>'
                     % "".join('<span class="comp"><b>%s</b> %s</span>'
                               % (esc(k), esc(v if not isinstance(v, dict)
                                              else json.dumps(v)))
                               for k, v in comp.items()))

    flags = "".join('<li>%s</li>' % esc(prose(f)) for f in (row.get("flags") or []))
    flags = ('<ul class="flags">%s</ul>' % flags) if flags else ""

    trust = (
        '<div class="trust">'
        '<span>n = %s %s</span><span>%s</span><span>%s</span><span>%s</span>'
        '</div>' % (esc(row.get("n") if row.get("n") is not None else "—"),
                    esc(row.get("n_unit") or ""),
                    ceiling_str(row), noise_str(row), esc(native_str(row))))

    return (
        '<article class="row" data-row-id="%s" data-scoreable="%s" data-family="%s"'
        ' data-has-caption="%s">\n'
        '  <div class="headline">%s<div class="idblock"><h4>%s</h4>'
        '<div class="stage">%s</div></div><div class="badges">%s</div>%s</div>\n'
        '  %s%s%s%s%s\n'
        '  <div class="chips">%s</div>\n'
        '  <div class="src">%s</div>\n'
        '</article>\n'
    ) % (rid, "true" if scoreable else "false", esc(row.get("family")),
         "true" if cap else "false",
         number, rid, esc(row.get("stage") or ""), "".join(badges), caption_html,
         bar, why, trust, comp_html, flags,
         comparability_chips(row),
         _evidence_html(row))


def _evidence_html(row: dict) -> str:
    """Openable paths and prose pointers, kept apart.

    v0.5.0 split `ceiling.evidence_prose` out of `evidence` precisely because a
    pointer like "CLAUDE.md · OMR_CHOIR_GROUPING" cannot be opened or existence-
    checked. Rendering the two as one list would put them back together.
    """
    c = row.get("ceiling") or {}
    bits = []
    paths = [esc(e) for e in (c.get("evidence") or [])]
    if paths:
        bits.append("evidence: " + ", ".join(paths))
    prose_ptrs = [esc(e) for e in (c.get("evidence_prose") or [])]
    if prose_ptrs:
        bits.append("<i>not an openable path:</i> " + "; ".join(prose_ptrs))
    if not bits:
        bits.append("evidence: " + esc(row.get("source") or "—"))
    return " · ".join(bits)


def group_html(g: dict) -> str:
    banner = ""
    if g["mixed"]:
        banner = ('<p class="mixbanner">⚠️ One sample, %d scored row%s and %d that '
                  'cannot be scored. Printed together because either half alone '
                  'misleads: a number here is not a verdict on what stands beside '
                  'it unmeasured, and an unscoreable row is not a failing one.</p>'
                  % (g["n_scored"], "" if g["n_scored"] == 1 else "s",
                     len(g["rows"]) - g["n_scored"]))
    return ('<section class="eragroup"><header class="erahead">'
            '<span class="eralabel">sample</span><code>%s</code>'
            '<span class="eracount">%d row%s</span></header>%s%s</section>\n'
            % (esc(g["era_key"]), len(g["rows"]), "" if len(g["rows"]) == 1 else "s",
               banner, "".join(row_html(r) for r in g["rows"])))


def _short_number(row: dict) -> str:
    """The figure alone, for the paired strip at the head of a bound block."""
    pct = row.get("pct_of_achievable")
    if row.get("scoreable") and pct is not None:
        return '<span class="bindpct %s">%.2f%%</span>' % (band(pct), pct)
    return '<span class="bindpct unscoreable">unscoreable</span>'


def bind_block_html(members: list[dict]) -> str:
    """One block; the NUMBERS adjacent, with nothing between them.

    ⚠️ Being inside one bordered box is not "rendered together" — that was the
    measured failure. So the members' figures are lifted into a single strip at
    the head of the block, side by side, before any metadata: whatever a row's
    detail rows do below, no scoreable row can come between the two numbers,
    which is what the schema rule requires.
    """
    strip = "".join(
        '<div class="bindside">%s<code>%s</code><span class="bindmetric">%s</span></div>'
        % (_short_number(m), esc(m["id"]), esc(m.get("raw_metric") or ""))
        for m in members)
    return ('<section class="bindgroup"><header class="bindhead">'
            '<span class="bindlabel">bound by <code>render_with</code></span>'
            '<span class="bindnote">These %d figures may only be read together. '
            'Either alone misleads in a named direction.</span></header>'
            '<div class="bindstrip">%s</div>%s</section>\n'
            % (len(members), strip, "".join(row_html(m) for m in members)))


def _rank(rows: list[dict]) -> float:
    """Worst first; a block with no number at all sorts ahead of every number."""
    scored = [r["pct_of_achievable"] for r in rows
              if r.get("scoreable") and r.get("pct_of_achievable") is not None]
    return min(scored) if scored else -1.0


def family_blocks(fam_rows: list[dict], binds: list[list[dict]]) -> list[str]:
    """Era groups and bound blocks, interleaved worst-first.

    A bound group is rendered ONCE, in the family of its worst member, and its
    members are withheld from era grouping everywhere — otherwise a pair
    spanning two families would print twice and the adjacency rule would be
    satisfied in one place and broken in the other.
    """
    fam = fam_rows[0].get("family") if fam_rows else None
    bound_here, bound_ids = [], set()
    for members in binds:
        bound_ids.update(m["id"] for m in members)
        home = min(members, key=lambda m: (m.get("pct_of_achievable")
                                           if m.get("scoreable") and
                                           m.get("pct_of_achievable") is not None
                                           else -1.0))
        if home.get("family") == fam:
            bound_here.append(members)

    blocks = [(_rank(g["rows"]), group_html(g))
              for g in era_groups([r for r in fam_rows if r["id"] not in bound_ids])]
    blocks += [(_rank(m), bind_block_html(m)) for m in bound_here]
    blocks.sort(key=lambda b: b[0])
    return [html for _rank_, html in blocks]


# ── page ─────────────────────────────────────────────────────────────────────

CSS = """
:root{--bg:#fbfbfa;--fg:#1d1c1a;--mut:#6b6862;--line:#e2ded7;--card:#fff;
--green:#1a7f4b;--amber:#a5741a;--red:#a5301f;--blue:#2a4f7c;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--bg:#16181a;--fg:#e9e6e1;--mut:#9b968e;--line:#2e3236;--card:#1d2023;
--green:#4cc38a;--amber:#e0b341;--red:#f06d5a;--blue:#7aa7dd;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 96px}
h1{font-size:26px;margin:0 0 6px}
h2{font-size:20px;margin:44px 0 4px;padding-top:18px;border-top:2px solid var(--line)}
h3{font-size:15px;margin:22px 0 6px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
h4{font-size:14px;margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.lede{color:var(--mut);max-width:74ch}
.unitbar{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--blue);
padding:12px 14px;border-radius:6px;margin:16px 0}
.eragroup{margin:16px 0 26px;border:1px solid var(--line);border-radius:8px;
background:var(--card);overflow:hidden}
.erahead{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;
padding:8px 12px;background:color-mix(in srgb,var(--line) 40%, transparent);
border-bottom:1px solid var(--line)}
.eralabel{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}
.eracount{margin-left:auto;font-size:11px;color:var(--mut)}
.mixbanner{margin:0;padding:9px 12px;font-size:13px;background:color-mix(in srgb,var(--amber) 12%, transparent);
border-bottom:1px solid var(--line)}
.row{padding:14px 14px 12px;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}
/* `width:100%` is explicit rather than inherited — a grid container should not
   depend on shrink-to-fit for a rule whose evidence is geometric.
   ⚠️ IT IS NOT THE FIX FOR THE REVIEWER'S ZERO-WIDTH READING, and saying so
   would be a mechanism claimed without measurement. Re-measured 2026-09-07:
   in that browser state `innerWidth` and `document.body` are BOTH 0 — the pane
   was hidden, so every element on the page measured zero and the screenshots
   came back blank from the same cause. In a live pane earlier the same day the
   headline measured normally and the captions read 20-38 px under their
   numbers at >100 px wide. The kept change is defensive, not corrective. */
.headline{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:start;width:100%}
.pct{font-size:30px;font-weight:640;line-height:1;font-variant-numeric:tabular-nums;
min-width:132px}
.pctunit{display:block;font-size:10px;font-weight:400;color:var(--mut);letter-spacing:.04em}
.pct.green{color:var(--green)}.pct.amber{color:var(--amber)}.pct.red{color:var(--red)}
.pct.unscoreable{font-size:16px;color:var(--mut);font-weight:600;text-transform:uppercase;
letter-spacing:.06em;padding-top:6px}
.stage{font-size:12px;color:var(--mut)}
.badges{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.badge{font-size:10px;letter-spacing:.06em;padding:2px 6px;border-radius:3px;border:1px solid var(--line)}
.badge.measured{color:var(--green);border-color:var(--green)}
.badge.assumed{color:var(--amber);border-color:var(--amber)}
.badge.blind{color:var(--mut)}
/* R1: the caption sits INSIDE .headline, spanning all three columns, directly
   under the number. There is no disclosure, no tooltip and no flag. */
.mandatory-caption{grid-column:1/-1;margin:8px 0 0;padding:9px 11px;font-size:13px;
background:color-mix(in srgb,var(--red) 10%, transparent);
border-left:3px solid var(--red);border-radius:0 5px 5px 0}
.capmark{display:block;font-size:9.5px;letter-spacing:.11em;color:var(--red);margin-bottom:3px}
.bar{height:7px;background:color-mix(in srgb,var(--line) 70%, transparent);
border-radius:4px;margin:11px 0 9px;overflow:hidden}
.fill{height:100%}
.fill.green{background:var(--green)}.fill.amber{background:var(--amber)}.fill.red{background:var(--red)}
.fill.hatched{background-image:repeating-linear-gradient(45deg,
rgba(255,255,255,.55) 0 3px,transparent 3px 7px)}
.whynot{margin:10px 0;padding:10px 12px;font-size:13px;border:1px dashed var(--line);
border-radius:5px;color:var(--fg);background:color-mix(in srgb,var(--mut) 8%, transparent)}
.trust{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:11.5px;color:var(--mut);margin-top:6px}
.companions{margin:8px 0 0;display:flex;flex-wrap:wrap;gap:4px 12px;font-size:11.5px;color:var(--mut);align-items:baseline}
.complabel{font-size:9.5px;letter-spacing:.1em;text-transform:uppercase}
.comp b{font-weight:600;color:var(--fg)}
.flags{margin:8px 0 0;padding-left:18px;font-size:12.5px;color:var(--mut)}
.chips{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}
.chip{font-size:10.5px;padding:2px 7px;border-radius:10px;border:1px solid var(--line);color:var(--mut)}
.chip.ts{border-color:var(--blue);color:var(--blue)}
.chip.h2h{border-color:var(--amber);color:var(--amber)}
.src{font-size:10.5px;color:var(--mut);margin-top:5px;word-break:break-all}
.h2hgroup{border:1px solid var(--amber);border-radius:8px;padding:12px;margin:14px 0;background:var(--card)}
.h2hgroup .side{display:flex;justify-content:space-between;gap:12px;padding:5px 0;
border-bottom:1px dotted var(--line);font-size:14px}
.h2hgroup .side:last-child{border-bottom:0}
.h2hgroup .num{font-variant-numeric:tabular-nums;font-weight:640}
.fallback{border-color:var(--mut);border-style:dashed}
table.inv{width:100%;border-collapse:collapse;font-size:12.5px}
table.inv th,table.inv td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
.warnbox{border:1px solid var(--amber);border-radius:6px;padding:10px 12px;margin:14px 0;
font-size:13px;background:color-mix(in srgb,var(--amber) 8%, transparent)}
.bindgroup{margin:16px 0 26px;border:2px solid var(--red);border-radius:8px;
background:var(--card);overflow:hidden}
.bindhead{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;padding:8px 12px;
background:color-mix(in srgb,var(--red) 12%, transparent);border-bottom:1px solid var(--line)}
.bindlabel{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--red)}
.bindnote{font-size:12.5px}
/* The two figures, side by side, with nothing between them. */
.bindstrip{display:flex;flex-wrap:wrap;gap:10px 28px;padding:14px 14px 12px;
border-bottom:1px solid var(--line);align-items:flex-start}
.bindside{display:flex;flex-direction:column;gap:2px}
.bindpct{font-size:30px;font-weight:640;line-height:1;font-variant-numeric:tabular-nums}
.bindpct.green{color:var(--green)}.bindpct.amber{color:var(--amber)}.bindpct.red{color:var(--red)}
.bindpct.unscoreable{font-size:16px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
.bindmetric{font-size:11.5px;color:var(--mut);max-width:38ch}
.scroll{overflow-x:auto}
"""


def _spread_sentence(rows: list[dict]) -> str:
    """⚠️ AGAINST THE TEN-SECOND READ. A reader who takes one glance should not
    be able to leave with the best number on the page. The spread and the
    unscoreable count are stated before any row is drawn — computed, never
    written, so they cannot go stale or be softened."""
    scored = [r["pct_of_achievable"] for r in rows
              if r.get("scoreable") and r.get("pct_of_achievable") is not None]
    blind = sum(1 for r in rows if not r.get("scoreable"))
    if not scored:
        return "<b>No row on this page carries a number.</b>"
    return ("<b>%d rows carry a number and they span %.2f%% to %.2f%%</b> — the "
            "worst and the best are measured on different samples against "
            "different ceilings and are not each other's context. <b>%d further "
            "rows carry no number at all</b>, listed at the foot of the page."
            % (len(scored), min(scored), max(scored), blind))


def prepare(reg: dict) -> tuple[list[dict], list[list[dict]], list[tuple[str, str]],
                                list[tuple[str, str, str]]]:
    """What may be rendered, and what may not — computed ONCE, for both formats.

    Two withholding rules, and the second CASCADES:
      * a row that requires a caption and cannot be given one (R1);
      * a row bound by `render_with` to a withheld row — the schema says a
        consumer that cannot place them together must render NEITHER, so a
        caption fault on one member takes the whole pair off the page rather
        than leaving the survivor to be read alone, which is the exact harm
        the binding exists to prevent.
    """
    skipped = {r["id"]: p for r in reg["rows"] if (p := caption_problem(r))}
    all_binds, faults = bind_groups(reg["rows"])

    for rid, kind, other in faults:                 # a broken link binds nothing
        skipped.setdefault(rid, "%s (%s) — the pair is withheld rather than "
                                "rendered apart" % (kind, other))
        skipped.setdefault(other, "named by `%s` in a link that is not "
                                  "reciprocal — the pair is withheld" % rid)

    for members in all_binds:                       # cascade
        hit = [m["id"] for m in members if m["id"] in skipped]
        if hit:
            for m in members:
                skipped.setdefault(
                    m["id"], "bound by `render_with` to a withheld row (%s), and "
                             "the schema says a consumer that cannot place them "
                             "together must render NEITHER" % ", ".join(hit))

    rows = [r for r in reg["rows"] if r["id"] not in skipped]
    binds = [m for m in all_binds if all(x["id"] not in skipped for x in m)]
    return rows, binds, sorted(skipped.items()), faults


def render_html(reg: dict, warnings: list[str], skipped: list[tuple[str, str]]) -> str:
    rows, binds, _skipped, _faults = prepare(reg)
    declared, fallback = head_to_head(rows)
    parts = []

    parts.append("<meta charset=\"utf-8\">\n<title>% of achievable</title>\n<style>" + CSS + "</style>\n<div class='wrap'>")
    parts.append("<h1>% of achievable</h1>")
    parts.append(
        "<p class='lede'>Every measurement this project makes, in one unit and one "
        "direction. <b>Higher is better, everywhere.</b> Read from "
        "<code>metric-registry.json</code> v%s; rendered %s.</p>"
        % (esc(reg["schema_version"]), _dt.date.today().isoformat()))
    parts.append(
        "<div class='unitbar'><b>Why one unit.</b> The raw metrics disagree about "
        "direction — an OMR-NED of 1.000 is catastrophic and a recall of 1.000 is "
        "perfect. Here <b>100 means the ceiling this row was measured against</b>, "
        "and every ceiling is named, with whether it was <b>measured</b> or "
        "<b>assumed</b>. Bars drawn <span style='background-image:repeating-linear-gradient("
        "45deg,rgba(128,128,128,.5) 0 3px,transparent 3px 7px);padding:0 10px'>hatched</span> "
        "are scored against a ceiling nobody has measured.<br><br>"
        "%s<br><br>"
        "<b>There is no page-level number, by construction.</b> Engraved and scan "
        "have different ceilings, noise floors and eras; one colour across them "
        "would be a lie. Rows are grouped by the <i>sample they were measured on</i> "
        "and never shown alone.</div>" % _spread_sentence(rows))

    if skipped:
        parts.append(
            "<div class='warnbox'><b>%d row%s WITHHELD.</b> A row that cannot be "
            "rendered as the schema requires — its <code>mandatory_caption</code> "
            "unplaceable, or its <code>render_with</code> partner withheld — is not "
            "rendered bare. The rule is that the renderer must not show it at all."
            "<ul>%s</ul></div>"
            % (len(skipped), "" if len(skipped) == 1 else "s",
               "".join("<li><code>%s</code> — %s</li>" % (esc(i), esc(w)) for i, w in skipped)))
    if warnings:
        # Grouped by KIND, so a repeated structural warning reads as one fact
        # about the registry rather than as eight paragraphs of noise. Nothing
        # is summarised away: every row id is still named.
        kinds: dict[str, list[str]] = {}
        for rid, kind, _detail in warnings:
            kinds.setdefault(kind, []).append(rid)
        parts.append(
            "<div class='warnbox'><b>%d warning%s</b> (non-zero exit under "
            "<code>--strict</code>):<ul>%s</ul></div>"
            % (len(warnings), "" if len(warnings) == 1 else "s",
               "".join("<li><b>%d ×</b> %s — %s</li>"
                       % (len(ids), esc(k), ", ".join("<code>%s</code>" % esc(i) for i in ids))
                       for k, ids in kinds.items())))

    # ── head-to-head, grouped ONLY on the declared key ───────────────────────
    parts.append("<h2 id='head-to-head'>Head-to-head</h2>")
    parts.append("<p class='lede'>Grouped on <code>comparable_as.head_to_head</code> "
                 "and on nothing else — same fixtures, same scorer, same row set, "
                 "<b>different system</b>. This is a comparison, <b>not a delta</b>: "
                 "it says nothing about direction over time.</p>")
    for key, members in declared:
        sides = "".join(
            "<div class='side'><span><code>%s</code></span><span class='num %s'>%s</span></div>"
            % (esc(m["id"]), band(m.get("pct_of_achievable")),
               ("%.2f%%" % m["pct_of_achievable"]) if m.get("pct_of_achievable") is not None else "unscoreable")
            for m in sorted(members, key=lambda m: -(m.get("pct_of_achievable") or 0)))
        parts.append("<div class='h2hgroup'><code>%s</code>%s</div>" % (esc(key), sides))
    if fallback:
        parts.append(
            "<div class='h2hgroup fallback'><b>FALLBACK GROUPING — not a declared "
            "head-to-head.</b> These rows carry <code>ceiling.kind == \"competitive\"</code> "
            "but declare no <code>comparable_as.head_to_head</code> key, so nothing "
            "says what they are comparable WITH. They are listed apart and are never "
            "filed under a declared key.%s</div>"
            % "".join("<div class='side'><span><code>%s</code></span></div>" % esc(m["id"])
                      for m in fallback))

    # ── families, cross-cutting FIRST ───────────────────────────────────────
    for fam in FAMILY_ORDER:
        fam_rows = [r for r in rows if r.get("family") == fam]
        if not fam_rows:
            continue
        parts.append("<h2 id='family-%s'>%s</h2>" % (esc(fam), esc(FAMILY_TITLE.get(fam, fam))))
        parts.append("<p class='lede'>%s</p>" % FAMILY_NOTE.get(fam, ""))
        parts.extend(family_blocks(fam_rows, binds))

    # ── R6: the page ends here, on what nothing measures ────────────────────
    blind = [r for r in rows if not r.get("scoreable")]
    parts.append("<h2 id='nothing-measures'>What nothing here measures</h2>")
    parts.append(
        "<p class='lede'>The page ends on this deliberately. %d of %d rows carry no "
        "number at all — most because the harness cannot see the stage, which is a "
        "ceiling of <b>zero information</b> and not a low score. A reader who takes "
        "ten seconds should leave with this, not with the best figure above it.</p>"
        % (len(blind), len(rows)))
    parts.append("<div class='scroll'><table class='inv'><tr><th>row</th><th>stage</th>"
                 "<th>ceiling kind</th><th>why it is not scored</th></tr>")
    for r in sorted(blind, key=lambda r: ((r.get("ceiling") or {}).get("kind") or "", r["id"])):
        parts.append("<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>"
                     % (esc(r["id"]), esc(r.get("stage") or ""),
                        esc((r.get("ceiling") or {}).get("kind") or "—"),
                        esc(prose(r.get("why_not") or ""))))
    parts.append("</table></div>")
    parts.append("</div>")
    return "\n".join(parts) + "\n"


def render_md(reg: dict, warnings: list[str], skipped: list[tuple[str, str]]) -> str:
    rows, binds, _skipped, _faults = prepare(reg)
    bound_ids = {m["id"] for g in binds for m in g}
    out = ["# % of achievable",
           "",
           "One unit, one direction: **higher is better, everywhere.** "
           "Registry v%s. Generated — do not hand-edit." % reg["schema_version"],
           ""]
    if skipped:
        out += ["## Withheld rows", ""]
        out += ["- `%s` — %s" % (i, w) for i, w in skipped] + [""]
    declared, fallback = head_to_head(rows)
    out += ["## Head-to-head (grouped on `comparable_as.head_to_head` only)", ""]
    for key, members in declared:
        out.append("**`%s`**" % key)
        for m in sorted(members, key=lambda m: -(m.get("pct_of_achievable") or 0)):
            out.append("- `%s` — %s" % (m["id"], ("%.2f%%" % m["pct_of_achievable"])
                                        if m.get("pct_of_achievable") is not None else "unscoreable"))
        out.append("")
    if fallback:
        out += ["**FALLBACK — not a declared head-to-head:** "
                + ", ".join("`%s`" % m["id"] for m in fallback), ""]
    def _bullet(r):
        pct = r.get("pct_of_achievable")
        head = ("**%.2f%% of achievable** — `%s`" % (pct, r["id"])) if (
            r.get("scoreable") and pct is not None) else (
            "**unscoreable** — `%s`" % r["id"])
        cap = r.get("mandatory_caption")
        # R1 in Markdown: the caption is on the SAME line as the number.
        if cap:
            head += " — ⚠️ MUST BE READ WITH THIS NUMBER: %s" % prose(cap)
        lines = ["- " + head]
        if not r.get("scoreable"):
            lines.append("  - %s" % prose(r.get("why_not") or ""))
        return lines

    for fam in FAMILY_ORDER:
        fam_rows = [r for r in rows if r.get("family") == fam]
        if not fam_rows:
            continue
        out += ["## %s" % FAMILY_TITLE.get(fam, fam), ""]
        # Bound pairs FIRST and in one block, so the two figures are adjacent
        # lines here exactly as they are adjacent elements in the HTML.
        for members in binds:
            home = min(members, key=lambda m: (m.get("pct_of_achievable")
                                               if m.get("scoreable") and
                                               m.get("pct_of_achievable") is not None
                                               else -1.0))
            if home.get("family") != fam:
                continue
            out += ["### bound by `render_with` — read together, never apart", ""]
            for m in members:
                out += _bullet(m)
            out.append("")
        for g in era_groups([r for r in fam_rows if r["id"] not in bound_ids]):
            out += ["### sample `%s`" % g["era_key"], ""]
            for r in g["rows"]:
                out += _bullet(r)
            out.append("")
    blind = [r for r in rows if not r.get("scoreable")]
    out += ["## What nothing here measures", "",
            "%d of %d rows carry no number at all." % (len(blind), len(rows)), ""]
    for r in blind:
        out.append("- `%s` (%s) — %s" % (r["id"], (r.get("ceiling") or {}).get("kind"),
                                         prose(r.get("why_not") or "")))
    return "\n".join(out) + "\n"


# ── warnings ─────────────────────────────────────────────────────────────────

#: An evidence entry that is a path this build can check. Some entries are
#: prose pointers ("CLAUDE.md · OMR_CHOIR_GROUPING (benchmarks/…)"), which are
#: reported separately rather than as missing files — a renderer inventing a
#: missing-file defect is as bad as one hiding a real warning.
_PATHLIKE = re.compile(r"^[\w./\-]+$")


def collect_warnings(reg: dict, root: Path) -> list[tuple[str, str, str]]:
    """`(row_id, kind, detail)` — the kind is what groups them on the page."""
    warns = []
    for r in reg["rows"]:
        for ev in ((r.get("ceiling") or {}).get("evidence") or []):
            if _PATHLIKE.match(str(ev)):
                if not (root / ev).exists():
                    warns.append((r["id"], "ceiling evidence is not on disk", str(ev)))
            else:
                warns.append((r["id"], "ceiling evidence is a prose pointer, not a "
                                       "checkable path", str(ev)))
        if r.get("scoreable") and (r.get("ceiling") or {}).get("status") is None:
            warns.append((r["id"], "scoreable with no ceiling status", ""))
    return warns


def build(reg: dict, root: Path) -> tuple[str, str, list[str], list[tuple[str, str]]]:
    gate_schema_version(reg)
    _rows, _binds, skipped, faults = prepare(reg)
    warns = collect_warnings(reg, root)
    warns += [(rid, "render_with: " + kind, other) for rid, kind, other in faults]
    warns += [(i, "WITHHELD", w) for i, w in skipped]
    return render_html(reg, warns, skipped), render_md(reg, warns, skipped), warns, skipped


def _strip_date(s: str) -> str:
    return re.sub(r"rendered \d{4}-\d{2}-\d{2}", "rendered <date>", s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render metric-registry.json as % of achievable.")
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out-html", type=Path, default=OUT_HTML)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--check", action="store_true",
                    help="non-zero if the committed output is stale")
    ap.add_argument("--strict", action="store_true",
                    help="non-zero on ANY warning (missing evidence, withheld row)")
    ap.add_argument("--serve", action="store_true", help="preview on :8601")
    args = ap.parse_args(argv)

    reg = load_registry(args.registry)
    html_s, md_s, warns, skipped = build(reg, ROOT)

    for rid, kind, detail in warns:
        print("WARN: %s: %s%s" % (rid, kind, (" — " + detail) if detail else ""),
              file=sys.stderr)

    if args.check:
        stale = []
        for path, fresh in ((args.out_html, html_s), (args.out_md, md_s)):
            if not path.exists() or _strip_date(path.read_text()) != _strip_date(fresh):
                stale.append(str(path))
        if stale:
            print("STALE: " + ", ".join(stale) + "\n  Re-run without --check.", file=sys.stderr)
            return 1
        print("up to date")
        return 2 if (args.strict and warns) else 0

    args.out_html.write_text(html_s)
    args.out_md.write_text(md_s)
    print("wrote %s\nwrote %s" % (args.out_html, args.out_md))

    if args.strict and warns:
        print("STRICT: %d warning(s) — failing the build. A live WARN beside a "
              "zero exit is how the previous build reported its own missing "
              "evidence." % len(warns), file=sys.stderr)
        return 2

    if args.serve:
        import functools, http.server, socketserver
        h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.out_html.parent))
        with socketserver.TCPServer(("127.0.0.1", 8601), h) as srv:
            print("serving http://127.0.0.1:8601/%s — ctrl-c to stop" % args.out_html.name)
            try:
                srv.serve_forever()
            except KeyboardInterrupt:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
