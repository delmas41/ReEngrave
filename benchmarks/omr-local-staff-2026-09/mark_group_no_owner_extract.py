"""ROADMAP 2.58c -- read-only extraction for the mark-group-no-owner census and tiles.

One `record_io.load_record` of a 10-07 day record -> a small JSON:

  * the census of every notehead mark seen 2+ times (members not refused as a
    note) by WHY it has or lacks an owner, counted off the record's saved
    verdicts under the project's own measure (`day_1007_report.marks`: the
    decided owner, or the FILING staff where no contest produced a verdict);
  * for the seeded tile groups, everything a tile needs: members (box, class,
    confidence, owner verdict, refused or not), every staff of the system
    (five line ys, instrument verdict, margin label).

  python3 benchmarks/omr-local-staff-2026-09/mark_group_no_owner_extract.py \
      <record.json> <litolff|brahms> <out.json>

Seeds are fixed (SEED = 20261008). No GATHER row is written; no tree state is
read except the record.
"""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.omr.staged.record_io import load_record  # noqa: E402

SEED = 20261008
#: the tile groups, by cause (chosen from the census, listed in FINDINGS)
WANT = {
    "litolff": {
        "none_far_no_rungs": ["mg/13/1/36", "mg/4/1/181"],
        "ledger_over_distance": ["mg/14/0/46", "mg/4/1/178"],
        "conflict_kept": ["mg/6/1/374"],
        "uncontested_one_staff": ["RANDOM"],
    },
    "brahms": {
        "none_far_no_rungs": ["mg/2/1/56"],
        "none_tied": ["mg/21/0/223"],
        "conflict_kept": ["mg/18/1/599", "mg/5/1/35"],
    },
}


def main(path, tag, out):
    rec = load_record(path)["record"]
    groups, fam = defaultdict(list), {}
    obs_of = defaultdict(dict)
    staff_lines, margin, gbox = {}, defaultdict(list), {}
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "mark_group":
            groups[o["value"]].append(o["subject"])
            fam[o["value"]] = (o.get("detail") or {}).get("family")
        elif q == "glyph_box":
            gbox[o["subject"]] = (o["value"][0], (o.get("detail") or {}).get("bbox_page_px"), o.get("score"))
        elif q == "staff_lines":
            staff_lines.setdefault(o["subject"], o["value"])
        elif q == "margin_label":
            margin[o["subject"]].append(o["value"])
    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    cur = {}
    allv = defaultdict(list)
    for v in rec["verdicts"]:
        if v["quantity"] in ("glyph_owner", "notehead_is_not_a_notehead", "instrument"):
            allv[(v["quantity"], v["subject"])].append(v)
            if v["id"] not in sup:
                cur[(v["quantity"], v["subject"])] = v

    def refused(s):
        v = cur.get(("notehead_is_not_a_notehead", s))
        return bool(v and v["outcome"] == "decided" and v["value"] is True)

    def eff(s):
        o = cur.get(("glyph_owner", s))
        if o is None:
            return "staff/" + "/".join(s.split("/")[1:4])
        return o["value"] if o["outcome"] == "decided" else None

    # ---- the census: why does a notehead group lack (or hold) one owner? ---
    census = Counter()
    pools = defaultdict(list)
    for g, m in groups.items():
        if fam[g] != "notehead":
            continue
        kept = [s for s in m if not refused(s)]
        if len(kept) < 2:
            continue
        census["marks seen 2+ times"] += 1
        decided_kept = [cur.get(("glyph_owner", s)) for s in kept
                        if cur.get(("glyph_owner", s)) and cur[("glyph_owner", s)]["outcome"] == "decided"]
        owners = {eff(s) for s in kept} - {None}
        if not decided_kept:
            ctr = [cur.get(("glyph_owner", s)) for s in kept]
            if all(c is None for c in ctr):
                homes = {"/".join(s.split("/")[1:4]) for s in kept}
                key = "no decided verdict: never contested, ONE filing staff" if len(homes) == 1 \
                    else "no decided verdict: never contested, SPLIT filing staves"
                pools["uncontested_one_staff" if len(homes) == 1 else "uncontested_split"].append(g)
            else:
                key = "no decided verdict: a contested copy abstained (" + ",".join(
                    sorted({c["reason"] for c in ctr if c})) + ")"
                pools["none"].append(g)
            census[key] += 1
        if len(owners) == 1:
            census["project measure: one owner"] += 1
        elif len(owners) > 1:
            census["project measure: two or more owners"] += 1
            pools["conflict"].append(g)
        else:
            census["project measure: no staff owns it"] += 1
    census["TOTAL no decided verdict on any member"] = sum(
        n for k, n in census.items() if k.startswith("no decided verdict"))

    # ---- the tile groups ----------------------------------------------------
    rng = random.Random(SEED)
    chosen = {}
    for cause, ids in WANT[tag].items():
        for gid in ids:
            if gid == "RANDOM":
                pool = sorted(pools["uncontested_one_staff"])
                # a mark whose copies were cut from different CELLS of one staff, so the question is not trivial
                gid = rng.choice(pool)
            elif gid.startswith("glyph/"):
                gid = next(g for g, m in groups.items() if gid in m)
            chosen[gid] = cause
    tiles = {}
    for gid, cause in chosen.items():
        m = groups[gid]
        page, sysi = m[0].split("/")[1:3]
        members = []
        for s in m:
            cls, bb, sc = gbox.get(s, (None, None, None))
            members.append(dict(subject=s, cls=cls, bbox=bb, conf=sc, refused=refused(s),
                                owner=[(v["decider"], v["outcome"], v["value"], v["reason"], v["id"] in sup)
                                       for v in allv.get(("glyph_owner", s), [])]))
        staves = {}
        for k, ys in staff_lines.items():
            p = k.split("/")
            if len(p) == 4 and p[1] == page and p[2] == sysi:
                iv = cur.get(("instrument", k))
                staves[k] = dict(lines=ys, instrument=(iv["value"] if iv and iv["outcome"] == "decided" else None),
                                 margin=margin.get(k, []))
        tiles[gid] = dict(cause=cause, page=int(page), system=int(sysi), members=members, staves=staves)
    json.dump(dict(tag=tag, census=dict(census), pools={k: len(v) for k, v in pools.items()}, tiles=tiles),
              open(out, "w"), indent=1, default=str)
    for k, n in sorted(census.items()):
        print(f"{n:6d}  {k}")
    print("pools", {k: len(v) for k, v in pools.items()}, "tiles", {g: c for g, c in chosen.items()})


if __name__ == "__main__":
    main(*sys.argv[1:4])
