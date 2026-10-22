"""ROADMAP 2.12f -- choose the blind tiles. Seeded, one tile per page where it
can be, shuffled so the order says nothing about the category.

    python3 benchmarks/omr-shape-role-2026-09/select_artic_tiles.py \
        --brahms-arm <arm.json> --brahms-cmp <cmp.json> --brahms-probe <probe.json> \
        --litolff-arm <arm.json> --out selection.json [--seed 20261009]

CATEGORIES (the manifest records which a tile is; Sean never sees it):

  relabel      a CHANGED decision: base `no_notehead` -> arm
               `suffix_contradicts_geometry` (class and nearest in-cell head
               disagree). The hypothesis under test: the class is right and the
               mark's head is in the NEIGHBOUR staff.
  cross_staff  UNCHANGED `no_notehead` whose declared-side head stands in
               another staff, within reach, in page pixels -- the population the
               follow-up (a cross-staff owner) would recover.
  far_pick     UNCHANGED decided owner 2.5+ head heights from its mark while a
               nearer head on the same declared side stands in the same x
               window -- the x-only pick under test.
  between      decided with a head on the OTHER side also in reach (the mark
               stands between two heads; the class chose).
  control      decided, class and measurement agree, head adjacent.
  litolff      the Litolff abstentions (a second plate).
"""
from __future__ import annotations

import argparse
import json
import random


