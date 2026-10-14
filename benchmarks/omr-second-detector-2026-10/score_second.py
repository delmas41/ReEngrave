"""ROADMAP 2.114 scorer: the second hollow detector, flag OFF vs ON, against Sean's hand truth. Reuses 2.110's scorers UNCHANGED
(`score_ab.score_litolff` / `score_brahms`, `score_truth.py`) and adds (a) three VIEWS of "what the record calls hollow" and (b) a table of
every disagreement and how it was settled.

  python3 benchmarks/omr-second-detector-2026-10/score_second.py off=lit.json:bra.json on=lit.json:bra.json [--out score.json]

VIEWS (the same function of the verdicts on BOTH arms, so OFF's own landed 2.70 / 2.88 / 2.23 hollow readings count in OFF too):
  gather  a glyph is hollow if its GLYPH class is half/whole (2.110's view: production's boxes, plus the second detector's own boxes when ON)
  read    + a production-black glyph whose ADJUDICATE duration verdict is DECIDED with head_fill half/whole   (READ: written plain)
  guess   + a glyph whose duration verdict is NARROWED with a half/whole candidate                           (GUESSED: blue, both candidates)
LITOLFF = Sean's 104 TEST cells (and the 95 CLEAN cells = those minus the 9 `leak_check.py` found in the second detector's training mix).
BRAHMS  = Sean's pdf 0 hand truth.
CONTROLS (rule 7, exit 1 if one does not behave): truth matched against itself finds all; shifted 3 head widths finds ~none;
  a view that calls EVERY black glyph hollow must wreck precision / filled-called-hollow (the metric can see an over-call).
"""
from __future__ import annotations

import collections
import copy
import dataclasses
import importlib.util
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from tools.omr.hand_truth import score as SC  # noqa: E402
from tools.omr.hand_truth import store as ST  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402

