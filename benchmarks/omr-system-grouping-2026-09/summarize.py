#!/usr/bin/env python3
"""Turn sweep.jsonl into SWEEP_SUMMARY.md + anomaly_shortlist.json.

Pure post-processing over already-computed sweep rows — no rendering, no
tools.omr calls. Implements the six anomaly flags and the K.183 / scan-pair
tables from the build brief.

Usage: python3 summarize.py [--sweep sweep.jsonl] [--out SWEEP_SUMMARY.md]
                             [--shortlist anomaly_shortlist.json] [--cap 60]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SWEEP = HERE / "sweep.jsonl"
DEFAULT_OUT = HERE / "SWEEP_SUMMARY.md"
DEFAULT_SHORTLIST = HERE / "anomaly_shortlist.json"

FLAG_LABELS = {
    "a": "error or zero staves",
    "b": "size-1 system next to a >=5-staff system",
    "c": "max/min system-size ratio >= 3",
    "d": ">=5 systems with median size >= 4",
    "e": "gap-heuristic fallback fired (used_bridging=False)",
    "f": "scan-pair disagreement",
}
FLAG_ORDER = ["a", "b", "c", "d", "e", "f"]


def load_rows(sweep_path: Path):
    rows = []
    with sweep_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # tolerate a torn last line if read concurrently with a live sweep
    return rows


# ─── Scan-pair join (flag f needs this before per-row flagging) ─────────────


def scan_pair_disagreements(rows):
    """pair_id -> [{page, sizes_a, sizes_b, pdf_a, pdf_b, kind}], for the
    3 same-plate SHARED-SAMPLE pairs only (k183 is two different engravings —
    page index is not content-aligned, so it is reported separately, not
    joined here)."""
    SCAN_PAIR_IDS = {"beethoven5-scan-pair", "brahms1-scan-pair", "mozart41-scan-pair"}
    by_pair = defaultdict(lambda: defaultdict(dict))  # pair_id -> page -> pdf_rel -> row
    for r in rows:
        pid = r.get("pair_id")
        if pid in SCAN_PAIR_IDS:
            by_pair[pid][r["page"]][r["pdf_rel"]] = r

    disagreements = defaultdict(list)
    flagged_keys = set()  # (pdf_rel, page) pairs to flag as (f)
    for pid, by_page in by_pair.items():
        for page, by_pdf in sorted(by_page.items()):
            if len(by_pdf) != 2:
                continue  # one side errored/missing — not a same-page comparison
            (pdf_a, row_a), (pdf_b, row_b) = sorted(by_pdf.items())
            sizes_a, sizes_b = row_a.get("staves_per_system"), row_b.get("staves_per_system")
            if row_a.get("error") or row_b.get("error"):
                continue
            n_a = len(sizes_a) if sizes_a else 0
            n_b = len(sizes_b) if sizes_b else 0
            if n_a != n_b:
                kind = "system-count differs"
            elif sizes_a != sizes_b:
                kind = "system count agrees, staff sizes differ"
            else:
                continue
            disagreements[pid].append({"page": page, "pdf_a": pdf_a, "pdf_b": pdf_b,
                                        "sizes_a": sizes_a, "sizes_b": sizes_b, "kind": kind})
            flagged_keys.add((pdf_a, page))
            flagged_keys.add((pdf_b, page))
    return disagreements, flagged_keys


# ─── Per-row anomaly flags ────────────────────────────────────────────────────


def flags_for_row(row, scan_pair_flagged_keys):
    reasons = []
    sizes = row.get("staves_per_system")

    if row.get("error") or not row.get("n_staves"):
        detail = row["error"] if row.get("error") else "zero staves detected"
        reasons.append(("a", f"{FLAG_LABELS['a']}: {detail}"))

    if sizes and len(sizes) >= 2:
        if 1 in sizes and max(sizes) >= 5:
            reasons.append(("b", f"{FLAG_LABELS['b']}: sizes={sizes}"))
        lo, hi = min(sizes), max(sizes)
        if lo > 0 and hi / lo >= 3:
            reasons.append(("c", f"{FLAG_LABELS['c']}: sizes={sizes} (ratio {hi/lo:.1f})"))

    if sizes and len(sizes) >= 5:
        med = statistics.median(sizes)
        if med >= 4:
            reasons.append(("d", f"{FLAG_LABELS['d']}: {len(sizes)} systems, median {med}: sizes={sizes}"))

    if row.get("used_bridging") is False:
        reasons.append(("e", f"{FLAG_LABELS['e']}"))

    if (row["pdf_rel"], row["page"]) in scan_pair_flagged_keys:
        reasons.append(("f", f"{FLAG_LABELS['f']}: see scan-pair table"))

    return reasons


def select_shortlist(rows, scan_pair_flagged_keys, cap):
    flagged = []
    for row in rows:
        reasons = flags_for_row(row, scan_pair_flagged_keys)
        if reasons:
            flagged.append((row, reasons))

    by_primary_flag = defaultdict(list)
    for row, reasons in flagged:
        by_primary_flag[reasons[0][0]].append((row, reasons))

    selected = []
    seen = set()
    buckets = {f: by_primary_flag.get(f, [])[:] for f in FLAG_ORDER}
    while len(selected) < cap and any(buckets[f] for f in FLAG_ORDER):
        for f in FLAG_ORDER:
            if len(selected) >= cap:
                break
            if buckets[f]:
                row, reasons = buckets[f].pop(0)
                key = (row["pdf_rel"], row["page"])
                if key in seen:
                    continue
                seen.add(key)
                selected.append((row, reasons))
    return selected, len(flagged)


# ─── Report sections ──────────────────────────────────────────────────────────


def k183_table(rows):
    k = [r for r in rows if r.get("pair_id") == "k183"]
    by_pdf = defaultdict(list)
    for r in k:
        by_pdf[r["pdf_rel"]].append(r)
    if len(by_pdf) != 2:
        return "(K.183 pair not fully present in this sweep)\n"
    (name_a, rows_a), (name_b, rows_b) = sorted(by_pdf.items())
    rows_a.sort(key=lambda r: r["page"])
    rows_b.sort(key=lambda r: r["page"])
    lines = [f"Two different ENGRAVINGS (not two scans of the same plate) — page index is "
             f"NOT content-aligned between columns. Listed side by side by row order only, "
             f"for a quick visual scan of each publisher's layout tendency.", "",
             f"- A = `{name_a}`", f"- B = `{name_b}`", "",
             "| A: page | A: staves | A: systems (sizes) | B: page | B: staves | B: systems (sizes) |",
             "|--:|--:|---|--:|--:|---|"]
    for i in range(max(len(rows_a), len(rows_b))):
        a = rows_a[i] if i < len(rows_a) else None
        b = rows_b[i] if i < len(rows_b) else None

        def cell(r):
            if r is None:
                return ("", "", "")
            if r.get("error"):
                return (str(r["page"]), "ERR", r["error"][:40])
            return (str(r["page"]), str(r["n_staves"]), str(r.get("staves_per_system")))
        pa, sa, za = cell(a)
        pb, sb, zb = cell(b)
        lines.append(f"| {pa} | {sa} | {za} | {pb} | {sb} | {zb} |")
    return "\n".join(lines) + "\n"


def scan_pair_section(disagreements, rows):
    lines = []
    SCAN_PAIR_IDS = ["beethoven5-scan-pair", "brahms1-scan-pair", "mozart41-scan-pair"]
    for pid in SCAN_PAIR_IDS:
        pair_rows = [r for r in rows if r.get("pair_id") == pid]
        pages = sorted({r["page"] for r in pair_rows})
        n_disagree = len(disagreements.get(pid, []))
        lines.append(f"### {pid}")
        lines.append("")
        lines.append(f"{len(pages)} shared pages compared, {n_disagree} disagreement(s).")
        lines.append("")
        if disagreements.get(pid):
            lines.append("| page | kind | sizes (scan A) | sizes (scan B) |")
            lines.append("|--:|---|---|---|")
            for d in disagreements[pid]:
                lines.append(f"| {d['page']} | {d['kind']} | {d['sizes_a']} | {d['sizes_b']} |")
            lines.append("")
    return "\n".join(lines) + "\n"


def publisher_histogram(rows):
    hist = defaultdict(int)
    err_hist = defaultdict(int)
    for r in rows:
        tok = r.get("publisher_token") or "unknown"
        hist[tok] += 1
        if r.get("error"):
            err_hist[tok] += 1
    lines = ["| publisher_token | pages swept | errors |", "|---|--:|--:|"]
    for tok in sorted(hist.keys(), key=lambda t: -hist[t]):
        lines.append(f"| {tok} | {hist[tok]} | {err_hist.get(tok, 0)} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--shortlist", type=Path, default=DEFAULT_SHORTLIST)
    ap.add_argument("--cap", type=int, default=60)
    args = ap.parse_args()

    rows = load_rows(args.sweep)
    n_total = len(rows)
    n_err = sum(1 for r in rows if r.get("error"))
    n_ok = n_total - n_err
    total_runtime = sum(r.get("runtime_s") or 0 for r in rows)

    disagreements, scan_pair_flagged_keys = scan_pair_disagreements(rows)
    shortlist, n_flagged_total = select_shortlist(rows, scan_pair_flagged_keys, args.cap)

    # Shortlist file: full row + reasons, suitable as make_crops.py --input.
    shortlist_out = []
    for row, reasons in shortlist:
        entry = dict(row)
        entry["anomaly_flags"] = [f for f, _ in reasons]
        entry["anomaly_reasons"] = [msg for _, msg in reasons]
        shortlist_out.append(entry)
    args.shortlist.write_text(json.dumps(shortlist_out, indent=2) + "\n")

    lines = []
    lines.append("# System-grouping sweep summary")
    lines.append("")
    lines.append(f"Source: `{args.sweep}` — {n_total} page rows ({n_ok} ok, {n_err} error). "
                 f"Sum of per-page `runtime_s` (serial): {total_runtime:.0f}s "
                 f"(~{total_runtime/60:.1f} min).")
    lines.append("")
    lines.append("## Publisher histogram (swept pages)")
    lines.append("")
    lines.append(publisher_histogram(rows))
    lines.append("## K.183 cross-publisher pair")
    lines.append("")
    lines.append(k183_table(rows))
    lines.append("## Same-plate scan-variance pairs")
    lines.append("")
    lines.append(scan_pair_section(disagreements, rows))
    lines.append("## Anomaly shortlist")
    lines.append("")
    lines.append(f"{n_flagged_total} pages matched at least one flag; {len(shortlist)} selected "
                 f"below (cap {args.cap}, round-robin across flags a-f so no single flag crowds "
                 f"out the others). Full row data (for `make_crops.py --input`): `{args.shortlist}`.")
    lines.append("")
    lines.append("Flags: " + "; ".join(f"({f}) {FLAG_LABELS[f]}" for f in FLAG_ORDER))
    lines.append("")
    lines.append("| # | publisher_token | pdf | page | flags | reason |")
    lines.append("|--:|---|---|--:|---|---|")
    for i, (row, reasons) in enumerate(shortlist):
        flag_str = ",".join(f for f, _ in reasons)
        reason_str = " / ".join(msg for _, msg in reasons)
        pdf_short = row["pdf_rel"]
        if len(pdf_short) > 60:
            pdf_short = "..." + pdf_short[-57:]
        lines.append(f"| {i+1} | {row.get('publisher_token')} | {pdf_short} | {row['page']} | "
                     f"{flag_str} | {reason_str[:160]} |")
    lines.append("")

    args.out.write_text("\n".join(lines) + "\n")
    print(f"{n_total} rows ({n_ok} ok, {n_err} error)")
    print(f"{n_flagged_total} pages flagged, {len(shortlist)} in shortlist (cap {args.cap})")
    print(f"wrote {args.out}")
    print(f"wrote {args.shortlist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
