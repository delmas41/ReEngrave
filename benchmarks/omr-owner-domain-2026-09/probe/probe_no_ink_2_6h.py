"""ROADMAP 2.6h — price `no_ink_under_box` on fresh one-page re-gathers.

Litolff pdf idx 3, Breitkopf pdf idx 1 (an ORDINARY-page control each) and
Litolff pdf idx 4 (one of §2.6g's own 4 confirmed-blank pages; pdf idx
8/10/13 attempted twice and not reached this session -- see FINDINGS
§2.6h). `--no-surya --no-ocr`, weights `deepscoresv2-yolov8l-hollow-
graft-shift09-2026-09-04.pt` (CLAUDE.md §5a), gathered by THIS lane
(`benchmarks/omr-owner-domain-2026-09/out/2.6h/`). Each record read ONLY
via `tools.omr.staged.record_io.load_record`, ONCE.

For every `notehead_is_not_a_notehead` verdict decided `no_ink_under_box`:
its own `Q.GLYPH_BOX` (class, page box), its `Q.NOTEHEAD_INK` row's `ink_raw`
/`ink_net`, and its STAFF's `Q.STAFF_LINES`/`Q.STAFF_SPACING` (for the crop
ruler). Also looks up `CONFIRMED_BLANK_SUBJECTS` directly (§2.6g's own 4
crops), independent of whether this lane's rule refuses them, so a miss is
reported as a miss rather than silently absent.

    python3 benchmarks/omr-owner-domain-2026-09/probe/probe_no_ink_2_6h.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged import export as EXP  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "out" / "2.6h"

RECORDS = [
    ("litolff-p3", str(OUT_DIR / "litolff-p3.record.json"),
     "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
     "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
     "1870--imslp984073.pdf"),
    ("breitkopf-p1", str(OUT_DIR / "breitkopf-p1.record.json"),
     "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
     "symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--"
     "imslp317803.pdf"),
    # ROADMAP 2.6h's own targeted pricing: the exact four PDF pages §2.6g's
    # 14-crop sample identified as isolated blanks (crops 01/04/08/12,
    # `out/print/2.6g-owner-not-read-{01,04,08,12}.png`), re-gathered here
    # under THIS lane's own code so `Q.NOTEHEAD_INK` exists on them -- the
    # whole-movement record they came from predates this quantity and is
    # off-limits to re-gather (another session's worktree, CLAUDE.md §5a).
    # Page 4 alone first (a combined 4-page run looked stalled under heavy
    # contention from a concurrent whole-movement gather on this machine
    # and was killed; a single-page retry of the SAME page completed fine
    # -- it was contention, not a hang), pages 8/10/13 together after.
    ("litolff-p4", str(OUT_DIR / "litolff-p4.record.json"),
     "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
     "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
     "1870--imslp984073.pdf"),
    ("litolff-p8-10-13", str(OUT_DIR / "litolff-p8-10-13.record.json"),
     "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
     "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
     "1870--imslp984073.pdf"),
]

#: The 4 subjects §2.6g's own read-by-eye confirmed as isolated blanks
#: (crops 01, 04, 08, 12) -- looked up directly, independent of whether
#: THIS lane's rule refuses them, so a miss is reported as a miss rather
#: than silently absent from the output.
CONFIRMED_BLANK_SUBJECTS = {
    "glyph/10/1/8/8/6": "2.6g crop 01",
    "glyph/4/1/0/1/0": "2.6g crop 04",
    "glyph/8/1/2/18/1": "2.6g crop 08",
    "glyph/13/0/2/6/4": "2.6g crop 12",
}


def _staff_of(glyph_subject: str) -> str:
    _, p, sysm, st, _cell, _gi = glyph_subject.split("/")
    return f"staff/{p}/{sysm}/{st}"


def main() -> int:
    manifest = {"roadmap_item": "2.6h", "records": []}
    for label, path, pdf in RECORDS:
        if not Path(path).exists():
            print(f"{label}: NOT YET WRITTEN ({path})")
            manifest["records"].append({"label": label, "path": path,
                                        "status": "missing"})
            continue
        t0 = time.time()
        result = load_record(path)
        t_load = time.time() - t0
        rec = result["record"]
        print(f"{label}: loaded in {t_load:.1f}s: "
              f"{len(rec['observations'])} observations, "
              f"{len(rec['verdicts'])} verdicts")

        # ── notes written / refused, via the real exporter, no re-gather ──
        _, report = EXP.to_musicxml(result)
        notes_not_written = report.get("notes_not_written", {})

        box_by_subject = {}
        ink_by_subject = {}
        staff_lines = {}
        staff_spacing = {}
        for o in rec["observations"]:
            q, s = o["quantity"], o["subject"]
            if q == "glyph_box":
                box_by_subject[s] = o
            elif q == "notehead_ink":
                ink_by_subject[s] = o
            elif q == "staff_lines":
                staff_lines[s] = o
            elif q == "staff_spacing":
                staff_spacing[s] = o

        superseded = {v["supersedes"] for v in rec["verdicts"]
                     if v.get("supersedes")}
        by_reason = Counter()
        no_ink_rows = []
        for v in rec["verdicts"]:
            if v["quantity"] != Q.NOTEHEAD_IS_NOT_A_NOTEHEAD:
                continue
            if v["id"] in superseded or v.get("outcome") != "decided" \
                    or v.get("value") is not True:
                continue
            by_reason[v.get("reason")] += 1
            if v.get("reason") != "no_ink_under_box":
                continue
            sub = v["subject"]
            box = box_by_subject.get(sub)
            ink = ink_by_subject.get(sub)
            st = _staff_of(sub)
            lines = staff_lines.get(st)
            sp = staff_spacing.get(st)
            if box is None or ink is None or lines is None or sp is None:
                continue
            no_ink_rows.append({
                "subject": sub,
                "class": box["value"][0],
                "bbox_page_px": (box.get("detail") or {}).get(
                    "bbox_page_px"),
                "ink_raw": (ink.get("detail") or {}).get("ink_raw"),
                "ink_net": (ink.get("detail") or {}).get("ink_net"),
                "staff_lines": [float(y) for y in lines["value"]],
                "staff_spacing": float(sp["value"]),
            })

        n_notehead_ink_rows = sum(
            1 for o in rec["observations"] if o["quantity"] == "notehead_ink")

        # ── §2.6g's own 4 confirmed-blank subjects, looked up directly ────
        nn_verdict = {}
        for v in rec["verdicts"]:
            if v["quantity"] != Q.NOTEHEAD_IS_NOT_A_NOTEHEAD:
                continue
            if v["id"] in superseded:
                continue
            nn_verdict[v["subject"]] = v
        confirmed = []
        for sub, tag in CONFIRMED_BLANK_SUBJECTS.items():
            if sub not in box_by_subject:
                continue
            ink = ink_by_subject.get(sub)
            v = nn_verdict.get(sub)
            confirmed.append({
                "subject": sub, "tag": tag,
                "notehead_ink_value": ink.get("value") if ink else None,
                "notehead_ink_detail": (ink.get("detail") if ink else None),
                "verdict_outcome": v.get("outcome") if v else None,
                "verdict_value": v.get("value") if v else None,
                "verdict_reason": v.get("reason") if v else None,
            })
            print(f"{label}: CONFIRMED BLANK {sub} ({tag}): "
                  f"notehead_ink={ink.get('value') if ink else 'MISSING'} "
                  f"verdict={v.get('reason') if v else 'MISSING'}")

        manifest["records"].append({
            "label": label, "path": path, "pdf": pdf,
            "status": "ok",
            "load_seconds": round(t_load, 1),
            "n_notehead_ink_rows": n_notehead_ink_rows,
            "notehead_is_not_a_notehead_by_reason": dict(by_reason),
            "written_notes": report.get("written", {}).get("notes"),
            "notes_not_written": notes_not_written,
            "no_ink_under_box_rows": no_ink_rows,
            "confirmed_blank_subjects": confirmed,
        })
        print(f"{label}: notehead_is_not_a_notehead by reason: "
              f"{dict(by_reason)}")
        print(f"{label}: no_ink_under_box = "
              f"{by_reason.get('no_ink_under_box', 0)} of "
              f"{n_notehead_ink_rows} notehead_ink rows")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "no-ink-2.6h-crop-data.json").write_text(
        json.dumps(manifest, indent=2))
    print(f"wrote {OUT_DIR / 'no-ink-2.6h-crop-data.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
