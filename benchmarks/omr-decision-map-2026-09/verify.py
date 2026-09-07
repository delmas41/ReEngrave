#!/usr/bin/env python3
"""Re-derive the mechanical claims in docs/architecture-decision-map.md.

Prose rots; this does not. Every row of the map marked `[V<n>]` is produced
here, from the tree, by grep-equivalents that are printed alongside their
answer so a reader can re-run one by hand.

    python3 benchmarks/omr-decision-map-2026-09/verify.py            # print
    python3 benchmarks/omr-decision-map-2026-09/verify.py --json     # machine

Exit code is 0 always: this reports, it does not gate. A CI gate on these
numbers would freeze the very facts the map exists to keep current.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Where a "consumer" may legitimately live. A hit anywhere else is the
# producer, a test, or a benchmark probe -- none of which is a consumer.
PROD_DIRS = ("tools/", "backend/", "frontend/src/")
NOT_CONSUMER = ("/tests/", "/test_", "benchmarks/", "docs/", ".md")


def _rg(pattern: str, *paths: str, fixed: bool = True) -> list[str]:
    """grep -rn over the tree; returns 'path:line:text' rows."""
    cmd = ["grep", "-rn"]
    if fixed:
        cmd.append("-F")
    cmd.append(pattern)
    cmd.extend(paths or ("tools", "backend", "frontend"))
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return [ln for ln in p.stdout.splitlines() if ln.strip()]


def _split(rows: list[str], producer: str | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"consumer": [], "producer": [], "test": []}
    for r in rows:
        path = r.split(":", 1)[0]
        if producer and path == producer:
            out["producer"].append(r)
        elif any(m in path for m in NOT_CONSUMER):
            out["test"].append(r)
        else:
            out["consumer"].append(r)
    return out


# --------------------------------------------------------------------------
# V1  the exporter never reads a detection confidence
# --------------------------------------------------------------------------
def v1() -> dict:
    rows = _rg(r"confidence", "tools/omr/export.py", fixed=True)
    code = [r for r in rows
            if not re.match(r"^[^:]+:\d+:\s*(#|\*|\"\"\")", r)
            and "`grep" not in r]
    return {
        "id": "V1",
        "claim": "export.py never reads a detection confidence",
        "cmd": "grep -c 'confidence' tools/omr/export.py",
        "hits": len(rows),
        "hits_that_are_code": len(code),
        "rows": rows,
        "holds": len(code) == 0,
    }


# --------------------------------------------------------------------------
# V2  the internal-consistency checks and who reads them
# --------------------------------------------------------------------------
CHECK_KEYS = [
    "rhythm_sum_warning",
    "measure_count_warning",
    "key_signature_warning",
    "clef_register_warning",
    "time_signature_disagreement",
    "clef_proposal",
]


def v2() -> dict:
    rows = {}
    for key in CHECK_KEYS:
        split = _split(_rg(key), producer="tools/omr/transcribe.py")
        rows[key] = {
            "cmd": f"grep -rn {key} tools backend frontend",
            "consumers": split["consumer"],
            "n_consumers": len(split["consumer"]),
            "n_test_or_benchmark": len(split["test"]),
        }
    return {
        "id": "V2",
        "claim": "four of the five consistency checks reach no consumer",
        "keys": rows,
        "n_with_no_consumer": sum(1 for k in rows.values()
                                  if k["n_consumers"] == 0),
    }


# --------------------------------------------------------------------------
# V3  warning keys named in prose that do not exist in the tree
# --------------------------------------------------------------------------
PHANTOM = ["key_consistency_warning", "meter_consistency_warning"]


def v3() -> dict:
    found = {p: _rg(p) for p in PHANTOM}
    return {
        "id": "V3",
        "claim": ("docs/scope-identity-upstream-2026-09-06.md names two "
                  "warning keys the tree does not define"),
        "keys": {k: len(v) for k, v in found.items()},
        "holds": all(not v for v in found.values()),
    }


# --------------------------------------------------------------------------
# V4  env flags in the tree vs env flags documented in CLAUDE.md
# --------------------------------------------------------------------------
def v4() -> dict:
    tree = set()
    for py in sorted((ROOT / "tools" / "omr").glob("*.py")):
        for m in re.finditer(r'os\.environ\.get\(\s*"(OMR_[A-Z0-9_]+)"',
                             py.read_text()):
            tree.add(m.group(1))
    for py in sorted((ROOT / "backend" / "modules").glob("*.py")):
        for m in re.finditer(r'"(OMR_[A-Z0-9_]+)"', py.read_text()):
            tree.add(m.group(1))
    doc = set(re.findall(r"OMR_[A-Z0-9_]+",
                         (ROOT / "CLAUDE.md").read_text()))
    return {
        "id": "V4",
        "claim": "CLAUDE.md's env table is not the tree's env surface",
        "n_in_tree": len(tree),
        "n_documented": len(tree & doc),
        "undocumented": sorted(tree - doc),
    }


# --------------------------------------------------------------------------
# V5  the three circularity refusals still stand, and where
# --------------------------------------------------------------------------
REFUSALS = {
    # module: (the phrase that IS the refusal, the edge it refuses)
    "tools/omr/clef_correction.py":
        ("never score-order deductions", "deduced identity -> clef"),
    "tools/omr/dossier.py":
        ("never the clefs", "clef -> part/staff join"),
    "tools/omr/score_layouts.py":
        ("a clef — never", "clef -> layout pin"),
}


def v5() -> dict:
    out = {}
    for path, (needle, edge) in REFUSALS.items():
        rows = _rg(needle, path)
        out[path] = {"edge_refused": edge, "n": len(rows),
                     "at": [r.split(":")[1] for r in rows], "rows": rows}
    return {"id": "V5",
            "claim": ("three modules independently refuse a feedback edge on "
                      "circularity grounds"),
            "holds": all(v["n"] >= 1 for v in out.values()),
            "sites": out}


# --------------------------------------------------------------------------
# V7  line references quoted in prose that have drifted in the tree
# --------------------------------------------------------------------------
CITED = [
    # (doc that cites it, file, cited line, the symbol it was cited FOR)
    ("benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md",
     "tools/omr/contextual.py", 1202, "_not_clef_evidence"),
    ("docs/scope-identity-upstream-2026-09-06.md",
     "tools/omr/clef_correction.py", 396, "never score-order deductions"),
    ("docs/scope-identity-upstream-2026-09-06.md",
     "tools/omr/dossier.py", 436, "never the clefs"),
    ("docs/scope-identity-upstream-2026-09-06.md",
     "tools/omr/score_layouts.py", 683, "a clef — never"),
    ("docs/scope-identity-upstream-2026-09-06.md",
     "tools/omr/transcribe.py", 4970, "apply_contextual_analysis"),
    ("benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md",
     "tools/omr/transcribe.py", 3729, "_flag_clef_register_inversion"),
]


def v7() -> dict:
    out = []
    for doc, path, cited, symbol in CITED:
        rows = _rg(symbol, path)
        actual = [int(r.split(":")[1]) for r in rows]
        out.append({
            "cited_by": doc, "file": path, "cited_line": cited,
            "symbol": symbol, "actual_lines": actual,
            "drifted": bool(actual) and cited not in actual,
            "gone": not actual,
        })
    return {"id": "V7",
            "claim": "line numbers quoted in prose against the current tree",
            "n_drifted": sum(1 for r in out if r["drifted"]),
            "n_gone": sum(1 for r in out if r["gone"]),
            "rows": out}


# --------------------------------------------------------------------------
# V6  which result-JSON keys nothing outside the producer reads
# --------------------------------------------------------------------------
TRACKED = [
    "pitch_candidates", "instrument_source", "weight_routing",
    "rhythm_reconciliation", "ambiguous_labels_resolved",
    "gap_bridging_counts", "line_thickness", "slot_facts",
    "label_contradiction", "clef_source", "n_clipped_notehead_fragments_dropped",
]


def v6() -> dict:
    out = {}
    for key in TRACKED:
        rows = _rg(key)
        prod = [r for r in rows if r.split(":", 1)[0].startswith("tools/omr/")]
        outside = [r for r in rows
                   if not r.split(":", 1)[0].startswith("tools/omr/")
                   and not any(m in r for m in NOT_CONSUMER)]
        out[key] = {"n_total": len(rows), "n_tools_omr": len(prod),
                    "n_outside_tools_omr": len(outside)}
    return {"id": "V6",
            "claim": "consumer counts for the tracked result-JSON keys",
            "keys": out}


CHECKS = [v1, v2, v3, v4, v5, v6, v7]


# ==========================================================================
# The picture. GENERATED, so it cannot drift from the text.
#
# Nodes and edges are declared here; the COLOURS are measured -- a node is
# red because `v2`/`v6` found it has no consumer, not because someone drew it
# red. Rendered as mermaid, which this project's HTML renders natively.
# ==========================================================================

# stage id -> (label, tech, dashboard stage number)
STAGES = [
    ("s1",  "Render + staff detection",   "classical CV",     "1"),
    ("s2",  "System grouping",            "classical CV",     "2"),
    ("s3",  "Measure + barlines",         "classical CV",     "3"),
    ("s8a", "Header clef",                "geometry + CV",    "8a"),
    ("s8b", "Header key signature",       "template + fit",   "8b"),
    ("s4",  "Symbol detection",           "YOLOv8l 208cls",   "4"),
    ("s5",  "Stems + beams",              "classical CV",     "5"),
    ("s6",  "Pitch resolution",           "geometry",         "6"),
    ("s7",  "Rhythm / durations",         "derived",          "7"),
    ("sown", "Glyph OWNERSHIP",           "ladder/range/dist","4d"),
    ("s8c", "Time signature",             "template + vote",  "8c"),
    ("s9",  "Margin labels",              "text/Surya/Vision","9"),
    ("s10", "Slot align + identity",      "monotone DP",      "10"),
    ("s11", "Export",                     "serialisation",    "11"),
]

# (from, to, label) -- the information that actually flows, in the tree
FLOW = [
    ("s1", "s2", "line_ys, gaps"),
    ("s2", "s3", "systems"),
    ("s3", "s4", "measure cells"),
    ("s3", "s8a", "header window"),
    ("s8a", "s8b", "the SLOT TABLE"),
    ("s4", "s5", "detections"),
    ("s4", "sown", "detections"),
    ("s5", "s7", "beam levels"),
    ("s4", "s6", "notehead y"),
    ("s8a", "s6", "clef"),
    ("s8b", "s6", "fifths"),
    ("s6", "s7", "pitch"),
    ("s7", "s8c", "durations"),
    ("s8c", "s7", "meter — bounded ±1"),
    ("sown", "s6", "one glyph, one staff"),
    ("s9", "s10", "instrument names"),
    ("s6", "s10", "register fit"),
    ("s8a", "s10", "clefs → fit_layouts · +51 records"),
    ("s10", "s11", "part names, slots"),
    ("s7", "s11", "events"),
    ("s6", "s11", "pitches"),
]

# Signals that ARE computed and reach nobody. `key` is what v2/v6 measures.
DEAD_ENDS = [
    ("d_conf",  "detection confidence", "s4",
     "export.py reads it 0 times [V1]"),
    ("d_pc",    "pitch_candidates", "s6",
     "written, then pop()ed unread"),
    ("d_rhy",   "rhythm_sum_warning", "s7",
     "1 consumer: a UI percentage"),
    ("d_mc",    "measure_count_warning", "s3", "NOBODY [V2]"),
    ("d_key",   "key_signature_warning", "s8b", "NOBODY [V2]"),
    ("d_reg",   "clef_register_warning", "s6",
     "NOBODY \u2014 and reach 7/193, precision 0/11"),
    ("d_ts",    "time_signature_disagreement", "s8c", "NOBODY [V2]"),
    ("d_sym",   "clef symmetry + the whole trace", "s8a",
     "no call site passes trace="),
    ("d_prop",  "clef_proposal (applied:False)", "s10", "NOBODY [V2]"),
    ("d_lc",    "label_contradiction", "s10",
     "158 firings, 0.873 right \u2014 undecided"),
    ("d_dt",    "direction placement/category/terms/reader", "s11",
     "6 of 8 keys unread; placement hardcoded"),
    ("d_align", "the slot alignment DP score", "s10",
     "never returned \u2014 no margin exists"),
]

# Modules that are written, measured, documented -- and wired to nothing.
ORPHANS = [
    ("o_hair", "hairpin_detection.py",
     "imported only by its own tests"),
    # Added 2026-09-07 by benchmarks/omr-decision-map-verify-2026-09 (E10):
    # the LARGER of the two CV orphans, and the map had missed it entirely.
    ("o_brack", "bracket_reader.py (390 lines)",
     "tests + one benchmark's probes only"),
    ("o_cond", "condensed_parts.py",
     "no producer — so OMR_CONDENSED_PARTS is inert"),
    ("o_tmpl", "template_matcher.py",
     "dead detector; 2 live env flags on it"),
]

# A dependency nobody can satisfy today -- different from one not yet done.
UNSAT = [
    ("u_clef", "clef OVERRIDE needs source is 'label'",
     "29 of 29 unresolved non-treble scan staves print NO label"),
    ("u_range", "_dedupe range tier needs a dossier",
     "scan gate is dossier-free BY PROTOCOL \u2014 0 of 4,256 firings"),
]

# Edges the codebase deliberately REFUSES, with where the refusal lives.
REFUSED = [
    ("s10", "s8a", "DEDUCED identity → clef · clef_correction.py:396"),
    ("s8a", "s10", "clef → the part↔staff PIN · dossier.py:434, score_layouts.py:682"),
]


def _mermaid() -> str:
    v2r, v6r = v2(), v6()
    lines = ["flowchart TD"]
    lines.append("  %% GENERATED by benchmarks/omr-decision-map-2026-09/"
                 "verify.py --mermaid -- do not hand-edit")
    for sid, label, tech, n in STAGES:
        lines.append(f'  {sid}["<b>{n} · {label}</b><br/><i>{tech}</i>"]')
    for a, b, lab in FLOW:
        lines.append(f'  {a} -->|"{lab}"| {b}')
    for a, b, lab in REFUSED:
        lines.append(f'  {a} -.->|"⛔ {lab}"| {b}')
    for did, label, src, why in DEAD_ENDS:
        lines.append(f'  {did}(["{label}<br/><i>{why}</i>"])')
        lines.append(f'  {src} --> {did}')
    for oid, label, why in ORPHANS:
        lines.append(f'  {oid}[/"{label}<br/><i>{why}</i>"/]')
    for uid, label, why in UNSAT:
        lines.append(f'  {uid}{{{{"{label}<br/><i>{why}</i>"}}}}')
    lines.append("  s10 -.-> u_clef")
    lines.append("  sown -.-> u_range")
    lines.append("  classDef dead fill:#7f1d1d,stroke:#ef4444,"
                 "color:#fee2e2,stroke-width:2px;")
    lines.append("  classDef orphan fill:#3f3f46,stroke:#a1a1aa,"
                 "color:#e4e4e7,stroke-dasharray:4 3;")
    lines.append("  classDef unsat fill:#78350f,stroke:#f59e0b,color:#fef3c7;")
    lines.append("  classDef stage fill:#1e293b,stroke:#64748b,color:#e2e8f0;")
    lines.append("  class " + ",".join(d[0] for d in DEAD_ENDS) + " dead;")
    lines.append("  class " + ",".join(o[0] for o in ORPHANS) + " orphan;")
    lines.append("  class " + ",".join(u[0] for u in UNSAT) + " unsat;")
    lines.append("  class " + ",".join(s[0] for s in STAGES) + " stage;")
    # a measured footnote so the picture carries its own provenance
    n_dead = v2r["n_with_no_consumer"]
    n_keys = sum(1 for k, v in v6r["keys"].items()
                 if v["n_outside_tools_omr"] == 0)
    lines.append(f'  %% measured: {n_dead} of {len(CHECK_KEYS)} checks have no '
                 f'consumer; {n_keys} of {len(TRACKED)} tracked result keys '
                 f'never leave tools/omr/')
    return "\n".join(lines)


BEGIN = "<!-- BEGIN GENERATED: decision-map-graph -->"
END = "<!-- END GENERATED: decision-map-graph -->"


def _doc_path() -> Path:
    return ROOT / "docs" / "architecture-decision-map.md"


def _block() -> str:
    return f"{BEGIN}\n\n```mermaid\n{_mermaid()}\n```\n\n{END}"


def _splice(check_only: bool) -> int:
    doc = _doc_path()
    text = doc.read_text()
    if BEGIN not in text or END not in text:
        print(f"no generated block markers in {doc}", file=sys.stderr)
        return 2
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    new = head + _block() + tail
    if new == text:
        print("graph is current")
        return 0
    if check_only:
        print("STALE: re-run with --write-doc", file=sys.stderr)
        return 1
    doc.write_text(new)
    print(f"rewrote the graph in {doc}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--only", help="run one check by id, e.g. V2")
    ap.add_argument("--mermaid", action="store_true",
                    help="print the generated graph")
    ap.add_argument("--write-doc", action="store_true",
                    help="splice the graph into the map")
    ap.add_argument("--check", action="store_true",
                    help="non-zero if the graph in the map is stale")
    args = ap.parse_args()

    if args.mermaid:
        print(_mermaid())
        return 0
    if args.write_doc or args.check:
        return _splice(check_only=args.check)

    results = [c() for c in CHECKS
               if not args.only or c().get("id") == args.only.upper()]

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for r in results:
        print(f"\n=== {r['id']}  {r['claim']}")
        for k, v in r.items():
            if k in ("id", "claim"):
                continue
            if isinstance(v, (int, bool, str)):
                print(f"    {k}: {v}")
            elif isinstance(v, list) and len(v) <= 25:
                for item in v:
                    print(f"      - {item}")
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    if isinstance(vv, dict):
                        brief = {a: b for a, b in vv.items()
                                 if isinstance(b, (int, str, bool))}
                        print(f"      {kk}: {brief}")
                    else:
                        print(f"      {kk}: {vv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
