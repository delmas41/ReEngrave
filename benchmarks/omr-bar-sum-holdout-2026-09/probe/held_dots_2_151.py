"""ROADMAP 2.151 -- in the Brahms whole-movement record's HELD bars (a voice that does not sum to the bar), what the dots
in that bar's cell did (STAGED; the record's own verdicts, nothing re-decided). Streams the record with ijson (never
loads it); keeps only rows of the held cells.

Per held voice, by its deficit (quarters - want): the cell's `Q.AUG_DOT` glyphs and their live `Q.DOT_ROLE`, and the
cell's heads' live `Q.DURATION` (dots, outcome). Class:
  dot_role_not_augmentation  a dot glyph in the cell whose role is not DECIDED augmentation (abstained / staccato)
  dot_decided_not_joined     a DECIDED augmentation dot whose named head's live duration carries no dot
  dots_all_joined            every augmentation dot reached a duration
  no_dot_glyph               no dot box in the cell at all (a missed dot is a RECOGNITION loss, or not a dot problem)
usage: held_dots_2_151.py RECORD.json COVERAGE.json OUT.json"""
import collections, json, sys
import ijson

REC, COV, OUT = sys.argv[1:4]
held = json.load(open(COV))["bars_held_out_sum"]["held"]
cells = {}
for b in held:
    key = "glyph/%d/%d/%d/%d/" % (b["page"], b["system"], b["staff"], b["cell"])
    cells[key] = b
OBSQ = {"glyph_box", "aug_dot", "notehead_class", "rest", "dot_staff_position"}
VQ = {"dot_role", "duration", "notehead_is_not_a_notehead"}
SP = 33.0  # Brahms page px per staff space at 600 dpi


def cell_of(sub):
    p = sub.split("/")
    if len(p) < 6 or p[0] != "glyph":
        return None
    k = "/".join(p[:5]) + "/"
    return k if k in cells else None


obs = collections.defaultdict(dict)
verd = {}
sup = set()
with open(REC, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        if o["quantity"] not in OBSQ:
            continue
        if cell_of(o["subject"]) is None:
            continue
        obs[o["subject"]][o["quantity"]] = dict(value=o["value"], detail=o.get("detail"))
print("obs done", len(obs), flush=True)
with open(REC, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        if v.get("supersedes"):
            sup.add(v["supersedes"])
        if v["quantity"] not in VQ or cell_of(v["subject"]) is None:
            continue
        verd.setdefault((v["subject"], v["quantity"]), []).append(
            dict(id=v["id"], outcome=v["outcome"], value=v.get("value"), reason=v.get("reason"),
                 decider=v.get("decider"), detail=v.get("detail"),
                 candidates=[c.get("value") for c in (v.get("candidates") or [])]))
print("verdicts done", len(verd), flush=True)


def live(sub, q):
    vs = [v for v in verd.get((sub, q), []) if v["id"] not in sup]
    return vs[-1] if vs else None


by_cell = collections.defaultdict(list)
for s in obs:
    by_cell[cell_of(s)].append(s)
out, c = [], collections.Counter()
for key, b in cells.items():
    subs = by_cell.get(key, [])
    dots = [s for s in subs if "aug_dot" in obs[s]]
    def _refused(s):
        v = live(s, "notehead_is_not_a_notehead")
        return v is not None and v["outcome"] == "decided" and v["value"] is True
    allheads = [s for s in subs if "notehead_class" in obs[s] or "rest" in obs[s]]
    heads = [s for s in allheads if not _refused(s)]
    drows = []
    for s in dots:
        r = live(s, "dot_role")
        drows.append(dict(glyph=s, cls=(obs[s].get("glyph_box") or {}).get("value", [None])[0],
                          bbox=((obs[s].get("glyph_box") or {}).get("detail") or {}).get("bbox_page_px"),
                          role=r and (r["value"] if r["outcome"] == "decided" else r["outcome"] + ":" + str(r["reason"])),
                          head=r and (r.get("detail") or {}).get("head")))
    hrows = []
    for s in heads:
        v = live(s, "duration")
        val = v and v["value"]
        hrows.append(dict(glyph=s, bbox=((obs[s].get("glyph_box") or {}).get("detail") or {}).get("bbox_page_px"),
                          outcome=v and v["outcome"], reason=v and v["reason"],
                          dots=val.get("dots") if isinstance(val, dict) else None,
                          written=val.get("written") if isinstance(val, dict) else None,
                          cand_dots=sorted({(cv or {}).get("dots") for cv in (v["candidates"] if v else [])
                                            if isinstance(cv, dict)}, key=str)))
    hdots = {h["glyph"]: h["dots"] for h in hrows}
    kinds = set()
    for dr in drows:
        if dr["role"] != "augmentation":
            if dr["role"] in ("staccato", "staccatissimo"):
                kinds.add("dot_decided_staccato")
            else:
                kinds.add("dot_role_not_augmentation")
        elif dr["head"] and dr["head"] in hdots and not hdots[dr["head"]]:
            kinds.add("dot_decided_not_joined")
        else:
            kinds.add("dots_joined")
    # a dot-sized notehead box the gate refused, in a kept head's dot place
    for s in allheads:
        if not _refused(s):
            continue
        bx = ((obs[s].get("glyph_box") or {}).get("detail") or {}).get("bbox_page_px")
        if not bx or (bx[2] - bx[0]) / SP > 0.6 or (bx[3] - bx[1]) / SP > 0.6:
            continue
        cy = (bx[1] + bx[3]) / 2
        for h in hrows:
            hb = h["bbox"]
            if not hb or h["dots"]:
                continue
            gap, dy = (bx[0] - hb[2]) / SP, (cy - (hb[1] + hb[3]) / 2) / SP
            if -0.1 <= gap <= 1.5 and abs(dy) <= 0.8:
                kinds.add("dot_boxed_as_a_refused_head")
                drows.append(dict(glyph=s, as_head=True, head=h["glyph"]))
                break
    if not [d for d in drows if not d.get("as_head")] and "dot_boxed_as_a_refused_head" not in kinds:
        kinds.add("no_dot_glyph")
    for q in b["quarters"]:
        deficit = round(q - b["want_quarters"], 3)
        for k in kinds:
            c[(deficit, k)] += 1
    out.append(dict(bar=b, dots=drows, heads=hrows, kinds=sorted(kinds)))
json.dump(out, open(OUT, "w"), indent=0, default=str)
tot = collections.Counter()
for b in held:
    for q in b["quarters"]:
        tot[round(q - b["want_quarters"], 3)] += 1
for deficit in (-0.5, -1.0, -1.5, 0.5, 1.0):
    print("deficit %+.2f voices %d" % (deficit, tot[deficit]),
          {k: n for (d_, k), n in sorted(c.items()) if d_ == deficit})
