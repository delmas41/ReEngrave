"""ROADMAP 2.305, MEASUREMENT ONLY (no pipeline code): sizing Sean's proposed end rule (DECISIONS 2026-11-13) --
"if there are any notes in a chord at the same point where an arc ends then that is where it should end"; the anchor is the x place on the staff the arc sits over.

    python3 end_columns_2305.py PLATE REPLAYWORK GATHERWORK [--sean]

REPLAYWORK = a lane_report replay `work/` with both arc flags ON (PLATE.on.extra.json = the page pass's entries, PLATE.on.musicxml = the written file);
GATHERWORK = the saved gather (PLATE.on.gathered.record.json: page-ink runs, notehead boxes, `Q.MARK_GROUP`, `Q.NOTEHEAD_STAFF_POSITION`).

Per page-pass run that abstains, per END:
  bound       the end names a head today (only the KIND was refused, or the other end failed)
  edge        the end is at a system's edge (cross-system; class (d))
  unbound     the end names no head; grouped by the binder's reason
For every end that is not bound, the COLUMNS at its x on the run's home staff (the staff the pass bound on): notehead boxes, twins of one page head (2.290 `Q.MARK_GROUP`)
counted once, grouped into columns (centres within half a head width); a column is a candidate when the end's x lies within ONE head width of its box extent.
  (a) exactly one column   (b) two or more   (c) none   (d) system edge
(c)'s "head-shaped ink with no box": the 2.290 page-head census rows (`Q.PAGE_HEAD`, `OMR_PAGE_HEADS`) are not in these gathers -- not determinable here.

Q3: runs whose two ends are each (a) or bound: the arc that would be written, compared BY PLACE with the written file's arcs on that staff (an arc whose two notes are in
those two columns = same pair; one that shares one column = a different pair; none = not written at all).
Q5 (kind): the head in each column nearest the run's tip height; same local position (`Q.NOTEHEAD_STAFF_POSITION.value`) within `SAME_POSITION_SPACES` (0.25 sp) -> tie
candidate; apart by at least `BIND_DIFFERENT_POSITION_SPACES` (0.435 sp) -> different; between -> inside the page-facts gap. The tip's height must stand within one space
of that head's centre for the column's head to count as the tip's (else "tip height does not agree").
--sean (Brahms only): Sean's 98 page-pass arcs on p0 (`arcs_combined.key_sean`): of those NOT right in the file, how many have both ends at an (a) column or bound,
and do those columns sit at his labelled ends (column centre within 2.5 sp for a slur, 3.5 for a tie, of his label's left / right edge).
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-arc-binding-2026-10"))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-arc-binding-2026-10" / "page-ink-2026-11" / "step2"))
from tools.omr.staged.judged import iter_array  # noqa: E402
import arcs as A  # noqa: E402

SAME_SP, DIFF_SP = 0.25, 0.435


def load(plate, rw, gw):
    ents = []
    for v in json.load(open(pathlib.Path(rw) / ("%s.on.extra.json" % plate))):
        pg = int(v["subject"].split("/")[1])
        for e in v["detail"]["runs"]:
            ents.append(dict(e, page=pg))
    pages = {e["page"] for e in ents}
    runs, heads, group, pos = {}, {}, {}, {}
    for o in iter_array(pathlib.Path(gw) / ("%s.on.gathered.record.json" % plate), "observations"):
        s, q = o.get("subject", ""), o.get("quantity")
        if q == "page_arc" and o.get("value") == "run":
            runs[o["id"]] = o["detail"]
        elif not s.startswith("glyph/") or int(s.split("/")[1]) not in pages:
            continue
        elif q == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
            heads[s] = [float(v) for v in o["detail"]["bbox_page_px"]]
        elif q == "mark_group":
            group[s] = str(o["value"])
        elif q == "notehead_staff_position" and isinstance(o.get("value"), (int, float)):
            pos[s] = float(o["value"])
    arcs = A.arcs_of_xml((pathlib.Path(rw) / ("%s.on.musicxml" % plate)).read_text())
    return ents, runs, heads, group, pos, arcs


def end_points(e, runs):
    d = runs[e["row"]]
    pts = d["points"]
    if e.get("x_range"):
        seg = [p for p in pts if e["x_range"][0] <= p[0] <= e["x_range"][1]]
        if seg:
            return [seg[0][:2], seg[-1][:2]], float(d["space_page_px"]), seg
    ce = d.get("core_ends") or [x[:2] for x in d["ends"]]
    return [ce[0][:2], ce[1][:2]], float(d["space_page_px"]), pts


def columns_of(staff, heads, group):
    """one entry per page head of the staff (twins once), grouped into columns by x"""
    pref = "glyph/%s/" % "/".join(staff.split("/")[1:4])
    seen, hs = set(), []
    for k, b in heads.items():
        if not k.startswith(pref):
            continue
        g = group.get(k, k)
        if g in seen:
            continue
        seen.add(g)
        hs.append(dict(key=k, box=b, cx=(b[0] + b[2]) / 2.0, cy=(b[1] + b[3]) / 2.0, w=b[2] - b[0]))
    hs.sort(key=lambda h: h["cx"])
    cols = []
    for h in hs:
        if cols and abs(h["cx"] - cols[-1]["cx"]) <= 0.5 * h["w"]:
            cols[-1]["heads"].append(h)
            cols[-1]["x0"] = min(cols[-1]["x0"], h["box"][0])
            cols[-1]["x1"] = max(cols[-1]["x1"], h["box"][2])
        else:
            cols.append(dict(cx=h["cx"], x0=h["box"][0], x1=h["box"][2], w=h["w"], heads=[h]))
    return cols


def main():
    plate, rw, gw = sys.argv[1:4]
    ents, runs, heads, group, pos, arcs = load(plate, rw, gw)
    colcache = {}
    reason = collections.Counter()
    klass = collections.Counter()
    klass_by_reason = collections.Counter()
    resolved = []
    for e in ents:
        if e["status"] != "abstained" or e["row"] not in runs or not e.get("home"):
            continue
        (L, R), sp, seg = end_points(e, runs)
        home = e["home"]
        if home not in colcache:
            colcache[home] = columns_of(home, heads, group)
        cols = colcache[home]
        out = {}
        for s_, (ex, ey) in (("left", L), ("right", R)):
            side = e.get(s_) or {}
            if side.get("head"):
                why = "bound (kind or other end refused: %s)" % e.get("why")
                k_ = "bound"
                col = next((c for c in cols if any(h["key"] == side["head"] or group.get(h["key"]) == group.get(side["head"]) for h in c["heads"])), None)
                out[s_] = ("bound", col, ey)
            elif side.get("edge"):
                why, k_ = "system_edge", "d"
                out[s_] = ("d", None, ey)
            else:
                why = (side.get("unbound") or ((e.get("unbound") or {}).get(s_) or {}).get("unbound") or e.get("why") or "other")
                cand = [c for c in cols if c["x0"] - c["w"] <= ex <= c["x1"] + c["w"]]
                k_ = "a" if len(cand) == 1 else "b" if cand else "c"
                out[s_] = (k_, cand[0] if len(cand) == 1 else None, ey)
            reason[why] += 1
            if k_ != "bound":
                klass[k_] += 1
                klass_by_reason[(why, k_)] += 1
        if all(out[s][0] in ("a", "bound") for s in ("left", "right")) and any(out[s][0] == "a" for s in ("left", "right")) \
                and out["left"][1] is not None and out["right"][1] is not None and out["left"][1] is not out["right"][1]:
            resolved.append((e, out, sp))
    print("== %s: abstained runs %d, ends by reason:" % (plate, sum(1 for e in ents if e["status"] == "abstained")))
    for k, v in reason.most_common():
        print("   %4d  %s" % (v, k))
    print("   unbound/edge ends by class: (a) one column %d | (b) two+ columns %d | (c) no note at that x %d | (d) system edge %d"
          % (klass["a"], klass["b"], klass["c"], klass["d"]))
    for (w, k), v in sorted(klass_by_reason.items()):
        print("      %-34s %s %d" % (w, k, v))
    # Q3
    file_arcs = [a for a in arcs]
    cmp_ = collections.Counter()
    kinds = collections.Counter()
    for e, out, sp in resolved:
        cl, cr = out["left"][1], out["right"][1]
        kl = {h["key"] for h in cl["heads"]} | {k for k, g in group.items() if g in {group.get(h["key"]) for h in cl["heads"]}}
        kr = {h["key"] for h in cr["heads"]} | {k for k, g in group.items() if g in {group.get(h["key"]) for h in cr["heads"]}}
        same = [a for a in file_arcs if (a["start"] in kl and a["stop"] in kr) or (a["start"] in kr and a["stop"] in kl)]
        one = [a for a in file_arcs if a not in same and (a["start"] in kl or a["stop"] in kl or a["start"] in kr or a["stop"] in kr)]
        cmp_["same pair already written (%s)" % "/".join(sorted({a["kind"] for a in same})) if same else
             "a different pair written at one of the columns" if one else "not written at all"] += 1
        # Q5
        ha = min(cl["heads"], key=lambda h: abs(h["cy"] - out["left"][2]))
        hz = min(cr["heads"], key=lambda h: abs(h["cy"] - out["right"][2]))
        agree = "tip at its head" if (abs(ha["cy"] - out["left"][2]) <= 1.5 * sp and abs(hz["cy"] - out["right"][2]) <= 1.5 * sp) else "tip > 1.5 sp from the column's nearest head"
        pa, pz = pos.get(ha["key"]), pos.get(hz["key"])
        if pa is None or pz is None:
            kinds[(agree, "position unread")] += 1
            continue
        dy = abs(pa - pz) / 2.0
        kinds[(agree, "tie candidate (same position)" if dy <= SAME_SP else "different positions (slur)" if dy >= DIFF_SP else "inside the gap (kind unread)")] += 1
    print("   Q3 runs whose two ends would be (a)-or-bound on two different columns: %d" % len(resolved))
    for k, v in cmp_.most_common():
        print("      %4d  %s" % (v, k))
    print("   Q5 kind of those: " + " | ".join("%s: %s %d" % (k[0], k[1], v) for k, v in sorted(kinds.items())))
    if "--sean" in sys.argv and plate == "brahms":
        import arcs_combined as AC
        keys = AC.key_sean()
        boxes = AC.head_boxes(pathlib.Path(gw) / "brahms.on.gathered.record.json", 0)
        spans = AC.spans_of((pathlib.Path(rw) / "brahms.on.musicxml").read_text(), boxes, 0)
        res, rows, _un = AC.score(keys, spans)
        SP = 32.0
        missing = [k for k in keys if rows[k["id"]][0] != "right"]
        r0 = [(e, out, sp) for e, out, sp in resolved if e["page"] == 0]
        hit, match = 0, 0
        lst = []
        for k in missing:
            reach = (3.5 if k["kind"] == "tie" else 2.5) * SP
            cand = []
            for e, out, sp in r0:
                xl, xr = out["left"][1]["cx"], out["right"][1]["cx"]
                yl = out["left"][2]
                if AC.yd(yl, k["y0"], k["y1"]) <= 6 * SP and xl - 3 * SP <= k["x0"] <= xr and xl <= k["x1"] <= xr + 3 * SP:
                    cand.append((e, out, abs(xl - k["x0"]) <= reach and abs(xr - k["x1"]) <= reach))
            if cand:
                hit += 1
                if any(c[2] for c in cand):
                    match += 1
            lst.append((k["id"], k["kind"], round(k["x0"]), round(k["x1"]), [(c[0]["ordinal"], c[0].get("why"), c[2]) for c in cand]))
        print("   Q4 Sean p0: %d of his 98 arcs not right in the file; %d have a run whose two ends resolve to (a)/bound columns; %d of those at his labelled ends by place"
              % (len(missing), hit, match))
        for l in lst:
            print("      ", l)


if __name__ == "__main__":
    main()
