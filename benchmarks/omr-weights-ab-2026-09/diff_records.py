#!/usr/bin/env python3
"""Diff two staged records built from the SAME pages, differing only in
`--weights` — Sean's method (DECISIONS 2026-09-29): "take newly grafted
weights and add them to a copy of production and compare the 2" at the
output of GATHER + ADJUDICATE ("stage 2"). Detector-level box counts
against a DIFFERENT model are explicitly not the test; this script only
ever compares two runs of the SAME staged pipeline over the SAME pages.

What it reports, per family (default: rest):
  1. GATHER — raw boxes read (`Q.REST` observations), by class.
  2. ADJUDICATE — every VERDICT and ABSTENTION quantity filed on a glyph
     subject that carries a `Q.REST` observation (so "ownership outcomes"
     means `Q.GLYPH_OWNER`, "refusals by reason" covers every quantity,
     `Q.REST_IS_NOT_A_REST` included), tallied by (quantity, outcome/state,
     value-or-reason).
  3. Where Sean's rest-queue verdicts (`benchmarks/omr-queue-rests-2026-09/
     verdicts/`) cover a gathered CELL, how many of each record's
     SURVIVING rests (gathered, and not decided `rest_is_not_a_rest`) are
     TP / FP / unsure against his boxes.

⚠️ KNOWN LIMITATION on (3), flagged rather than hidden: the match is by
CELL ADDRESS (page, system, staff, measure) + CLASS, counted, not by
sub-pixel IoU of the two canonical-frame boxes. `Q.REST`'s own detail
carries `x0/y0/x1/y1` in the SAME per-cell canonical frame the labeling UI
cuts cells in (`measure_extractor._upscale_to_canonical`), so a geometric
IoU match is possible in principle — it is not done here because that
canonical frame is proven NOT constant across cells (CLAUDE.md / `Q.
CELL_STAFF_SPACE`: 100px nominal, 19-50px on 2/3 of an engraved fixture's
cells depending on a width-vs-height scaling fallback), and confirming the
two cell-cutting paths (gather's runtime frame vs. the labeling corpus's
own recut) agree on that fallback was out of scope for this harness. A
per-cell class COUNT is the honest, cheap alternative: exact where a cell
holds 0 or 1 of a class (the common case), ambiguous only where a cell
holds 2+ of the SAME class, which this script flags rather than guesses.

Usage:
    python3 diff_records.py --a recA.json --b recB.json \\
        --label-a production --label-b candidate \\
        --family rest --verdicts-dir ../omr-queue-rests-2026-09 \\
        --out-json out/pair/summary.json --out-md out/pair/TABLE.md
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from tools.omr.staged import record_io  # noqa: E402

REST_CLASSES = ("restWhole", "restHalf", "restQuarter", "rest8th",
                "rest16th", "restHBar")

FAMILY_GATHER_QUANTITY = {
    "rest": "rest",
}


def cell_key_of(glyph_key: str) -> str:
    parts = glyph_key.split("/")
    assert parts[0] == "glyph", glyph_key
    return "/".join(["cell"] + parts[1:5])


def load(path: str) -> dict:
    """The CLI (`tools.omr.staged.__main__`) writes its WHOLE result dict
    (`record`, `summary`, `adjudication`, `stopped_after`, `weight_routing`,
    `provenance`) to `--out`, not `Log.to_json()` bare -- so the
    observations/abstentions/verdicts this module wants are nested one
    level down, under `["record"]`. Reading `rec["observations"]` directly
    silently sees an empty list on a real CLI-written file (`{}.get(...,
    [])` never raises) -- caught by `test_diff_records.py`'s fixture,
    which is shaped exactly like a real `--out` file for this reason."""
    outer = record_io.load_record(path)
    return outer.get("record", outer)


def family_glyph_subjects(rec: dict, family: str) -> dict[str, dict]:
    """{glyph_subject_key: the Q.<family> Observation dict} — one entry per
    glyph this family's own GATHER quantity fired on. A glyph can only carry
    ONE `Q.REST` row (one detection = one glyph subject, per `gather.py`)."""
    q = FAMILY_GATHER_QUANTITY[family]
    out = {}
    for o in rec.get("observations", []):
        if o["quantity"] == q:
            out[o["subject"]] = o
    return out


def gather_counts(rec: dict, family: str) -> collections.Counter:
    subs = family_glyph_subjects(rec, family)
    return collections.Counter(o["value"] for o in subs.values())


def adjudicate_census(rec: dict, family_glyphs: dict[str, dict]) -> dict:
    """Every Verdict/Abstention filed EXACTLY on one of `family_glyphs`'
    subjects, tallied by quantity.

    Returns {quantity: {"verdicts": Counter[(outcome, value_or_reason)],
                         "abstentions": Counter[reason]}}
    """
    wanted = set(family_glyphs)
    out: dict[str, dict] = {}
    for v in rec.get("verdicts", []):
        if v["subject"] not in wanted:
            continue
        slot = out.setdefault(v["quantity"], {"verdicts": collections.Counter(),
                                               "abstentions": collections.Counter()})
        key = (v["outcome"], _short(v["value"]), v["reason"])
        slot["verdicts"][key] += 1
    for a in rec.get("abstentions", []):
        if a["subject"] not in wanted:
            continue
        slot = out.setdefault(a["quantity"], {"verdicts": collections.Counter(),
                                               "abstentions": collections.Counter()})
        slot["abstentions"][a["reason"]] += 1
    return out


def _short(value):
    """Verdict values can be nested dicts (e.g. glyph_owner's) — keep the
    census key small and printable."""
    if isinstance(value, dict):
        return tuple(sorted((k, v) for k, v in value.items()
                             if isinstance(v, (str, int, float, bool, type(None)))))
    if isinstance(value, list):
        return tuple(value)
    return value


def surviving_rests(rec: dict, family_glyphs: dict[str, dict]) -> dict[str, str]:
    """{glyph_subject_key: rest_class} for every rest glyph NOT decided
    `rest_is_not_a_rest`=True. A NARROWED or ABSTAINED verdict, or no
    verdict at all, leaves the glyph standing — refusal must be a DECIDED
    True, matching the rest of this codebase's rule that abstaining never
    becomes an answer (CLAUDE.md rule 8)."""
    refused = set()
    for v in rec.get("verdicts", []):
        if v["quantity"] != "rest_is_not_a_rest":
            continue
        if v["outcome"] == "decided" and v["value"] is True:
            refused.add(v["subject"])
    return {k: o["value"] for k, o in family_glyphs.items() if k not in refused}


def load_verdicts_index(verdicts_dir: Path, cells_json: Path) -> dict:
    """{(pdf_basename, page, system, staff, measure):
        Counter[class] of TP / FP / unsure} from Sean's rest-queue triage.

    Cross-references `cells.json` (cell_id -> pdf/page/system/staff/measure)
    with each `<cell_id>.verdict.json` (per-detection verdict + class)."""
    cells = json.loads(cells_json.read_text())
    by_id = {c["cell_id"]: c for c in cells}
    out: dict[tuple, dict[str, collections.Counter]] = {}
    for vf in sorted(verdicts_dir.glob("*.verdict.json")):
        cell_id = vf.stem.replace(".verdict", "")
        c = by_id.get(cell_id)
        if c is None:
            continue
        pdf_base = Path(c["pdf"]).name
        addr = (pdf_base, c["page"], c["system_index"], c["staff_index"],
                c["measure_index"])
        data = json.loads(vf.read_text())
        bucket = out.setdefault(addr, {"TP": collections.Counter(),
                                        "FP": collections.Counter(),
                                        "unsure": collections.Counter()})
        for d in data.get("detections", []):
            verdict = d.get("human_corrected_class") and d["verdict"] or d["verdict"]
            klass = d.get("human_corrected_class") or d.get("model_predicted_class")
            if d["verdict"] in ("TP", "FP", "unsure"):
                bucket[d["verdict"]][klass] += 1
        for d in data.get("added_detections", []):
            klass = d.get("human_corrected_class") or d.get("model_predicted_class")
            bucket["TP"][klass] += 1
    return out


def cross_reference(rec: dict, family_glyphs: dict[str, dict], pdf_name: str,
                     verdicts_index: dict) -> dict:
    survivors = surviving_rests(rec, family_glyphs)
    per_cell = collections.defaultdict(collections.Counter)
    for glyph_key, klass in survivors.items():
        per_cell[cell_key_of(glyph_key)][klass] += 1

    rows = []
    for cell_key, surv_counts in sorted(per_cell.items()):
        parts = cell_key.split("/")  # cell/p/s/st/c
        page, system, staff, measure = (int(x) for x in parts[1:5])
        addr = (pdf_name, page, system, staff, measure)
        truth = verdicts_index.get(addr)
        if truth is None:
            continue
        for klass in set(surv_counts) | set(truth["TP"]) | set(truth["FP"]):
            rows.append({
                "cell": cell_key, "class": klass,
                "record_surviving": surv_counts.get(klass, 0),
                "sean_tp": truth["TP"].get(klass, 0),
                "sean_fp": truth["FP"].get(klass, 0),
                "sean_unsure": truth["unsure"].get(klass, 0),
            })
    total_matched = sum(min(r["record_surviving"], r["sean_tp"]) for r in rows)
    total_surviving = sum(r["record_surviving"] for r in rows)
    total_sean_tp = sum(r["sean_tp"] for r in rows)
    return {"cells_matched": len(per_cell) and sum(
                1 for c in per_cell if any(
                    verdicts_index.get((pdf_name, *(int(x) for x in c.split("/")[1:5])))
                    for c in [c])),
            "rows": rows,
            "totals": {"record_surviving": total_surviving,
                       "sean_tp": total_sean_tp,
                       "best_case_matched": total_matched}}


def diff_gather(a: collections.Counter, b: collections.Counter) -> dict:
    classes = sorted(set(a) | set(b))
    return {c: {"a": a.get(c, 0), "b": b.get(c, 0), "delta": b.get(c, 0) - a.get(c, 0)}
            for c in classes}


def diff_census(a: dict, b: dict) -> dict:
    out = {}
    for q in sorted(set(a) | set(b)):
        qa = a.get(q, {"verdicts": collections.Counter(), "abstentions": collections.Counter()})
        qb = b.get(q, {"verdicts": collections.Counter(), "abstentions": collections.Counter()})
        verdict_keys = sorted(set(qa["verdicts"]) | set(qb["verdicts"]), key=str)
        abst_keys = sorted(set(qa["abstentions"]) | set(qb["abstentions"]))
        out[q] = {
            "verdicts": [
                {"key": list(k) if isinstance(k, tuple) else k,
                 "a": qa["verdicts"].get(k, 0), "b": qb["verdicts"].get(k, 0),
                 "delta": qb["verdicts"].get(k, 0) - qa["verdicts"].get(k, 0)}
                for k in verdict_keys],
            "abstentions": [
                {"reason": r, "a": qa["abstentions"].get(r, 0),
                 "b": qb["abstentions"].get(r, 0),
                 "delta": qb["abstentions"].get(r, 0) - qa["abstentions"].get(r, 0)}
                for r in abst_keys],
        }
    return out


def render_markdown(summary: dict) -> str:
    lines = [f"# Weights A/B — {summary['label_a']} vs {summary['label_b']}",
             "",
             f"Family: `{summary['family']}`. Pages: `{summary['pages']}`. "
             f"Weights differ; pipeline, pdf and pages are identical.",
             "",
             "## 1. GATHER — boxes by class", "",
             "| class | " + summary['label_a'] + " | " + summary['label_b'] + " | delta |",
             "|---|--:|--:|--:|"]
    for c, d in summary["gather"].items():
        lines.append(f"| {c} | {d['a']} | {d['b']} | {d['delta']:+d} |")
    total_delta = sum(d["delta"] for d in summary["gather"].values())
    lines += ["", f"**Total boxes gathered:** {summary['label_a']} "
                  f"{sum(d['a'] for d in summary['gather'].values())}, "
                  f"{summary['label_b']} "
                  f"{sum(d['b'] for d in summary['gather'].values())} "
                  f"(delta {total_delta:+d})", ""]

    lines += ["## 2. ADJUDICATE — per quantity, verdicts and refusals", ""]
    for q, d in summary["adjudicate"].items():
        any_nonzero = any(r["delta"] for r in d["verdicts"]) or \
            any(r["delta"] for r in d["abstentions"])
        lines.append(f"### `{q}`" + ("" if any_nonzero else " (no difference)"))
        if d["verdicts"]:
            lines += ["", "| outcome/value/reason | a | b | delta |", "|---|--:|--:|--:|"]
            for r in d["verdicts"]:
                lines.append(f"| {r['key']} | {r['a']} | {r['b']} | {r['delta']:+d} |")
        if d["abstentions"]:
            lines += ["", "| abstention reason | a | b | delta |", "|---|--:|--:|--:|"]
            for r in d["abstentions"]:
                lines.append(f"| {r['reason']} | {r['a']} | {r['b']} | {r['delta']:+d} |")
        lines.append("")

    if summary.get("cross_reference"):
        lines += ["## 3. Sean's rest-queue verdicts vs each record's surviving rests", ""]
        for label, xr in summary["cross_reference"].items():
            lines.append(f"### {label}")
            t = xr["totals"]
            lines.append(f"cells with a Sean verdict AND a record rest reading: "
                          f"{len(xr['rows'])} (class, cell) rows — surviving "
                          f"{t['record_surviving']}, Sean TP {t['sean_tp']}, "
                          f"best-case matched (min per cell/class) "
                          f"{t['best_case_matched']}")
            lines += ["", "| cell | class | record surviving | Sean TP | Sean FP | Sean unsure |",
                      "|---|---|--:|--:|--:|--:|"]
            for r in xr["rows"]:
                lines.append(f"| {r['cell']} | {r['class']} | {r['record_surviving']} "
                              f"| {r['sean_tp']} | {r['sean_fp']} | {r['sean_unsure']} |")
            lines.append("")

    zero = (total_delta == 0
            and all(not r["delta"] for d in summary["adjudicate"].values()
                    for r in d["verdicts"] + d["abstentions"]))
    lines += ["## Verdict", "",
              ("**ZERO differences at stage 2.**" if zero else
               "**Differences found** — see deltas above."), ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="record built with weights A")
    ap.add_argument("--b", required=True, help="record built with weights B")
    ap.add_argument("--label-a", default="a")
    ap.add_argument("--label-b", default="b")
    ap.add_argument("--family", default="rest", choices=sorted(FAMILY_GATHER_QUANTITY))
    ap.add_argument("--pdf-name", default=None,
                     help="basename of the pdf gathered, for the cross-reference "
                          "(e.g. brahms--symphony-1-op68--breitkopf-hartel-brahms"
                          "--imslp317803.pdf)")
    ap.add_argument("--verdicts-dir", type=Path, default=None,
                     help="e.g. benchmarks/omr-queue-rests-2026-09/verdicts")
    ap.add_argument("--cells-json", type=Path, default=None,
                     help="e.g. benchmarks/omr-queue-rests-2026-09/cells.json")
    ap.add_argument("--pages", default="?", help="for the report header only")
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, required=True)
    a = ap.parse_args()

    rec_a = load(a.a)
    rec_b = load(a.b)

    glyphs_a = family_glyph_subjects(rec_a, a.family)
    glyphs_b = family_glyph_subjects(rec_b, a.family)

    summary = {
        "family": a.family, "pages": a.pages,
        "label_a": a.label_a, "label_b": a.label_b,
        "record_a": str(a.a), "record_b": str(a.b),
        "gather": diff_gather(gather_counts(rec_a, a.family), gather_counts(rec_b, a.family)),
        "adjudicate": diff_census(adjudicate_census(rec_a, glyphs_a),
                                   adjudicate_census(rec_b, glyphs_b)),
    }

    if a.verdicts_dir and a.cells_json and a.pdf_name:
        vindex = load_verdicts_index(a.verdicts_dir, a.cells_json)
        summary["cross_reference"] = {
            a.label_a: cross_reference(rec_a, glyphs_a, a.pdf_name, vindex),
            a.label_b: cross_reference(rec_b, glyphs_b, a.pdf_name, vindex),
        }

    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(summary, indent=2, default=str))
    a.out_md.parent.mkdir(parents=True, exist_ok=True)
    a.out_md.write_text(render_markdown(summary))
    print(f"wrote {a.out_json} and {a.out_md}")

    total_delta = sum(d["delta"] for d in summary["gather"].values())
    any_adj_delta = any(r["delta"] for d in summary["adjudicate"].values()
                        for r in d["verdicts"] + d["abstentions"])
    if total_delta == 0 and not any_adj_delta:
        print("ZERO differences at stage 2.")
    else:
        print("Differences found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
