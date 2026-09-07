"""MEASURE the scan structural floor instead of estimating it.

Round 1 bracketed it: `floor_low` was the minimum `entire staff` charge over the
engines measured on a row, `floor_high` everything the page-normalising transform
removed. Both are proxies. The floor itself has an exact definition and one
cheap measurement:

    A PERFECT page-faithful reader emits exactly the page-normalised truth.
    Score THAT as the prediction against the RAW truth, and the number you get
    is the OMR-NED such a reader is charged — the floor, on the raw scale.

⚠️ THE DIRECTION THAT MATTERS. This measurement can only be wrong in ONE
direction that flatters us: if the transform DAMAGES the truth, the derived file
is further from the raw truth than a faithful merge would be, the floor comes out
too large, and every `% of achievable` above it comes out too high. The
independence guard exists to stop exactly that. So the edit list is decomposed:

    structural   `entire staff insert/delete` + `entire measure insert/delete`
                 — the condensation itself: truth parts with no printed staff,
                 and the bars inside them.
    residue      everything else — `wrong lyric`, `wrong tie`, `wrong flag/beam`
                 … Some of this is legitimate (chording an aligned divisi really
                 does change note heads); none of it is DEMONSTRABLY legitimate.

The score uses the STRUCTURAL part only. The residue is reported beside it as
the amount by which a credulous reading would overstate us.

CONTROLS, both of which can fail:
  * the three Dvořák rows are 15 parts into 15 staves — the transform is the
    identity there, so their floor must be EXACTLY 0.0. If it is not, the
    transform is distorting the truth and no other row's floor means anything.
  * `n_output_parts` must equal the staves the page prints, per `works.json`.

    OMRNED_PYTHON=/path/to/.venv-omrned/bin/python \\
      python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_structural_floor.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "structural-floor-measured.json"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixtureroot import fixture_root, require_nonempty  # noqa: E402
import page_normalise                                    # noqa: E402
from tools.omr import omr_ned as omr_ned_mod             # noqa: E402

SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"

#: ⚠️ `fixtures/` is gitignored and this worktree has none. The canonical 20-row
#: run was made in the `reconciliation` worktree and `results-normalised-arm-20row.json`
#: names those exact paths — so the floor is bound to the SAME files the headline
#: was scored on, and the binding is CHECKED (every truth's sha256 is compared
#: against the canonical arm's `sha.truth`, and the run refuses on a mismatch)
#: rather than assumed from a path.
#: override with OMR_FIXTURE_ROOT (a directory holding *.truth.musicxml).
FIXTURES = fixture_root(Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation/"
    "benchmarks/omr-scan-e2e-2026-09/fixtures"))
WORKS = SCAN / "works.json"
DERIVED = HERE / "derived-truth-floor"
NORM20 = (ROOT / "benchmarks" / "omr-page-normalise-fixes-2026-09"
          / "results-normalised-arm-20row.json")

#: musicdiff buckets that ARE the condensation, in order of how certainly they
#: are structural. `entire staff insert/delete` is unambiguous — it is a truth
#: PART with no printed staff to pair with. `entire measure insert/delete` is
#: mostly the bars inside those parts, but a bar the transform mangled would also
#: land here, so it forms a second, less certain rung.
STRUCTURAL_CERTAIN = ("entire staff insert/delete",)
STRUCTURAL_LIKELY = ("entire staff insert/delete", "entire measure insert/delete")

#: music21 stamps a fresh 32-hex instrument id on every write, so the derived
#: truth is SEMANTICALLY deterministic and not BYTE-deterministic. The committed
#: control (`probe_derived_truth_unmoved.py`) already normalises these; this
#: reproduces its hash exactly so the two can be compared.
_RANDOM_ID = re.compile(r'"I[0-9a-f]{32}"')


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def canonical_sha(p: Path) -> str:
    """sha256 with music21's random instrument ids masked — the writer's own
    randomness, not a content difference. Identical to the helper in
    `benchmarks/omr-page-normalise-fixes-2026-09/probe_derived_truth_unmoved.py`."""
    return hashlib.sha256(_RANDOM_ID.sub('"I#"', p.read_text()).encode()).hexdigest()


def git_head() -> str:
    out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def load_rows() -> list[dict]:
    doc = json.loads(WORKS.read_text())
    rows = doc["rows"]
    by_id = {r["row_id"]: r for r in rows}
    for row in rows:
        for key in ("staves", "condensation"):
            v = row.get(key)
            if isinstance(v, str) and v.startswith("same-as:"):
                row[key] = by_id[v.split(":", 1)[1]][key]
    return rows


def main() -> int:
    DERIVED.mkdir(exist_ok=True)
    rows = load_rows()
    canon = {r["row_id"]: r for r in json.loads(NORM20.read_text())["rows"]}
    _ctl = json.loads((ROOT / "benchmarks" / "omr-page-normalise-fixes-2026-09"
                       / "derived-truth-bytes.json").read_text())
    bytes_ctl = {r["row_id"]: r["fixed"] for r in _ctl["rows"]
                 if r.get("map_kind") == "works.json hand map"}

    # GATE: every truth fixture must be byte-identical to the one the canonical
    # 20-row arm scored. A floor measured on different files is not a floor for
    # the headline it will be subtracted from.
    binding = []
    for rid, c in canon.items():
        f = FIXTURES / f"{rid}.truth.musicxml"
        got = sha(f) if f.is_file() else None
        binding.append({"row_id": rid, "want": c["sha"]["truth"], "got": got,
                        "ok": got == c["sha"]["truth"]})
    if not all(b["ok"] for b in binding):
        print("FIXTURE BINDING FAILED — refusing to measure:", file=sys.stderr)
        for b in binding:
            if not b["ok"]:
                print("  %s want %s got %s" % (b["row_id"], b["want"], b["got"]),
                      file=sys.stderr)
        return 2

    pairs, entries, skipped = [], [], []
    for row in rows:
        rid = row["row_id"]
        truth = FIXTURES / f"{rid}.truth.musicxml"
        if not truth.is_file():
            skipped.append({"row_id": rid, "reason": "no truth fixture on disk"})
            continue
        norm_xml = DERIVED / f"{rid}.page-normalised.musicxml"
        try:
            report = page_normalise.write(
                truth, row.get("staves"), norm_xml,
                source_reference=row["reference"]["catalog_path"])
        except page_normalise.NoHandMap as exc:
            skipped.append({"row_id": rid, "reason": str(exc),
                            "staves_a_human_would_read": row["page"].get("n_staves")})
            continue
        entries.append({
            "row_id": rid, "work_id": row["work_id"],
            "n_systems": row["page"].get("n_systems"),
            "n_staves_printed": row["page"].get("n_staves"),
            "n_staves_note": row["page"].get("n_staves_note"),
            "n_slots_in_map": len(row.get("staves") or []),
            "transform": {
                "version": report["transform_version"],
                "n_source_parts": report["n_source_parts"],
                "n_output_parts": report["n_output_parts"],
                "exact_duplication_share": report["exact_duplication_share"],
                "divisi_share": report["divisi_share"],
            },
            "sha": {"raw_truth": sha(truth), "derived_truth": sha(norm_xml),
                    "derived_truth_canonical": canonical_sha(norm_xml)},
            "derived_truth_reproduces_committed_control": (
                canonical_sha(norm_xml) == bytes_ctl.get(rid)),
            "identity_transform": report["n_source_parts"] == report["n_output_parts"],
        })
        # THE MEASUREMENT: derived truth AS THE PREDICTION, raw truth as truth.
        pairs.append((rid, norm_xml, truth))

    require_nonempty(pairs, "scoreable (derived truth, raw truth) pairs", FIXTURES)
    scored = omr_ned_mod.score_batch(pairs, detail="AllObjects")
    by_name = {p["name"]: p for p in scored.get("pairs", [])}

    for e in entries:
        s = by_name.get(e["row_id"]) or {}
        cats = s.get("categories") or {}
        certain = sum(v for k, v in cats.items() if k in STRUCTURAL_CERTAIN)
        struct = sum(v for k, v in cats.items() if k in STRUCTURAL_LIKELY)
        residue = s.get("omr_ed", 0) - struct
        den = s.get("truth_symbols", 0) + s.get("pred_symbols", 0)
        e["floor"] = {
            "omr_ned_total": s.get("omr_ned"),
            "omr_ed_total": s.get("omr_ed"),
            "raw_truth_symbols": s.get("truth_symbols"),
            "derived_truth_symbols": s.get("pred_symbols"),
            "denominator": den,
            "unpaired_part_edits": certain,
            "structural_edits": struct,
            "residue_edits": residue,
            "floor_unpaired_parts_only": (certain / den) if den else None,
            "floor_structural_only": (struct / den) if den else None,
            "floor_total": s.get("omr_ned"),
            "categories": cats,
        }
        # the round-1 estimate, for the comparison the coordinator asked for
        c = canon.get(e["row_id"])
        if c and c.get("normalised"):
            raw_cats = c["raw"]["categories"]
            ideal_den = c["raw"]["truth_symbols"] + c["norm"]["truth_symbols"]
            e["round1_estimate"] = {
                "floor_low": raw_cats.get("entire staff insert/delete", 0) / ideal_den,
                "floor_high": (c["raw"]["omr_ed"] - c["norm"]["omr_ed"]) / ideal_den,
            }

    dv = [e for e in entries if e["work_id"].startswith("dvorak")]
    controls = {
        "identity_rows": [e["row_id"] for e in entries if e["identity_transform"]],
        "identity_rows_floor_is_exactly_zero": all(
            e["floor"]["omr_ed_total"] == 0 for e in entries if e["identity_transform"]),
        "identity_row_floors": {e["row_id"]: e["floor"]["omr_ed_total"]
                                for e in entries if e["identity_transform"]},
        "dvorak_rows": [e["row_id"] for e in dv],
        # ⚠️ TWO UNIT ERRORS IN THIS CONTROL BEFORE IT WAS RIGHT, both kept
        # visible because each failed loudly and neither was a real defect in
        # the transform.
        #   1st draft: `n_output_parts == page.n_staves`. `page.n_staves` counts
        #      staves across ALL systems (22 = 2 x 11) while `n_output_parts` is
        #      per PART, so it failed on all ten two-system rows and passed on
        #      all five single-system ones — it was measuring the system count.
        #   2nd draft: `page.n_staves // n_systems`. A printed score SUPPRESSES
        #      tacet staves, so a page's systems need not have equal staff
        #      counts: Beethoven p3 is 11 + 8 and Brahms p2 is 14 + 13, both
        #      documented in `works.json`'s own `n_staves_note`. Integer division
        #      failed on exactly those three rows.
        # What the control can actually assert is that the transform emitted one
        # part per hand-read staff SLOT and dropped none. That the slot count
        # equals the widest system's staff count is stated in `n_staves_note` as
        # prose and is not machine-checkable from this file.
        "output_parts_equal_hand_read_slots": {
            e["row_id"]: (e["transform"]["n_output_parts"] == e["n_slots_in_map"])
            for e in entries},
        "derived_truth_reproduces_committed_control": {
            e["row_id"]: e["derived_truth_reproduces_committed_control"]
            for e in entries},
    }
    controls["fixture_binding"] = {
        "n_rows": len(binding), "all_match_canonical_arm": True,
        "what": "every truth fixture's raw sha256 equals the one "
                "results-normalised-arm-20row.json scored; the run refuses "
                "otherwise"}
    controls["derived_truth_note"] = (
        "`results-normalised-arm-20row.json`'s `sha.normalised_truth` is a RAW "
        "sha256 and cannot be reproduced across runs — music21 stamps a fresh "
        "32-hex instrument id on every write. Reproduction is checked against "
        "`derived-truth-bytes.json`'s CANONICAL hash instead, which masks them. "
        "The arm's `sha.truth` and `sha.pred` are reproducible and are used above.")
    controls["PASS"] = (
        controls["identity_rows_floor_is_exactly_zero"]
        and all(controls["output_parts_equal_hand_read_slots"].values())
        and all(controls["derived_truth_reproduces_committed_control"].values()))

    ed_c = sum(e["floor"]["unpaired_part_edits"] for e in entries)
    ed_s = sum(e["floor"]["structural_edits"] for e in entries)
    ed_r = sum(e["floor"]["residue_edits"] for e in entries)
    den = sum(e["floor"]["denominator"] for e in entries)
    pooled = {
        "n_rows": len(entries),
        "row_ids": [e["row_id"] for e in entries],
        "floor_unpaired_parts_only": ed_c / den,
        "floor_structural_only": ed_s / den,
        "floor_total": (ed_s + ed_r) / den,
        "unpaired_part_edits": ed_c,
        "structural_edits": ed_s,
        "residue_edits": ed_r,
        "residue_share_of_total_floor": ed_r / (ed_s + ed_r) if (ed_s + ed_r) else 0.0,
        "denominator": den,
        "which_to_use": "floor_unpaired_parts_only — the MOST CONSERVATIVE rung. "
                        "A larger floor raises every % of achievable above it, "
                        "which is the one direction the independence guard exists "
                        "to prevent, so the ladder is climbed only as far as the "
                        "evidence is unambiguous. `entire staff insert/delete` is "
                        "unambiguous (a truth PART with no printed staff). "
                        "`entire measure` is mostly the bars inside those parts "
                        "but could also hold a bar the transform mangled. "
                        "`floor_total` additionally holds the residue.",
        "ladder": "unpaired-parts <= structural <= total",
    }
    cats_pool: dict[str, int] = {}
    for e in entries:
        for k, v in e["floor"]["categories"].items():
            cats_pool[k] = cats_pool.get(k, 0) + v
    pooled["categories"] = dict(sorted(cats_pool.items(), key=lambda kv: -kv[1]))

    doc = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/"
                        "probe_structural_floor.py",
        "git_head": git_head(),
        "transform_version": page_normalise.TRANSFORM_VERSION,
        "what_this_is": "the OMR-NED a PERFECT page-faithful reader is charged "
                        "against the raw truth — the structural FLOOR, measured "
                        "rather than estimated. Scored with the derived truth as "
                        "the PREDICTION.",
        "not_a_pipeline_figure": "no prediction of ours appears in this "
                                 "measurement at all. It is a property of "
                                 "(reference encoding, hand-read page map).",
        "structural_buckets": {"certain": list(STRUCTURAL_CERTAIN),
                               "likely": list(STRUCTURAL_LIKELY)},
        "control_history": [
            "output_parts == page.n_staves        — WRONG, page.n_staves is "
            "summed over systems; failed 10 rows",
            "output_parts == n_staves // systems  — WRONG, systems suppress "
            "tacet staves and are unequal (11+8, 14+13); failed 3 rows",
            "output_parts == len(works.json staves map) — correct",
        ],
        "controls": controls,
        "pooled": pooled,
        "rows": entries,
        "skipped": skipped,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")

    print("CONTROLS:", "PASS" if controls["PASS"] else "*** FAIL ***")
    print("  identity-transform rows:", controls["identity_row_floors"])
    print()
    print("%-36s %-9s %-9s %-9s | round-1 est" % (
        "row", "F_unpair", "F_struct", "F_total"))
    for e in entries:
        f = e["floor"]
        r1 = e.get("round1_estimate")
        print("%-36s %-9.4f %-9.4f %-9.4f | %s" % (
            e["row_id"], f["floor_unpaired_parts_only"], f["floor_structural_only"],
            f["floor_total"],
            ("%.4f-%.4f" % (r1["floor_low"], r1["floor_high"])) if r1 else "-"))
    print()
    print("POOLED (%d rows): F_unpaired %.4f  F_structural %.4f  F_total %.4f"
          % (pooled["n_rows"], pooled["floor_unpaired_parts_only"],
             pooled["floor_structural_only"], pooled["floor_total"]))
    print("                  residue %d of %d (%.1f%%)"
          % (
             pooled["residue_edits"], pooled["structural_edits"] + pooled["residue_edits"],
             100 * pooled["residue_share_of_total_floor"]))
    print("top buckets:", list(pooled["categories"].items())[:6])
    print("skipped:", [s["row_id"] for s in skipped])
    return 0 if controls["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
