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


def _page_measure_count(page: dict) -> tuple[int, dict[int, int]]:
    """Measures on the page per staff ordinal (summed across systems), and
    the mode — the count most staves agree on."""
    per_staff: Counter[int] = Counter()
    for sys_ in page.get("systems", []):
        for st in sys_.get("staves", []):
            per_staff[st.get("staff_index", 0)] += st.get("n_measures", len(st.get("measures", [])))
    if not per_staff:
        return 0, {}
    mode = Counter(per_staff.values()).most_common(1)[0][0]
    return mode, dict(per_staff)


def _draft_system(staves: list[dict], base_staves: list[dict]) -> tuple[list[dict], list[str]]:
    """Pair this system's staves with the base row's entries by instrument,
    in order of appearance within an instrument."""
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
                        "read_as": inst_read, "source": st.get("instrument_source")})
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
        mode, per_staff = _page_measure_count(page)
        checks: list[str] = [
            f"first_ref_measure {cursor} is chained from the previous page's measure count — "
            "confirm on the page"]
        disagree = {s: n for s, n in per_staff.items() if n != mode}
        if disagree:
            checks.append(f"{len(disagree)} of {len(per_staff)} staves read a different measure "
                          f"count than the mode {mode}: {disagree}")
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
