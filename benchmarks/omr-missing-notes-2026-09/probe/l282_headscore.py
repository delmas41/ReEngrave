#!/usr/bin/env python3
"""l282_headscore: every note head of Sean's hand-truth page (Brahms 317803 pdf 0, FULLY LABELED cells), its
written value as his boxes show it (`l281_truth.Truth.derive`), and what ADJUDICATE's standing `Q.DURATION`
verdict of a record says: right / narrowed (the truth is a candidate) / narrowed (it is not) / wrong / no
verdict. First two stages only (CLAUDE.md §6b). ROADMAP 2.82. A reading probe.

  right        decided, and `beats` equals the truth's written value (dots included)
  wrong        decided, and it does not
  narrowed_in  narrowed, the truth value is one of the candidates;  narrowed_out  it is not
  none         no `Q.DURATION` verdict on the matched head at that stage

Heads the derivation cannot judge (no stem box under a head: `no_truth_stem`) are counted apart and never
as right or wrong. Matching is the scorer's own `hand_truth.score.match_boxes` (IoU >= 0.3).

    python3 l282_headscore.py --record R [--json out.json] [--base other.json]   # --base: diff before -> after
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_truth import Truth, in_full_cell  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

PAGE = 0


def beats_of(v):
    if not isinstance(v, dict):
        return None
    b = v.get("beats")
    return None if b is None else float(b)


def score(record_path):
    run = RO.load_run(record_path)
    T = Truth()
    read = []
    keys = []
    for k, g in run.glyphs.items():
        if g.page != PAGE or g.box_page is None:
            continue
        if not str(g.cls or "").startswith("notehead"):
            continue
        read.append((len(read), tuple(g.box_page), g.cls))
        keys.append(k)
    truth = [(h.idx, h.rect, h.cls) for h in T.heads]
    pairs, only_t, only_r = S.match_boxes(truth, read)
    by_idx = {h.idx: h for h in T.heads}
    rows = []
    for t_idx, (r_i, iou) in sorted(pairs.items()):
        th = by_idx[t_idx]
        if in_full_cell(T.full, th.rect) is None:
            continue
        d = T.derive(th)
        key = keys[r_i]
        row = {"key": key, "truth_id": th.id, "truth_status": d["status"], "truth_levels": d.get("levels"),
               "truth_written": d.get("written"), "truth_cls": th.cls, "rect": d["rect"]}
        v = run.standing(key, Q.DURATION, "ADJUDICATE")
        if v is None:
            row["judge"] = "none"
            rows.append(row)
            continue
        row["outcome"] = v["outcome"]
        row["reason"] = v.get("reason")
        det = v.get("detail") or {}
        row["why"] = det.get("beams_not_by_ink_why")
        row["beam_evidence"] = det.get("beam_evidence")
        if d["status"] != "ok" or d.get("written") is None:
            row["judge"] = "unjudged_" + d["status"]
            row["ours"] = beats_of(v.get("value")) if v["outcome"] == "decided" else \
                [beats_of(c.get("value")) for c in (v.get("candidates") or [])]
            rows.append(row)
            continue
        tw = float(d["written"])
        if v["outcome"] == "decided":
            b = beats_of(v.get("value"))
            row["ours"] = b
            row["judge"] = "right" if (b is not None and abs(b - tw) < 1e-6) else "wrong"
        elif v["outcome"] == "narrowed":
            cands = [beats_of(c.get("value")) for c in (v.get("candidates") or [])]
            row["ours"] = cands
            row["judge"] = "narrowed_in" if any(c is not None and abs(c - tw) < 1e-6 for c in cands) \
                else "narrowed_out"
        else:
            row["ours"] = None
            row["judge"] = "abstained"
        rows.append(row)
    return rows


def summary(rows, title):
    print(f"== {title}")
    judged = [r for r in rows if not r["judge"].startswith("unjudged")]
    print("   heads matched in fully labeled cells:", len(rows), "| judged:", len(judged),
          "| unjudged (no truth stem):", len(rows) - len(judged))
    for lab, sel in (("ALL judged", judged),
                     ("truth level 0 (a quarter or longer)", [r for r in judged if r["truth_levels"] == 0]),
                     ("truth level >= 1 (EIGHTH or shorter)", [r for r in judged if (r["truth_levels"] or 0) >= 1]),
                     ("truth level 1 (an eighth)", [r for r in judged if r["truth_levels"] == 1])):
        c = collections.Counter(r["judge"] for r in sel)
        print(f"   {lab:42s} n={len(sel):3d}  " + "  ".join(f"{k} {c.get(k, 0)}" for k in
                                                         ("right", "narrowed_in", "narrowed_out", "wrong", "abstained",
                                                          "none")))
    wr = [r for r in judged if r["judge"] in ("wrong", "narrowed_out")]
    if wr:
        print("   wrong / narrowed-out heads:", [(r["key"], r["truth_levels"], r["judge"]) for r in wr][:30])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--base", default=None, help="a previous --json: print the before -> after table")
    a = ap.parse_args()
    rows = score(a.record)
    summary(rows, Path(a.record).name)
    if a.json:
        Path(a.json).write_text(json.dumps(rows, separators=(",", ":"), default=str))
    if a.base:
        base = {r["key"]: r for r in json.load(open(a.base))}
        moves = collections.Counter()
        moved = []
        for r in rows:
            b = base.get(r["key"])
            if b is None:
                moves[("(new)", r["judge"])] += 1
                continue
            if b["judge"] != r["judge"] or b.get("ours") != r.get("ours"):
                moves[(b["judge"], r["judge"])] += 1
                moved.append((r["key"], b["judge"], b.get("ours"), r["judge"], r.get("ours"), r["truth_levels"]))
        print("\n== before -> after (judge changes):")
        for k, v in sorted(moves.items()):
            print(f"   {k[0]:14s} -> {k[1]:14s} {v}")
        for m in moved:
            print("   ", m)


if __name__ == "__main__":
    main()
