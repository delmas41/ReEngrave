"""ROADMAP 2.194 -- how often two readers of the SAME ink disagree, counted on the frozen-sample slices (20261020-night).

Pairs measured (each is one stroke or one head read by two independent code paths):
  beams    per head's duration verdict: `cv_beams` (CV beam strokes joined to the stem) vs `yolo_beams` (detector beam boxes at
           the stem); and `levels_certain` vs `levels_possible` (how often the reading is left open)
  head fill per head: detector class (noteheadBlack* / noteheadHalf* / noteheadWhole*) vs `notehead_ink.interior_white`
           (cv_notehead_ink) as the duration verdict read it (`head_is_open`, `head_fill_first`)
  stems    per head: the stem finder (`head_stem` abstention `no_stem` = no Q.STEM row touches the head) vs `head_stem_reach`
           (cv_head_stem_reach: a vertical run leaving the head box up or down, in staff spaces) and `notehead_ink.stem_bridge`
  ledgers  per head: detector-based `glyph_ladder.found` vs `ledger_rung_ink` (cv_ledger) centre states for the same head
  arcs     detector `arc_box` rows vs `system_arc` pieces (cv_system_arc): arc boxes no system arc traced
Writes results/disagreements.json with counts and the subject keys of every disagreement (for crops). Read-only.
"""
from __future__ import annotations
import collections, json, os, re

ROOT = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261020-night"
OUT = os.path.join(os.path.dirname(__file__), "results")

def load(plate):
    obs = collections.defaultdict(list)          # (subject, quantity) -> rows
    ids = {}
    with open(os.path.join(ROOT, plate, "observations.jsonl"), "rb") as fh:
        for line in fh:
            o = json.loads(line); obs[(o["subject"], o["quantity"])].append(o); ids[o["id"]] = o
    verd = collections.defaultdict(list)
    with open(os.path.join(ROOT, plate, "verdicts.jsonl"), "rb") as fh:
        for line in fh:
            o = json.loads(line); o.pop("basis", None); o.pop("considered", None); verd[(o["subject"], o["quantity"])].append(o)
    abst = collections.defaultdict(list)
    with open(os.path.join(ROOT, plate, "abstentions.jsonl"), "rb") as fh:
        for line in fh:
            o = json.loads(line); abst[(o["subject"], o["quantity"])].append(o)
    return obs, ids, verd, abst

def cls_fill(name):
    n = str(name)
    if n.startswith("noteheadBlack"): return "black"
    if n.startswith("noteheadHalf"): return "half"
    if n.startswith("noteheadWhole"): return "whole"
    return None

