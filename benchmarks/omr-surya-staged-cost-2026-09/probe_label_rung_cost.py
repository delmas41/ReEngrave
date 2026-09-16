"""Part A of the staged-Surya experiment: the ATTRIBUTABLE numerator.

`docs/scope-surya-staged-optin-2026-09-16.md` §9. What one margin-label read
costs, per rung, per page, with NO DETECTOR in the way -- so the number is
the reader's and not a share of somebody else's gather.

    OMR_SURYA_KEEP_ALIVE=0 python3 -u \\
        benchmarks/omr-surya-staged-cost-2026-09/probe_label_rung_cost.py \\
        --pdf "$PDF" --pages 1-4 --repeats 3 --json-out out/rung-cost.json

⚠️⚠️ IT REFUSES TO RUN AGAINST A RESIDENT SERVER, and that refusal is the
whole instrument. CLAUDE.md's 2026-09-11 correction to its own keep-alive
section: `OMR_SURYA_KEEP_ALIVE=0` does NOT give a run its own worker -- Surya
attaches through its own sentinel to whatever server exists, and the flag
only governs whether it is KEPT. One page once queued ~6 minutes behind a
sibling session. So a timing arm taken while a server is up measures
QUEUEING, and it does not look like it. `--allow-resident` exists only for
deliberately measuring the attached case, and stamps the record so the two
can never be pooled by accident. **Never `pkill`; use
`python3 -m tools.omr.staff_labels_surya --stop`, and only when nothing else
is reading.**

⚠️ REACH BEFORE COST. A rung that is not installed reads nothing in zero
seconds, which is the fastest possible result and means nothing -- the same
shape as the wedge arm's "DEAD at zero" and the dotted-rest arm's positive
control. So every rung's raw / usable / consumable counts travel beside its
seconds, and the CENSUS below exits non-zero when Surya read nothing on any
page-run. A cost with no yield beside it is half a decision.

⚠️ THE PREPARE IS TIMED AND REPORTED APART. `render_page` + `detect_staves`
at dpi 600 is most of this script's wall clock and NONE of it is
attributable to an OCR rung; folding it in would flatter every ratio.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

PDF = (REPO / "library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")


def parse_pages(spec: str):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def _counts(labels, contextual, consumable) -> dict:
    got = [lab for lab in labels if (lab.text or "").strip()]
    return {"raw": len(got),
            "usable": contextual._usable(labels),
            "consumable": consumable(labels)}


def _consumable(labels) -> int:
    """What a CONSUMER keeps, not what the ladder's own merge counts.

    Taken from `benchmarks/omr-label-ladder-2026-09/probe_ladder_rungs.py`
    rather than restated -- `slots.build_reference` and every caller shaped
    like it drop a `low` match, while `contextual._usable` counts `matched`
    alone, so the two genuinely disagree and both are worth reporting.
    """
    return sum(1 for lab in labels
               if lab.matched and lab.instrument
               and lab.confidence in ("high", "medium"))


def _provenance() -> dict:
    """⚠️ A HALF-NAMED TREE IS NOT A NAMED ONE. `commit` and `dirty` are
    written together or neither is: CLAUDE.md records a stamp where
    `rev-parse` succeeded while `status` failed, leaving a record naming a
    COMMIT with dirtiness unknown, which the consumer read as clean."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                                capture_output=True, text=True,
                                check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                                capture_output=True, text=True,
                                check=True).stdout
    except Exception:                                         # noqa: BLE001
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": bool(status.strip()),
            "dirty_files": [ln[3:] for ln in status.splitlines()][:20]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(PDF))
    ap.add_argument("--pages", default="1-4")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--allow-resident", action="store_true",
                    help="measure the ATTACHED case on purpose; stamps the "
                         "record so it can never be pooled with a spawn run")
    args = ap.parse_args(argv)

    from tools.omr import contextual, staff_labels_surya
    from tools.omr import staff_labels_tesseract
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_labels import read_staff_labels

    # ── REACH FIRST ──────────────────────────────────────────────────────
    surya_up = staff_labels_surya.available()
    tess_up = staff_labels_tesseract.available()
    print("rungs: text_layer=on  surya=%s  tesseract=%s"
          % ("on" if surya_up else "NOT INSTALLED",
             "on" if tess_up else "NOT INSTALLED"))
    print("OMR_SURYA_KEEP_ALIVE=%r" % os.environ.get("OMR_SURYA_KEEP_ALIVE"))
    prov = _provenance()
    print("tree: %s dirty=%s" % (prov["commit"], prov["dirty"]))
    if not surya_up:
        print("DEAD: Surya is not installed here. This probe measures the "
              "cost of a rung that cannot run; every number would be zero "
              "and none of them would mean anything.")
        return 2
    if not tess_up:
        print("DEAD: Tesseract is not installed here. The attributable "
              "numerator is Surya + Tesseract and half of it is missing.")
        return 2

    resident = staff_labels_surya.resident_server()
    if resident is not None and not args.allow_resident:
        print("REFUSING TO RUN -- a keep-alive server is resident "
              "(pid %s, port %s)." % (resident.get("pid"),
                                      resident.get("port")))
        print("A rung timed against it measures QUEUEING, not Surya: "
              "OMR_SURYA_KEEP_ALIVE=0 does not give this run its own worker.")
        print("Stop it with `python3 -m tools.omr.staff_labels_surya --stop` "
              "once nothing else is reading -- NEVER `pkill`.")
        return 2

    pages = parse_pages(args.pages)
    rows = []
    for p in pages:
        for rep in range(args.repeats):
            t0 = time.perf_counter()
            pws = detect_staves(render_page(Path(args.pdf), p, dpi=args.dpi))
            t_prepare = time.perf_counter() - t0
            n_staves = len(pws.staves)
            n_systems = len({s.system_index for s in pws.staves})

            before = staff_labels_surya.resident_server()

            t0 = time.perf_counter()
            text = read_staff_labels(pws)
            t_text = time.perf_counter() - t0

            t0 = time.perf_counter()
            surya1 = staff_labels_surya.read_staff_labels_surya(pws)
            t_surya_1 = time.perf_counter() - t0

            # ⚠️ THE SECOND CALL IS THE EXPERIMENT, not a repeat. If the two
            # differ by roughly a model load then the cost is per SPAWN and
            # the single-subprocess merge (§7) is worth more than the flag;
            # if they are equal, something is already resident and this run
            # is measuring the attached case whatever the sentinel said.
            t0 = time.perf_counter()
            surya2 = staff_labels_surya.read_staff_labels_surya(pws)
            t_surya_2 = time.perf_counter() - t0

            t0 = time.perf_counter()
            tess = staff_labels_tesseract.read_staff_labels_tesseract(pws)
            t_tess = time.perf_counter() - t0

            after = staff_labels_surya.resident_server()

            row = {
                "page": p, "repeat": rep,
                "n_staves": n_staves, "n_systems": n_systems,
                "t_prepare_s": round(t_prepare, 3),
                "t_text_s": round(t_text, 3),
                "t_surya_spawn_s": round(t_surya_1, 3),
                "t_surya_second_s": round(t_surya_2, 3),
                "t_tesseract_s": round(t_tess, 3),
                # The number §9's decision rule is written against.
                "t_attributable_s": round(t_surya_1 + t_tess, 3),
                "resident_before": before, "resident_after": after,
                "counts": {
                    "text_layer": _counts(text, contextual, _consumable),
                    "surya": _counts(surya1, contextual, _consumable),
                    "surya_second": _counts(surya2, contextual, _consumable),
                    "tesseract": _counts(tess, contextual, _consumable),
                },
            }
            rows.append(row)
            print("page %d rep %d: %2d staves/%d systems | prepare %6.1fs | "
                  "text %5.2fs(%d) surya %6.1fs(%d) surya2 %6.1fs(%d) "
                  "tess %5.2fs(%d) | attributable %6.1fs"
                  % (p, rep, n_staves, n_systems, t_prepare,
                     t_text, row["counts"]["text_layer"]["raw"],
                     t_surya_1, row["counts"]["surya"]["raw"],
                     t_surya_2, row["counts"]["surya_second"]["raw"],
                     t_tess, row["counts"]["tesseract"]["raw"],
                     row["t_attributable_s"]))

    # ── THE CENSUS ───────────────────────────────────────────────────────
    read_nothing = [(r["page"], r["repeat"]) for r in rows
                    if r["counts"]["surya"]["raw"] == 0]
    attributable = [r["t_attributable_s"] for r in rows]
    summary = {
        "n_page_runs": len(rows),
        "attributable_median_s": round(statistics.median(attributable), 2)
        if attributable else None,
        "attributable_max_s": round(max(attributable), 2)
        if attributable else None,
        "surya_spawn_median_s": round(statistics.median(
            [r["t_surya_spawn_s"] for r in rows]), 2) if rows else None,
        "surya_second_median_s": round(statistics.median(
            [r["t_surya_second_s"] for r in rows]), 2) if rows else None,
        "tesseract_median_s": round(statistics.median(
            [r["t_tesseract_s"] for r in rows]), 2) if rows else None,
        "prepare_median_s": round(statistics.median(
            [r["t_prepare_s"] for r in rows]), 2) if rows else None,
        "census_surya_read_nothing": read_nothing,
        "allow_resident": bool(args.allow_resident),
    }
    print()
    print("median attributable %.1fs/page, max %.1fs over %d page-runs"
          % (summary["attributable_median_s"], summary["attributable_max_s"],
             len(rows)))
    print("  surya spawn median %.1fs, second call median %.1fs, "
          "tesseract median %.1fs, prepare median %.1fs"
          % (summary["surya_spawn_median_s"],
             summary["surya_second_median_s"],
             summary["tesseract_median_s"], summary["prepare_median_s"]))

    out = {"provenance": prov, "args": vars(args), "summary": summary,
           "rows": rows}
    if args.json_out:
        dest = Path(args.json_out)
        if not dest.is_absolute():
            dest = Path(__file__).resolve().parent / dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=2))
        print("wrote", dest)

    if read_nothing:
        print("VOID: Surya read NOTHING on %d page-run(s): %s"
              % (len(read_nothing), read_nothing))
        return 1
    if prov["dirty"]:
        print("⚠️ the tree was DIRTY -- this record does not name a tree.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