def _doc_pdf(path_json):
    return json.load(open(path_json))["pdf"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brahms-arm", required=True)
    ap.add_argument("--brahms-cmp", required=True)
    ap.add_argument("--brahms-probe", required=True)
    ap.add_argument("--litolff-arm", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261009)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)

    arm = json.load(open(a.brahms_arm))
    cmp_ = json.load(open(a.brahms_cmp))
    probe = {r["subject"]: r for r in json.load(open(a.brahms_probe))["rows"]}
    byarm = {r["subject"]: r for r in arm["articulations"]}
    pdf_b = arm["pdf"]

    def pick(pool, n, used_pages):
        pool = list(pool)
        rng.shuffle(pool)
        out = []
        for r in pool:
            if len(out) == n:
                break
            if r["page"] in used_pages:
                continue
            used_pages.add(r["page"])
            out.append(r)
        return out

    tiles = []
    used = set()

    # relabel: the CHANGED decisions
    rel = [byarm[c["subject"]] for c in cmp_["changed"]
           if byarm[c["subject"]].get("mark_bbox_page")]
    for r in pick(rel, 5, used):
        d = r["owner"]["detail"]
        tiles.append(dict(
            category="relabel", doc="brahms", pdf=pdf_b, page=r["page"],
            subject=r["subject"], mark_bbox_page=r["mark_bbox_page"],
            read_before="abstained: no_notehead (class %s names %s; no head on "
                        "that side in this cell)" % (r["class"], d["suffix_side"]),
            read_after="abstained: suffix_contradicts_geometry (class names %s; "
                       "nearest in-cell head %s, measured %s the head, gap %.2f "
                       "heads; head %s)" % (d["suffix_side"], d["head"],
                                            d["measured_side"],
                                            d["gap_head_heights"], d["head"])))

    # cross_staff: unchanged no_notehead, declared-side head in another staff
    cs = []
    for s, p in probe.items():
        r = byarm.get(s)
        if (r and r["owner"] and r["owner"]["reason"] == "no_notehead"
                and p.get("declared_side_head_elsewhere")
                and p.get("mark_bbox_page")):
            cs.append({**r, "elsewhere": p["declared_side_head_elsewhere"]})
    for r in pick(cs, 1, used):
        e = r["elsewhere"][0]
        tiles.append(dict(
            category="cross_staff", doc="brahms", pdf=pdf_b, page=r["page"],
            subject=r["subject"], mark_bbox_page=r["mark_bbox_page"],
            read_before="abstained: no_notehead (no head in this cell)",
            read_after="abstained: no_notehead -- UNCHANGED; a head on the "
                       "declared side stands in another staff (%s, gap %.2f "
                       "heads)" % (e["head"], e["gap_heads"])))

    # far_pick: decided far while a nearer same-side head exists
    fp = []
    for r in arm["articulations"]:
        o = r["owner"]
        if not o or o["outcome"] != "decided" or not r.get("mark_bbox_page"):
            continue
        d = o["detail"]
        if (d["gap_head_heights"] > 2.5
                and d["nearest_declared_side_gap_head_heights"] + 0.25
                < d["gap_head_heights"]
                and d["nearest_declared_side_head"] != o["value"]):
            fp.append(r)
    for r in pick(fp, 3, used):
        d = r["owner"]["detail"]
        tiles.append(dict(
            category="far_pick", doc="brahms", pdf=pdf_b, page=r["page"],
            subject=r["subject"], mark_bbox_page=r["mark_bbox_page"],
            read_before="decided: owner %s (gap %.2f heads); a nearer head on "
                        "the same side is %s (gap %.2f heads)"
                        % (r["owner"]["value"], d["gap_head_heights"],
                           d["nearest_declared_side_head"],
                           d["nearest_declared_side_gap_head_heights"]),
            read_after="UNCHANGED (this lane records the nearer head, does not "
                       "move the pick)"))

    # between: a head on the other side also in reach
    bt = [r for r in arm["articulations"]
          if r["owner"] and r["owner"]["outcome"] == "decided"
          and r["owner"]["detail"]["other_side_head_in_reach"]
          and r.get("mark_bbox_page")]
    for r in pick(bt, 1, used):
        d = r["owner"]["detail"]
        tiles.append(dict(
            category="between", doc="brahms", pdf=pdf_b, page=r["page"],
            subject=r["subject"], mark_bbox_page=r["mark_bbox_page"],
            read_before="decided: owner %s by the class (%s); another head on "
                        "the other side is also within reach"
                        % (r["owner"]["value"], d["suffix_side"]),
            read_after="UNCHANGED (recorded: other_side_head_in_reach)"))

    # control: decided, adjacent, agrees
    ct = [r for r in arm["articulations"]
          if r["owner"] and r["owner"]["outcome"] == "decided"
          and r["owner"]["detail"]["gap_head_heights"] <= 0.6
          and r["owner"]["detail"]["nearest_declared_side_head"] == r["owner"]["value"]
          and not r["owner"]["detail"]["other_side_head_in_reach"]
          and r.get("mark_bbox_page")]
    for r in pick(ct, 1, used):
        d = r["owner"]["detail"]
        tiles.append(dict(
            category="control", doc="brahms", pdf=pdf_b, page=r["page"],
            subject=r["subject"], mark_bbox_page=r["mark_bbox_page"],
            read_before="decided: owner %s (%s, gap %.2f heads)"
                        % (r["owner"]["value"], d["suffix_side"],
                           d["gap_head_heights"]),
            read_after="UNCHANGED"))

    # litolff: the abstentions
    la = json.load(open(a.litolff_arm))
    pdf_l = la["pdf"]
    lab = [r for r in la["articulations"]
           if r["owner"] and r["owner"]["outcome"] == "abstained"
           and r.get("mark_bbox_page")]
    for r in lab[:1]:
        tiles.append(dict(
            category="litolff", doc="litolff", pdf=pdf_l, page=r["page"],
            subject=r["subject"], mark_bbox_page=r["mark_bbox_page"],
            read_before="abstained: %s" % r["owner"]["reason"],
            read_after="UNCHANGED (%s)" % r["owner"]["reason"]))

    rng.shuffle(tiles)
    for i, t in enumerate(tiles, 1):
        t["n"] = i
    json.dump(tiles, open(a.out, "w"), indent=1)
    for t in tiles:
        print(t["n"], t["category"], t["doc"], t["subject"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
