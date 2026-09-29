"""ROADMAP 2.6g — probe of the 345 `owner_not_read` notes on the fresh
whole-movement Litolff record gathered 2026-09-29 on `23f4fa9e` (2.6c hard
gate, 2.6d CV rungs, 2.6e tied/no_evidence, 2.6f own-rim all in).

Record read ONLY via `tools.omr.staged.record_io.load_record`, ONCE, here.
Writes one small JSON (`out/owner-not-read-2.6g-breakdown.json`) and does
not touch the source record or its worktree.

Method:
  1. Load the record once.
  2. Confirm 345 by an in-process `to_musicxml` (no re-gather, no file
     write of the record) with `export.Record.verdict` wrapped to capture
     every subject whose owner abstains under `OWNER_NOT_READ_REASONS`
     (`export.py:967-976`'s own predicate, reproduced by observation, not
     re-derived).
  3. For each captured subject: its OWN `glyph_owner` verdict (already
     decided on this record -- 2.6c/2.6e are already IN this gather, so no
     readjudication is needed for the reason/detail), its `Q.GLYPH_BAND_
     DISTANCE` rows (candidate staff -> spaces), its `Q.LEDGER_RUNG_INK`
     rows (did the CV reader run here, and what did it find), and its TWIN
     -- the other glyph subject GATHER's own `gather_ownership_evidence`
     paired it with (same category, different staff, same system, IoU >
     `gather.CONTEST_IOU` (0.3) -- the EXACT predicate GATHER used to file
     the contest, replayed here over `Q.GLYPH_BOX` rows already in memory,
     not re-measured or approximated).
  4. Whether the twin (if any) was ALSO dropped `owner_not_read`, was
     WRITTEN (decided, naming a staff), or has no verdict at all.

    python3 benchmarks/omr-owner-domain-2026-09/probe/probe_owner_not_read_2_6g.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged import export as EXP  # noqa: E402
from tools.omr.staged.adjudicators import ownership as OWN  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

RECORD_PATH = (
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
    "regather-20260929/benchmarks/acceptance/out/beethoven5-litolff/"
    "beethoven5-litolff-whole-movement-20260929T104646Z.record.json")

OUT = Path(__file__).resolve().parent.parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

CONTEST_IOU = 0.3  # gather.py's own constant, restated for the replay


def _iou(a, b) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _staff_of(glyph_subject: str) -> str:
    _, p, sysm, st, _cell, _gi = glyph_subject.split("/")
    return f"staff/{p}/{sysm}/{st}"


def _page_system(glyph_subject: str):
    _, p, sysm, _st, _cell, _gi = glyph_subject.split("/")
    return int(p), int(sysm)


def main() -> int:
    t0 = time.time()
    result = load_record(RECORD_PATH)  # THE ONE READ
    t_load = time.time() - t0
    rec = result["record"]
    print(f"loaded in {t_load:.1f}s: "
          f"{len(rec['observations'])} observations, "
          f"{len(rec['verdicts'])} verdicts")

    # ── 1. reproduce the 345 by an in-process export, no re-gather ────────
    captured: dict = {}
    orig_verdict = EXP.Record.verdict

    def patched(self, quantity, subject):
        v = orig_verdict(self, quantity, subject)
        if (quantity == Q.GLYPH_OWNER and v
                and v.get("outcome") == "abstained"
                and v.get("reason") in OWN.OWNER_NOT_READ_REASONS):
            captured[subject] = v
        return v

    EXP.Record.verdict = patched
    t1 = time.time()
    try:
        xml, report = EXP.to_musicxml(result)
    finally:
        EXP.Record.verdict = orig_verdict
    t_export = time.time() - t1
    reported = report["notes_not_written"].get("owner_not_read", 0)
    print(f"export in {t_export:.1f}s: report owner_not_read={reported}, "
          f"captured subjects={len(captured)}")

    # ── 2. index only what we need, from the SAME in-memory result ────────
    box_by_subject: dict = {}
    band_by_subject: dict = defaultdict(list)
    rung_ink_by_subject: dict = defaultdict(list)
    by_page_system: dict = defaultdict(list)
    for o in rec["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            box_by_subject[s] = o
            by_page_system[_page_system(s)].append(s)
        elif q == "glyph_band_distance":
            band_by_subject[s].append(o)
        elif q == "ledger_rung_ink":
            rung_ink_by_subject[s].append(o)

    # every glyph_owner verdict, standing (supersedes-resolved), indexed by
    # subject -- so the twin's OWN verdict can be read with no re-decision.
    superseded = {v["supersedes"] for v in rec["verdicts"]
                  if v.get("supersedes")}
    owner_verdict: dict = {}
    _fallback: dict = {}
    for v in rec["verdicts"]:
        if v["quantity"] != Q.GLYPH_OWNER:
            continue
        _fallback[v["subject"]] = v
        if v["id"] not in superseded:
            owner_verdict[v["subject"]] = v
    for s, v in _fallback.items():
        owner_verdict.setdefault(s, v)

    def find_twin(sub: str):
        o = box_by_subject.get(sub)
        if o is None:
            return None, 0.0
        bb = o["detail"]["bbox_page_px"]
        cat = o["detail"].get("category")
        my_staff = _staff_of(sub)
        ps = _page_system(sub)
        best, best_iou = None, 0.0
        for other in by_page_system.get(ps, ()):
            if other == sub or _staff_of(other) == my_staff:
                continue
            oo = box_by_subject[other]
            if oo["detail"].get("category") != cat:
                continue
            v = _iou(bb, oo["detail"]["bbox_page_px"])
            if v > CONTEST_IOU and v > best_iou:
                best, best_iou = other, v
        return best, best_iou

    # ── 3. per-subject detail ──────────────────────────────────────────
    by_reason = Counter()
    rows = []
    for sub, v in sorted(captured.items()):
        reason = v.get("reason")
        by_reason[reason] += 1
        bands = band_by_subject.get(sub, [])
        candidates = [
            {"staff": b["detail"].get("candidate"),
             "own": b["detail"].get("own"),
             "distance_spaces": round(float(b["value"]), 3)
             if isinstance(b.get("value"), (int, float)) else b.get("value")}
            for b in bands]
        rungs = rung_ink_by_subject.get(sub, [])
        rung_summary = {
            "n_rows": len(rungs),
            "n_true": sum(1 for r in rungs if r.get("value") is True),
            "n_false": sum(1 for r in rungs if r.get("value") is False),
            "n_abstained": sum(1 for r in rungs if r.get("value") is None),
        }
        ledger = (v.get("detail") or {}).get("ledger")
        sides = (ledger or {}).get("sides") or {}
        twin, twin_iou = find_twin(sub)
        twin_v = owner_verdict.get(twin) if twin else None
        if twin_v is None:
            twin_status = "no_twin_found"
        elif (twin_v.get("outcome") == "abstained"
              and twin_v.get("reason") in OWN.OWNER_NOT_READ_REASONS):
            twin_status = "twin_also_owner_not_read"
        elif twin_v.get("outcome") == "decided":
            twin_status = "twin_decided_" + (
                "self" if twin_v.get("value") == _staff_of(twin) else "other")
        else:
            twin_status = f"twin_{twin_v.get('outcome')}_{twin_v.get('reason')}"
        rows.append({
            "subject": sub, "reason": reason,
            "candidates": candidates,
            "ledger_sides": sides,
            "ledger_rung_ink": rung_summary,
            "twin": twin, "twin_iou": round(twin_iou, 3),
            "twin_status": twin_status,
        })

    twin_status_counts = Counter(r["twin_status"] for r in rows)
    ledger_expected_found = []
    for r in rows:
        for staff, sd in r["ledger_sides"].items():
            ledger_expected_found.append(
                {"reason": r["reason"], "expected": sd.get("expected"),
                 "found": sd.get("found"), "toward": sd.get("toward"),
                 "sources": sd.get("sources") or {}})

    summary = {
        "record": RECORD_PATH,
        "load_seconds": round(t_load, 1),
        "export_seconds": round(t_export, 1),
        "reported_owner_not_read": reported,
        "captured_owner_not_read": len(captured),
        "by_reason": dict(by_reason),
        "twin_status_counts": dict(twin_status_counts),
        "n_ledger_sides_seen": len(ledger_expected_found),
        "n_ledger_sides_with_cv_source": sum(
            1 for d in ledger_expected_found
            if any(v == "cv_ink" for v in d["sources"].values())),
        "n_rows_with_any_ledger_rung_ink": sum(
            1 for r in rows if r["ledger_rung_ink"]["n_rows"] > 0),
        "n_rows_with_ledger_rung_ink_true": sum(
            1 for r in rows if r["ledger_rung_ink"]["n_true"] > 0),
    }
    print(json.dumps(summary, indent=2))

    (OUT / "owner-not-read-2.6g-breakdown.json").write_text(json.dumps({
        "summary": summary, "rows": rows}, indent=1, default=str))

    # ── 4. stratified sample of 16, by twin fate (the only reason on this
    # record is `far_no_rungs`; the axis the task asks to stratify by
    # collapses to one value, so the twin-fate breakdown -- whether the
    # note vanishes entirely or is written on the twin's own staff -- is
    # used instead, proportioned to its own population) ───────────────────
    import random
    rng = random.Random(2026092916)
    by_status: dict = defaultdict(list)
    for r in rows:
        by_status[r["twin_status"]].append(r)
    for v in by_status.values():
        rng.shuffle(v)
    targets = {"twin_also_owner_not_read": 12, "twin_decided_self": 3,
               "twin_decided_other": 1}
    sample = []
    for status, n in targets.items():
        sample.extend(by_status.get(status, [])[:n])
    print(f"sampled {len(sample)} of 16 target "
          f"({ {k: len(by_status.get(k, [])[:v]) for k, v in targets.items()} })")

    # geometry + the exact CV windows + any nearby detector `ledgerLine`
    # boxes, for the crop-cutting script (PDF-only, no second record read).
    geo: dict = {}
    for o in rec["observations"]:
        if o["quantity"] in ("staff_lines", "staff_spacing"):
            geo.setdefault(o["subject"], {})[o["quantity"]] = o["value"]
    ledger_boxes_by_ps: dict = defaultdict(list)
    for s, o in box_by_subject.items():
        if o["value"][0] == "ledgerLine":
            d = o["detail"]
            if "bbox_page_px" in d:
                ledger_boxes_by_ps[_page_system(s)].append(
                    {"subject": s, "bbox_page_px": d["bbox_page_px"]})

    crop_jobs = []
    for r in sample:
        sub = r["subject"]
        ps = _page_system(sub)
        cand_geo = {c["staff"]: geo.get(c["staff"], {}) for c in r["candidates"]}
        rung_rows = [
            {"candidate": o["detail"].get("candidate"),
             "step": o["detail"].get("step"),
             "window_page_px": o["detail"].get("window_page_px"),
             "want_y_page": o["detail"].get("want_y_page"),
             "center": o["detail"].get("center"),
             "left": o["detail"].get("left"),
             "right": o["detail"].get("right"),
             "adjacent": o["detail"].get("adjacent"),
             "value": o.get("value")}
            for o in rung_ink_by_subject.get(sub, [])]
        crop_jobs.append({
            "subject": sub, "reason": r["reason"], "twin_status": r["twin_status"],
            "twin": r["twin"], "candidates": r["candidates"],
            "ledger_sides": r["ledger_sides"],
            "head_box": box_by_subject[sub]["detail"],
            "candidate_geometry": cand_geo,
            "ledger_rung_ink_rows": rung_rows,
            "nearby_detector_ledger_boxes": ledger_boxes_by_ps.get(ps, []),
        })

    (OUT / "owner-not-read-2.6g-crop-data.json").write_text(json.dumps({
        "record": RECORD_PATH, "seed": 2026092916, "targets": targets,
        "jobs": crop_jobs}, indent=1, default=str))
    print(f"wrote {len(crop_jobs)} crop jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