_spec = importlib.util.spec_from_file_location("score_ab", "benchmarks/omr-labeling-hollow4-2026-10/score_ab.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

HERE = Path(__file__).parent
HOLLOW_CLS = "noteheadHalfInSpace"
BLACKISH = "noteheadBlack"
FILLS = ("half", "whole")


def leaked_cells():
    d = json.loads((HERE / "leak_check.json").read_text())
    out = set()
    for name in d["litolff"]["key_cells"]:
        s, st, m = name.split("/")[1].replace("s", "", 1).replace("st", "").replace("m", "").split("-")
        out.add((int(s), int(st), int(m)))
    return out


def fill_state(run, g):
    """'read' | 'guessed' | None  -- what ADJUDICATE's duration verdict says about this glyph's fill."""
    v = run.standing(g.key, "duration", "ADJUDICATE")
    if v is None:
        return None
    if v["outcome"] == "decided" and ((v.get("value") or {}).get("head_fill") in FILLS):
        return "read"
    if v["outcome"] == "narrowed" and any(((c.get("value") or {}).get("head_fill") in FILLS) for c in (v.get("candidates") or [])):
        return "guessed"
    return None


def view_run(run, view, everything_black=False):
    r = copy.copy(run)
    gl = {}
    for k, g in run.glyphs.items():
        c = g.cls or ""
        if c.startswith(BLACKISH):
            st = fill_state(run, g)
            if everything_black or (view == "read" and st == "read") or (view == "guess" and st in ("read", "guessed")):
                g = dataclasses.replace(g, cls=HOLLOW_CLS)
        gl[k] = g
    r.glyphs = gl
    return r


def second_rows(run):
    """glyph key -> its Q.SECOND_HOLLOW observation, for every glyph the second detector touched."""
    out = {}
    for o in run.observations:
        if o["quantity"] == "second_hollow":
            out[o["subject"]] = o
    return out


def settlement(run, key, row):
    """(relation, settled-as, reason) for one touched glyph."""
    rel = (row.get("detail") or {}).get("relation")
    v = run.standing(key, "duration", "ADJUDICATE")
    if v is None:
        return rel, "no duration verdict", None
    reason, outcome = v.get("reason"), v["outcome"]
    sh = (v.get("detail") or {}).get("second_hollow") or {}
    if rel == "agrees":
        return rel, "agrees (production already hollow)", reason
    if rel == "disagrees":
        if reason == "second_hollow_confirmed":
            return rel, "READ hollow (new rule)", reason
        if reason == "second_hollow_unclear":
            return rel, "NARROWED black/hollow (new rule)", reason
        if sh.get("settled") == "black_stands":
            return rel, "black stands (ink filled / marks)", reason
        return rel, f"settled before the new rule: {outcome} {reason}", reason
    if rel == "second_only":
        if reason == "second_only_hollow":
            return rel, "NARROWED (second-only head)", reason
        if reason == "second_hollow_refuted_by_ink":
            return rel, "refused: ink reads filled", reason
        if reason == "second_hollow_contradicted_by_marks":
            return rel, "refused: beam/flag on its stem", reason
        return rel, f"other: {outcome} {reason}", reason
    return rel, "?", reason


def truth_class_litolff(glyph, truth, cellset):
    key = (glyph.system, glyph.staff, glyph.cell)
    if glyph.page != 1 or key not in cellset or glyph.box_canon is None:
        return "outside the 104 labelled cells"
    return "truth hollow head" if any(S.same(t, glyph.box_canon) for t in truth.get(key, [])) else "not a truth hollow head"


def truth_class_brahms(glyph, page):
    if glyph.box_page is None:
        return "no page box"
    r = tuple(glyph.box_page)
    for b in page.boxes:
        if S.same(b.rect, r):
            if b.cls.startswith(S.HOLLOW):
                return "truth hollow head"
            if b.cls.startswith("noteheadBlack"):
                return "truth BLACK head"
            return f"truth {b.cls}"
    return "no truth box"


def main():
    args = [a for a in sys.argv[1:] if "=" in a and not a.startswith("--")]
    arms = {a.split("=", 1)[0]: a.split("=", 1)[1].split(":") for a in args}
    truth, n_truth, cellset = S.litolff_truth()
    leak = leaked_cells() & cellset
    clean = cellset - leak
    page = ST.load(Path("data/hand-truth/pages/imslp317803/0.json"))
    wmed = statistics.median([t[2] - t[0] for ts in truth.values() for t in ts])
    ok = True
    # ---------------- controls ----------------
    c1 = sum(1 for ts in truth.values() for t in ts if S.same(t, t))
    c2 = sum(1 for ts in truth.values() for t in ts if S.same(t, (t[0] + 3 * wmed, t[1], t[2] + 3 * wmed, t[3])))
    first = RO.load_run(next(iter(arms.values()))[0])
    all_black = S.score_litolff(view_run(first, "gather", everything_black=True), truth, cellset)
    plain = S.score_litolff(first, truth, cellset)
    print(f"controls: truth self-match {c1}/{n_truth}; shifted 3 head widths {c2}/{n_truth}; "
          f"'every black glyph is hollow' view: precision {all_black['precision']:.2f} (plain {plain['precision']:.2f}) -> must collapse")
    ok &= c1 == n_truth and c2 <= max(1, n_truth // 10) and all_black["precision"] < 0.5 * plain["precision"]
    if not ok:
        print("CONTROL FAILED -- numbers withheld")
        return 1
    print(f"Litolff TEST cells {len(cellset)} ({n_truth} truth heads); leaked cells {len(leak)}; clean {len(clean)} cells, "
          f"{sum(len(v) for k, v in truth.items() if k in clean)} heads")
    res = {"leaked": sorted(leak), "arms": {}}
    for lab, (lit_p, bra_p) in arms.items():
        lit, bra = RO.load_run(lit_p), RO.load_run(bra_p)
        row = {}
        for view in ("gather", "read", "guess"):
            lv, bv = view_run(lit, view), view_run(bra, view)
            for tag, cs in (("all104", cellset), ("clean95", clean)):
                r = S.score_litolff(lv, {k: x for k, x in truth.items() if k in cs}, cs)
                r.pop("extra_boxes", None)
                row[f"litolff_{tag}_{view}"] = r
                print(f"[{lab} litolff {tag} {view:6s}] recall {r['found']}/{r['truth_heads']}={100*r['recall']:.1f}%  "
                      f"precision {r['hollow_boxes_on_a_truth_head']}/{r['hollow_boxes']}={100*r['precision']:.1f}%")
            b = S.score_brahms(bv, page)
            row[f"brahms_{view}"] = b
            print(f"[{lab} brahms {view:6s}] hollow found {b['found_hollow']}/{b['truth_hollow']}  boxes {b['hollow_boxes']} extra {b['extra_hollow_boxes']} "
                  f"on {b['extra_sits_on']}  FILLED heads called hollow {b['filled_heads_called_hollow']}")
        # disagreement table
        dis = []
        for tag, run in (("litolff", lit), ("brahms", bra)):
            for key, o in second_rows(run).items():
                g = run.glyphs.get(key)
                if g is None:
                    continue
                rel, how, reason = settlement(run, key, o)
                tc = truth_class_litolff(g, truth, cellset) if tag == "litolff" else truth_class_brahms(g, page)
                dis.append({"doc": tag, "key": key, "relation": rel, "settled": how, "reason": reason, "truth": tc,
                            "second_class": (o.get("value")), "second_score": (o.get("detail") or {}).get("second_score"),
                            "production_class": (o.get("detail") or {}).get("production_class")})
        row["touched"] = dis
        cnt = collections.Counter((d["doc"], d["relation"], d["settled"]) for d in dis)
        row["settlement_counts"] = {" | ".join(k): v for k, v in sorted(cnt.items())}
        tcnt = collections.Counter((d["doc"], d["relation"], d["settled"], d["truth"]) for d in dis if d["relation"] != "agrees")
        row["settlement_by_truth"] = {" | ".join(k): v for k, v in sorted(tcnt.items())}
        res["arms"][lab] = row
        if dis:
            print(f"[{lab}] touched glyphs {len(dis)}")
            for k, v in sorted(cnt.items()):
                print("   ", " | ".join(k), v)
            print("   by truth:")
            for k, v in sorted(tcnt.items()):
                print("   ", " | ".join(k), v)
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