def main():
    out = {}
    for plate in ("litolff", "brahms"):
        obs, ids, verd, abst = load(plate)
        R = {"beams": collections.Counter(), "fill": collections.Counter(), "stems": collections.Counter(),
             "ledgers": collections.Counter(), "arcs": collections.Counter()}
        cases = collections.defaultdict(list)
        heads = [s for (s, q) in obs if q == "notehead_class"]
        for s in heads:
            cls = cls_fill(obs[(s, "notehead_class")][0]["value"])
            # --- beams: cv vs yolo at this head (duration verdict detail)
            for v in verd.get((s, "duration"), []):
                d = v.get("detail") or {}
                if "cv_beams" in d and "yolo_beams" in d:
                    cv, yo = d.get("cv_beams"), d.get("yolo_beams")
                    ncv = len(cv) if isinstance(cv, (list, dict)) else (cv if isinstance(cv, int) else None)
                    nyo = len(yo) if isinstance(yo, (list, dict)) else (yo if isinstance(yo, int) else None)
                    if ncv is None or nyo is None: R["beams"]["unparsed"] += 1; continue
                    R["beams"]["heads_with_both_readers"] += 1
                    if (ncv > 0) != (nyo > 0):
                        R["beams"]["presence_disagrees"] += 1; cases["beams_presence"].append((s, ncv, nyo, v.get("reason")))
                    elif ncv != nyo:
                        R["beams"]["count_disagrees"] += 1; cases["beams_count"].append((s, ncv, nyo, v.get("reason")))
                    else: R["beams"]["agree"] += 1
                    lc, lp = d.get("levels_certain"), d.get("levels_possible")
                    if lc is not None and lp is not None and lc != lp: R["beams"]["levels_left_open"] += 1
                    R["beams"][f"reason:{v.get('reason')}"] += 1
                    # --- head fill: detector class vs ink
                    ho = d.get("head_is_open"); hf = d.get("head_fill_first")
                    if cls in ("black", "half") and ho is not None:
                        R["fill"]["heads_with_both_readers"] += 1
                        ink_open = bool(ho)
                        if (cls == "half") != ink_open:
                            R["fill"]["disagree"] += 1; R["fill"][f"disagree:{cls}_vs_ink_{'open' if ink_open else 'filled'}"] += 1
                            cases["fill"].append((s, cls, ink_open, hf, v.get("reason")))
                        else: R["fill"]["agree"] += 1
                    if hf is not None and ho is not None and isinstance(hf, dict):
                        hfo = hf.get("open") if "open" in hf else hf.get("is_open")
                        if hfo is not None and bool(hfo) != bool(ho):
                            R["fill"]["slit_vs_window_disagree"] += 1; cases["fill_slit_vs_window"].append((s, hfo, ho))
            # --- stems: finder vs reach reader vs bridge
            no_stem = any(a.get("reason") == "no_stem" for a in abst.get((s, "head_stem"), []))
            reach = obs.get((s, "head_stem_reach"), [])
            ni = obs.get((s, "notehead_ink"), [])
            bridge = None
            if ni:
                sb = (ni[0].get("detail") or {}).get("stem_bridge")
                if isinstance(sb, dict): bridge = sb.get("side") or sb.get("bridged") or sb.get("stem")
                elif sb is not None: bridge = sb
            if reach:
                d = reach[0].get("detail") or {}
                up, dn = d.get("up_ext"), d.get("down_ext")
                try: ext = max(float(up or 0), float(dn or 0))
                except Exception: ext = 0.0
                R["stems"]["heads_with_reach_row"] += 1
                if no_stem and ext >= 2.0:
                    R["stems"]["finder_none_reach_sees_>=2sp"] += 1; cases["stems_finder_none_reach_sees"].append((s, up, dn))
                elif no_stem and ext < 2.0: R["stems"]["finder_none_reach_none"] += 1
                elif not no_stem and ext < 1.0:
                    R["stems"]["finder_stem_reach_none"] += 1; cases["stems_finder_stem_reach_none"].append((s, up, dn))
                else: R["stems"]["agree"] += 1
            if bridge is not None:
                R["stems"]["heads_with_bridge_row"] += 1
                bridged = bool(bridge) and bridge not in ("none", "no", False)
                if bridged and no_stem:
                    R["stems"]["bridge_yes_finder_none"] += 1; cases["stems_bridge_yes_finder_none"].append((s, bridge))
            # --- ledgers: detector ladder vs cv rungs
            lad = obs.get((s, "glyph_ladder"), [])
            rungs = obs.get((s, "ledger_rung_ink"), [])
            if lad and rungs:
                found = (lad[0].get("detail") or {}).get("found")
                nfound = len(found) if isinstance(found, (list, dict)) else (found if isinstance(found, int) else None)
                states = [str(r.get("value")) for r in rungs]
                n_present = sum(1 for st in states if st in ("present", "True", "rung", "ink", "1"))
                R["ledgers"]["heads_with_both_readers"] += 1
                if nfound is not None:
                    if (nfound > 0) != (n_present > 0):
                        R["ledgers"]["presence_disagrees"] += 1; cases["ledgers"].append((s, nfound, states[:6]))
                    else: R["ledgers"]["agree_on_presence"] += 1
        # --- arcs: detector arc boxes vs system arcs
        arc_boxes = [s for (s, q) in obs if q == "arc_box"]
        covered = set()
        for (s, q), rows in obs.items():
            if q == "system_arc":
                for r in rows:
                    for p in ((r.get("detail") or {}).get("pieces") or []):
                        covered.add(str(p) if not isinstance(p, dict) else str(p.get("glyph") or p.get("subject") or p.get("id")))
        R["arcs"]["detector_arc_boxes"] = len(arc_boxes)
        R["arcs"]["in_a_system_arc"] = sum(1 for s in arc_boxes if s in covered or any(c in s for c in covered if c))
        R["arcs"]["system_arcs"] = sum(len(v) for (s, q), v in obs.items() if q == "system_arc")
        for q in ("arc_kind",):
            for (s, qq), vs in verd.items():
                if qq == q:
                    for v in vs: R["arcs"][f"arc_kind:{v.get('outcome')}:{v.get('reason')}"] += 1
        # the readers' own disagreement words on abstentions
        words = collections.Counter()
        for (s, q), rows in abst.items():
            for a in rows:
                r = a.get("reason")
                if r and re.search(r"disagree|ambiguous|contradict|uncertain|cannot_tell|unread", str(r)): words[f"{q}:{r}"] += 1
        print(f"== {plate}")
        for k, c in R.items(): print(f"  {k}: {dict(c.most_common(14))}")
        print("  abstention words of disagreement:", dict(words.most_common(20)))
        out[plate] = {"counts": {k: dict(c) for k, c in R.items()}, "disagreement_words": dict(words),
                      "cases": {k: v[:400] for k, v in cases.items()}}
    json.dump(out, open(os.path.join(OUT, "disagreements.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
