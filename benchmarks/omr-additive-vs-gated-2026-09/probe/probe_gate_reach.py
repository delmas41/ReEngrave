"""How often does each decision point FIRE, and on what population?

Reach before accuracy. Reads only committed transcription JSONs -- the same
inputs both standing benchmarks use -- so it costs seconds and re-runs nothing.

    python3 benchmarks/omr-additive-vs-gated-2026-09/probe/probe_gate_reach.py

Two families, kept apart on purpose (a scan and an engraving fail differently):

    scan     benchmarks/omr-scan-e2e-2026-09/fixtures/*.graft09.omr.json
    engraved benchmarks/omr-orchestral-e2e/fixtures/*.omr.json

⚠️ These are SINGLE-PAGE (scan) and single-excerpt (engraved) runs, so any
document-scope gate (`absent_instrument`, span composition) is structurally
inert here and a zero from this probe is coverage of nothing, not a null.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Fixtures are gitignored build products; in a worktree they live in the main
# checkout. `OMR_FIXTURE_ROOT` points there.
ROOT = os.environ.get("OMR_FIXTURE_ROOT", ROOT)

WARNING_KEYS = ("clef_register_warning", "key_signature_warning",
                "measure_count_warning", "time_signature_disagreement",
                "key_consistency_warning", "meter_consistency_warning",
                "clef_continuity_warning", "rhythm_sum_warning")

FAMILIES = {
    "scan": os.path.join(
        ROOT, "benchmarks/omr-scan-e2e-2026-09/fixtures/*.graft09.omr.json"),
    "engraved": os.path.join(
        ROOT, "benchmarks/omr-orchestral-e2e/fixtures/*.omr.json"),
}


def staves(doc):
    for page in doc.get("pages", []):
        for sysm in page.get("systems", []):
            for st in sysm.get("staves", []):
                yield page, sysm, st


def detections(doc):
    for _p, _s, st in staves(doc):
        for m in st.get("measures", []):
            for d in m.get("detections", []):
                yield d


def harvest(paths):
    agg = {
        "docs": 0, "pages": 0, "systems": 0, "staves": 0, "measures": 0,
        "detections": 0,
        "clef_source": collections.Counter(),
        "key_signature_source": collections.Counter(),
        "key_signature_unread_reason": collections.Counter(),
        "instrument_source": collections.Counter(),
        "instrument_absent": 0,
        "clef_value": collections.Counter(),
        "conf_bins": collections.Counter(),
        "conf_by_cat": collections.defaultdict(list),
        "vetoes": collections.Counter(),
        "warnings": collections.Counter(),
        "warn_conf": collections.defaultdict(list),
        "meter_source": collections.Counter(),
        "per_doc": [],
    }
    for path in sorted(paths):
        doc = json.load(open(path))
        agg["docs"] += 1
        row = {"name": os.path.basename(path)}
        for key in ("n_cross_staff_duplicates_removed",
                    "n_unladdered_noteheads_dropped",
                    "n_clipped_notehead_fragments_dropped",
                    "n_rhythm_reconciliations",
                    "n_noteheads_total", "n_detections_total",
                    "n_staves_total"):
            val = doc.get(key)
            if isinstance(val, int):
                agg["vetoes"][key] += val
                row[key] = val
        for page in doc.get("pages", []):
            agg["pages"] += 1
            rev = page.get("uncorroborated_meter_changes_reverted")
            if isinstance(rev, int):
                agg["vetoes"]["uncorroborated_meter_changes_reverted"] += rev
            its = page.get("inferred_time_signature") or {}
            if its:
                agg["meter_source"][its.get("source", "?")] += 1
            for wkey in ("clef_register_warning", "key_signature_warning",
                         "measure_count_warning", "time_signature_disagreement",
                         "rhythm_sum_warning", "key_consistency_warning",
                         "meter_consistency_warning"):
                _count_warning(agg, page, wkey)
            for sysm in page.get("systems", []):
                agg["systems"] += 1
                for wkey in ("clef_register_warning", "key_signature_warning",
                             "measure_count_warning",
                             "time_signature_disagreement"):
                    _count_warning(agg, sysm, wkey)
                for st in sysm.get("staves", []):
                    agg["staves"] += 1
                    agg["clef_source"][st.get("clef_source") or "(none)"] += 1
                    agg["clef_value"][st.get("clef") or "(none)"] += 1
                    agg["key_signature_source"][
                        st.get("key_signature_source") or "(none)"] += 1
                    if st.get("key_signature_unread_reason"):
                        agg["key_signature_unread_reason"][
                            st["key_signature_unread_reason"]] += 1
                    src = st.get("instrument_source")
                    agg["instrument_source"][src or "(none)"] += 1
                    if not st.get("instrument"):
                        agg["instrument_absent"] += 1
                    for wkey in WARNING_KEYS:
                        _count_warning(agg, st, wkey)
                    prop = st.get("clef_proposal")
                    if prop:
                        agg["warnings"]["clef_proposal"] += 1
                        agg["warn_conf"]["clef_proposal.confidence_label"] \
                            .append(prop.get("confidence_label", "?"))
                    for m in st.get("measures", []):
                        agg["measures"] += 1
                        for wkey in ("rhythm_sum_warning",):
                            _count_warning(agg, m, wkey)
                        for d in m.get("detections", []):
                            agg["detections"] += 1
                            c = d.get("confidence")
                            if isinstance(c, (int, float)):
                                agg["conf_bins"][round(c - c % 0.05, 2)] += 1
                                agg["conf_by_cat"][
                                    d.get("category") or "?"].append(c)
        agg["per_doc"].append(row)
    return agg


def _count_warning(agg, obj, key):
    val = obj.get(key)
    if not val:
        return
    items = val if isinstance(val, list) else [val]
    for it in items:
        agg["warnings"][key] += 1
        if isinstance(it, dict):
            for cf in ("confidence", "severity"):
                if cf in it:
                    agg["warn_conf"][f"{key}.{cf}"].append(it[cf])


def report(name, agg, out):
    p = lambda *a: print(*a, file=out)
    p(f"\n{'='*72}\n{name.upper()}  "
      f"{agg['docs']} docs / {agg['pages']} pages / {agg['systems']} systems / "
      f"{agg['staves']} staves / {agg['measures']} measures / "
      f"{agg['detections']} detections\n{'='*72}")

    p("\n-- clef_source (reach of clef_correction: it fires only on '(none)') --")
    for k, v in agg["clef_source"].most_common():
        p(f"   {k:24s} {v:6d}  {v/max(1,agg['staves']):6.1%}")
    p("-- clef VALUE --")
    for k, v in agg["clef_value"].most_common():
        p(f"   {k:24s} {v:6d}")

    p("\n-- key_signature_source --")
    for k, v in agg["key_signature_source"].most_common():
        p(f"   {k:34s} {v:6d}")
    if agg["key_signature_unread_reason"]:
        p("-- key_signature_unread_reason (the abstain branch) --")
        for k, v in agg["key_signature_unread_reason"].most_common():
            p(f"   {k[:60]:60s} {v:5d}")

    p("\n-- instrument_source (identity provenance) --")
    for k, v in agg["instrument_source"].most_common():
        p(f"   {k:24s} {v:6d}  {v/max(1,agg['staves']):6.1%}")
    p(f"   staves with NO instrument at all: {agg['instrument_absent']}"
      f"  ({agg['instrument_absent']/max(1,agg['staves']):.1%})")

    p("\n-- meter vote source --")
    for k, v in agg["meter_source"].most_common():
        p(f"   {k:24s} {v:6d}")

    p("\n-- VETO / DISCARD volumes --")
    for k, v in agg["vetoes"].most_common():
        p(f"   {k:44s} {v:7d}")

    p("\n-- CONSISTENCY WARNINGS (Class C: computed, consumed by nobody) --")
    if not agg["warnings"]:
        p("   (none fired)")
    for k, v in agg["warnings"].most_common():
        p(f"   {k:34s} {v:6d}")
    for k, vals in sorted(agg["warn_conf"].items()):
        nums = [x for x in vals if isinstance(x, (int, float))]
        strs = [x for x in vals if isinstance(x, str)]
        if nums:
            nums.sort()
            p(f"   {k}: n={len(nums)} min={nums[0]:.3f} "
              f"med={nums[len(nums)//2]:.3f} max={nums[-1]:.3f}")
        if strs:
            p(f"   {k}: {dict(collections.Counter(strs))}")

    p("\n-- DETECTION CONFIDENCE (export.py reads none of this) --")
    tot = sum(agg["conf_bins"].values())
    cum = 0
    for b in sorted(agg["conf_bins"]):
        cum += agg["conf_bins"][b]
        p(f"   [{b:.2f},{b+0.05:.2f})  {agg['conf_bins'][b]:6d}"
          f"  cum {cum/max(1,tot):6.1%}")
    p("   by category (n, median, share under 0.40):")
    for cat, vals in sorted(agg["conf_by_cat"].items(),
                            key=lambda kv: -len(kv[1])):
        vals = sorted(vals)
        lo = sum(1 for v in vals if v < 0.40) / len(vals)
        p(f"     {cat:16s} n={len(vals):6d} med={vals[len(vals)//2]:.3f}"
          f"  <0.40: {lo:5.1%}")

    p("\n-- per document --")
    for row in agg["per_doc"]:
        p("   " + row["name"][:52].ljust(54) + "  " + "  ".join(
            f"{k.replace('n_','').replace('_removed','').replace('_dropped','')}"
            f"={v}" for k, v in row.items() if k != "name"))


def main():
    out = sys.stdout
    for fam, pattern in FAMILIES.items():
        paths = glob.glob(pattern)
        if fam == "engraved":
            paths = [p for p in paths if "graft09" not in p
                     and "restamp" not in p]
        report(fam, harvest(paths), out)


if __name__ == "__main__":
    main()
