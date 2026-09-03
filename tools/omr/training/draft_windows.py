"""Draft the window rows a labeling batch needs, from its transcription.

    python3 -m tools.omr.training.draft_windows \\
        --transcription benchmarks/omr-labeling-NEW/transcription.json \\
        --base benchmarks/omr-scan-e2e-2026-09/works.json --row-id brahms-sym1-mvt1-317803-p1 \\
        --out benchmarks/omr-labeling-NEW/windows.json

`mxl_verdicts` needs, per page, WHICH reference measure the page starts on
and WHICH parts each printed staff carries. Both are facts about the page
that the runner must not infer from the reading it is about to score — but
a DRAFT of them can be, as long as every drafted value is marked for a
human to confirm. That is what this writes:

- **The measure window is chained** from a base row (the scan benchmark's
  hand-verified row for an earlier page of the same edition): the next page
  starts one measure after the base row ends, and each later page starts
  where the previous page's measure count (the mode across its staves)
  leaves off. A page whose staves disagree about their measure count is
  flagged, because a barline error is exactly what shifts every bar after it.
- **Staff ↔ parts is drafted by instrument name**, per system: the base
  row's staff names and the transcription's contextual `instrument` on each
  staff both resolve through `instruments.lookup`, and same-instrument staves
  are paired in order of appearance (first horn staff → first horn entry).
  A staff with no instrument read gets `parts: []`, which makes `mxl_verdicts`
  abstain on its cells until someone fills it in.

Every drafted row carries `"confidence": "draft"` and a `check` list naming
what was inferred. Open the file, read the margin of each page against it,
fix what is wrong, and delete the `draft` marker when it is right.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..instruments import lookup


def _canonical(name: str | None) -> str | None:
    if not name:
        return None
    m = lookup(name)
    return m.instrument.name if m else None


def _base_row(path: Path, row_id: str | None, work_id: str | None) -> dict:
    raw = json.loads(path.read_text())
    rows = raw.get("rows", raw) if isinstance(raw, dict) else raw
    by_id = {r.get("row_id"): r for r in rows}
    if row_id:
        if row_id not in by_id:
            raise SystemExit(f"no row {row_id!r} in {path}")
        row = by_id[row_id]
    else:
        cands = [r for r in rows if work_id and r.get("work_id") == work_id]
        if len(cands) != 1:
            raise SystemExit(f"{len(cands)} rows for work {work_id!r} in {path}; pass --row-id")
        row = cands[0]
    staves = row.get("staves")
    hops = 0
    while isinstance(staves, str) and staves.startswith("same-as:") and hops < 10:
        staves = (by_id.get(staves[len("same-as:"):]) or {}).get("staves")
        hops += 1
    if not isinstance(staves, list):
        raise SystemExit(f"row {row.get('row_id')!r} has no staves list to draft from")
    row = dict(row)
    row["staves"] = staves
    return row


def system_measure_count(system: dict) -> int:
    """The bar count a system prints — the mode across its staves. A system
    is one row of bars, so every staff in it has the same count; a staff
    that differs has a barline error, not a different length."""
    counts = [st.get("n_measures", len(st.get("measures", []))) for st in system.get("staves", [])]
    if not counts:
        return 0
    return Counter(counts).most_common(1)[0][0]


def _page_measure_count(page: dict) -> tuple[int, list[str]]:
    """Measures on the page = the sum of its systems' counts. `staff_index`
    is numbered across the PAGE (system 1's staves continue the count), so
    counts are never summed per staff across systems. Returns the total and
    the staves that disagree with their own system."""
    total = 0
    disagree: list[str] = []
    for sys_ in page.get("systems", []):
        mode = system_measure_count(sys_)
        total += mode
        for st in sys_.get("staves", []):
            n = st.get("n_measures", len(st.get("measures", [])))
            if n != mode:
                disagree.append(f"system {sys_.get('system_index')} staff {st.get('staff_index')} "
                                f"reads {n} bars, its system {mode}")
    return total, disagree


def _draft_system(staves: list[dict], base_staves: list[dict]) -> tuple[list[dict], list[str]]:
    """Pair this system's staves with the base row's entries.

    When the system prints as many staves as the base row, it is the full
    lineup and the pairing is POSITIONAL — top to bottom, the same order —
    and the read instrument is only a cross-check, reported where it
    disagrees. A margin reader that turns `Kontrafagott` into `Bassoon`
    must not move a staff the print already placed.

    A shorter system (tacet staves suppressed) is paired by instrument, in
    order of appearance within an instrument; a staff whose instrument was
    not read, or whose instrument's entries are used up, gets `parts: []`
    for the human.
    """
    if len(staves) == len(base_staves):
        out: list[dict] = []
        checks: list[str] = []
        for st, b in zip(staves, base_staves):
            inst_read = st.get("instrument")
            out.append({"name": b.get("name", ""), "parts": list(b.get("parts", [])),
                        "read_as": inst_read, "source": st.get("instrument_source"),
                        "paired_by": "position"})
            want = _canonical(b.get("name"))
            got = _canonical(inst_read) if inst_read else None
            if got is not None and want is not None and got != want:
                checks.append(f"staff {st.get('staff_index')}: placed as {b.get('name')!r} by position, "
                              f"but the margin read {inst_read!r} — confirm on the page")
        return out, checks
    base_by_inst: dict[str | None, list[dict]] = {}
    for b in base_staves:
        base_by_inst.setdefault(_canonical(b.get("name")), []).append(b)
    used: dict[str | None, int] = {}
    out: list[dict] = []
    checks: list[str] = []
    for st in staves:
        inst_read = st.get("instrument")
        canon = _canonical(inst_read) if inst_read else None
        pool = base_by_inst.get(canon, []) if canon else []
        k = used.get(canon, 0)
        if canon and k < len(pool):
            b = pool[k]
            used[canon] = k + 1
            out.append({"name": b.get("name", inst_read), "parts": list(b.get("parts", [])),
                        "read_as": inst_read, "source": st.get("instrument_source"),
                        "paired_by": "instrument"})
        else:
            out.append({"name": inst_read or "?", "parts": [], "read_as": inst_read})
            checks.append(f"staff {st.get('staff_index')}: "
                          + (f"no base entry left for {canon!r}" if canon else "no instrument read")
                          + " — fill in `parts` by hand")
    return out, checks


def draft(transcription: dict, base: dict, *, first_measure: int | None = None) -> list[dict]:
    pages = sorted(transcription.get("pages", []), key=lambda p: p.get("page_index", 0))
    if not pages:
        raise SystemExit("the transcription has no pages")
    base_page = int(base["page"]["pdf_page_index"])
    base_last = base.get("window", {}).get("last_ref_measure")
    if first_measure is None:
        if base_last is None:
            raise SystemExit("base row has no last_ref_measure; pass --first-measure")
        if pages[0].get("page_index") != base_page + 1:
            raise SystemExit(
                f"the transcription starts on page {pages[0].get('page_index')}, which is not the "
                f"page after the base row's ({base_page}); pass --first-measure for that page")
        first_measure = int(base_last) + 1
    base_staves = base["staves"]
    rows: list[dict] = []
    cursor = first_measure
    for page in pages:
        pidx = page.get("page_index")
        mode, disagree = _page_measure_count(page)
        checks: list[str] = [
            f"first_ref_measure {cursor} is chained from the previous page's measure count — "
            "confirm on the page"]
        checks.extend(disagree)
        systems: dict[str, list[dict]] = {}
        for sys_ in page.get("systems", []):
            specs, sys_checks = _draft_system(sys_.get("staves", []), base_staves)
            systems[str(sys_.get("system_index", 0))] = specs
            checks.extend(f"system {sys_.get('system_index')}: {c}" for c in sys_checks)
        n_staves = sum(len(s.get("staves", [])) for s in page.get("systems", []))
        rows.append({
            "row_id": f"{base.get('row_id', 'base')}-draft-p{pidx}",
            "work_id": base.get("work_id"),
            "edition": base.get("edition"),
            "reference": base.get("reference"),
            "page": {"pdf_page_index": pidx, "n_systems": len(page.get("systems", [])),
                     "n_staves": n_staves},
            "window": {"first_ref_measure": cursor, "last_ref_measure": cursor + mode - 1,
                       "established_by": "draft_windows.py — chained from the base row and the "
                                         "transcription's measure counts; NOT verified",
                       "confidence": "draft"},
            # The page-level list is the first system's; per-system lists
            # carry the tacet-suppressed pages. mxl_verdicts reads `systems`.
            "staves": systems.get("0", []),
            "systems": systems,
            "confidence": "draft",
            "check": checks,
        })
        cursor += mode
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--transcription", required=True, type=Path)
    ap.add_argument("--base", required=True, type=Path,
                    help="works.json holding a hand-verified row for an earlier page of this edition")
    ap.add_argument("--row-id", default=None)
    ap.add_argument("--work-id", default=None)
    ap.add_argument("--first-measure", type=int, default=None,
                    help="reference measure the FIRST transcribed page starts on "
                         "(default: one after the base row's window)")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    transcription = json.loads(args.transcription.read_text())
    base = _base_row(args.base, args.row_id, args.work_id)
    rows = draft(transcription, base, first_measure=args.first_measure)
    args.out.write_text(json.dumps(rows, indent=2))
    n_checks = sum(len(r["check"]) for r in rows)
    print(f"wrote {len(rows)} draft rows to {args.out} — {n_checks} things to check:")
    for r in rows:
        w = r["window"]
        print(f"  page {r['page']['pdf_page_index']}: measures {w['first_ref_measure']}-{w['last_ref_measure']}, "
              f"{r['page']['n_systems']} systems, {r['page']['n_staves']} staves")
        for c in r["check"]:
            print(f"      - {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
