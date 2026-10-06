"""lane-farhead-not-a-note (2026-10-05): the not-a-note gate at the entry of the far-head reader. READ ONLY -- no gather.

The evidence the gate reads is what the record holds ABOUT each far head, indexed straight off a record's rows
(`evidence_index`): the measure cell's page box and the measure cuts of its own staff (`cell_box` rows), 2.49's
`notehead_stem_cross_ink` detail, and -- only for the "with verdict" arm -- the `notehead_is_not_a_notehead` verdict
(which does NOT exist at GATHER, so the headline arm is WITHOUT it, exactly what a gather would see).

  python3 farhead_not_a_note_eval.py control     # the truth-set far heads (Litolff p3, Brahms p1) + Sean's tiles
  python3 farhead_not_a_note_eval.py oos         # the 10-04 run-2 records, every far head, refusals by reason
"""
from __future__ import annotations
import collections, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg
from tools.omr.staged.record import Q

CROSS = Q.NOTEHEAD_STEM_CROSS_INK
SEAN = {  # tile -> (doc, subject, what Sean said it is)
    1: ("litolff", "glyph/14/1/9/0/17", "a barline/bracket"), 5: ("litolff", "glyph/13/0/5/10/0", "a tremolo slash"),
    7: ("brahms", "glyph/9/1/1/0/14", 'the "a 2" numeral'), 8: ("brahms", "glyph/10/1/7/3/6", "a barline/bracket"),
    2: ("litolff", "glyph/4/1/6/4/0", "a real head"), 12: ("brahms", "glyph/5/1/2/3/20", "a real head")}


def evidence_index(rec, with_verdict=False):
    """subject-key -> dict(cell_box, barline_xs, cross[, decided]) built off the record's rows, for every glyph whose
    cell / staff the caller asks about, lazily from three row sets."""
    cell_box, cross, decided = {}, {}, {}
    for o in rec.observations:
        q = o["quantity"]
        if q == Q.CELL_BOX and o.get("value"):
            cell_box[o["subject"]] = tuple(float(v) for v in o["value"])
        elif q == CROSS:
            cross[o["subject"]] = dict(o.get("detail") or {})
    if with_verdict:
        for v in rec.verdicts:
            if v["quantity"] == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD and v.get("value") is True:
                decided[v["subject"]] = str(v.get("reason"))
    cuts = collections.defaultdict(set)
    for ck, b in cell_box.items():
        cuts["/".join(ck.split("/")[1:4])].update((b[0], b[2]))

    def get(subject):
        p = subject.split("/")
        ck = "cell/" + "/".join(p[1:5])
        ev = dict(cell_box=cell_box.get(ck), barline_xs=sorted(cuts.get("/".join(p[1:4]), ())))
        if subject in cross:
            ev["cross"] = cross[subject]
        if subject in decided:
            ev["decided"] = decided[subject]
        return ev
    return get


def main_control():
    import jut_from_ink_eval as J
    import edge_census as ec
    FH.CHORD_SPLIT = True
    FH.READER_KEYWORDS.update(through_head_on_rung=True, note_first=True, ledger_not_text=True)
    FH.EXCLUSION_RULES["jut_from_ink"] = True
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        L, fp, far = J.prepare(doc, page)
        get = evidence_index(L["rec"])
        res = {}
        for on in (False, True):
            FH.READER_KEYWORDS["not_a_note"] = on
            fp.not_a_note = {h["subject"]: get(h["subject"]) for h in L["heads"]} if on else {}
            out = {}
            for h in far:
                sk = "staff/" + "/".join(h["subject"].split("/")[1:4])
                r = fp.read(h["subject"], h["box"], h["cls"], L["staff_lines"][sk])
                out[h["subject"]] = (ec.verdict(r["pos"], h["truth"]), r["pos"], r["reason"])
            res[on] = out
        refused = [s for s, v in res[True].items() if v[2].startswith("not_a_note")]
        print("==", doc, "p%d" % page, "far heads", len(far),
              "| gate OFF", J.tal(res[False]), "| gate ON", J.tal(res[True]), "| REFUSED by the gate:", len(refused))
        for s in refused:
            print("   refused", s, res[True][s][2], "(off:", res[False][s][:2], ")")
        diff = [s for s in res[False] if res[False][s][:2] != res[True][s][:2]]
        print("   heads whose reading differs on/off:", len(diff))
    FH.READER_KEYWORDS["not_a_note"] = True


def main_oos():
    import farhead_note_first_oos as OOS
    from tools.omr.staged import export as EXP
    from tools.omr.staged.record_io import load_record
    ranges = {"litolff": (4, 16), "brahms": (2, 26)}
    for which, (p0, p1) in ranges.items():
        doc, fname = OOS.RECORDS[which]
        rec = EXP.Record(load_record(OOS.SHARED / fname))
        get = evidence_index(rec)
        getv = evidence_index(rec, with_verdict=True)
        glyphs = collections.defaultdict(list)
        for o in rec.observations:
            if o["quantity"] != Q.GLYPH_BOX or not o.get("value"):
                continue
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                glyphs[int(o["subject"].split("/")[1])].append(
                    (o["subject"], o["value"][0], tuple(float(v) for v in pb), 1.0))
        far_n, by, byv, also = 0, collections.Counter(), collections.Counter(), collections.Counter()
        both, barpos = collections.Counter(), collections.Counter()
        refused = []
        for page in range(p0, p1 + 1):
            if page not in glyphs:
                continue
            heads, staff_lines, page_boxes = OOS.page_inputs(rec, page, glyphs[page])
            text = [tuple(b) for (_s, c, b) in page_boxes if lg.is_text_class(c)]
            for h in heads:
                if not lg.far_head_needs_ledger_read(h["pos"]):
                    continue
                far_n += 1
                gl = h["global_lines"]
                sp = (max(gl) - min(gl)) / 4.0
                ev = get(h["subject"])
                r = FH.not_a_note_reason(h["box"], h["cls"], sp, cell_box=ev["cell_box"], cross=ev.get("cross"),
                                         barline_xs=ev["barline_xs"], text_boxes=text)
                if r:
                    dec = bool(getv(h["subject"]).get("decided"))
                    both[(r["reason"], dec)] += 1
                    if r["reason"] == "on_a_barline":
                        cut = r["drawn"][0][1]
                        inside = h["box"][0] <= cut <= h["box"][2]
                        barpos[(inside, dec)] += 1
                    by[r["reason"]] += 1
                    refused.append((h["subject"], r["reason"], r["also"]))
                    for a in r["also"]:
                        also[a] += 1
                evv = getv(h["subject"])
                rv = FH.not_a_note_reason(h["box"], h["cls"], sp, cell_box=evv["cell_box"], cross=evv.get("cross"),
                                          barline_xs=evv["barline_xs"], text_boxes=text, decided=evv.get("decided"))
                if rv:
                    byv[rv["reason"]] += 1
        print(f"== {which}: far heads {far_n} | refused at GATHER-time evidence {sum(by.values())} "
              f"({100.0 * sum(by.values()) / max(1, far_n):.1f}%) by reason {dict(by)}")
        print(f"   also fired (second reasons) {dict(also)}")
        print(f"   with the record's own verdict as well: {sum(byv.values())} by {dict(byv)}")
        print("   refused by reason, (reason, the record's verdict ALSO says not-a-notehead):", dict(both))
        print("   on_a_barline: (cut inside the box?, already decided not-a-notehead?):", dict(barpos))
        out = HERE / f"farhead_not_a_note_oos_{which}.json"
        import json
        out.write_text(json.dumps(dict(far=far_n, by=by, refused=refused), indent=0))
        del rec


def main_tiles():
    """Sean's six tiles of the note-first abstain sheet (1,5,7,8 not notes; 2,12 real heads), on the 10-04 records."""
    import farhead_note_first_oos as OOS
    from tools.omr.staged import export as EXP
    from tools.omr.staged.record_io import load_record
    recs = {}
    for tile, (which, subj, what) in sorted(SEAN.items()):
        if which not in recs:
            doc, fname = OOS.RECORDS[which]
            recs[which] = EXP.Record(load_record(OOS.SHARED / fname))
        rec = recs[which]
        page = int(subj.split("/")[1])
        glyphs = []
        for o in rec.observations:
            if o["quantity"] == Q.GLYPH_BOX and o.get("value") and int(o["subject"].split("/")[1]) == page:
                pb = (o.get("detail") or {}).get("bbox_page_px")
                if pb:
                    glyphs.append((o["subject"], o["value"][0], tuple(float(v) for v in pb), 1.0))
        heads, _sl, page_boxes = OOS.page_inputs(rec, page, glyphs)
        h = [x for x in heads if x["subject"] == subj][0]
        gl = h["global_lines"]
        ev = evidence_index(rec)(subj)
        text = [tuple(b) for (_s, c, b) in page_boxes if lg.is_text_class(c)]
        r = FH.not_a_note_reason(h["box"], h["cls"], (max(gl) - min(gl)) / 4.0, cell_box=ev["cell_box"],
                                 cross=ev.get("cross"), barline_xs=ev["barline_xs"], text_boxes=text)
        print(f"tile {tile:2d} {subj:22s} Sean: {what:22s} -> gate: "
              + (f"{r['reason']} (also {r['also']})" if r else "NOT refused"))


if __name__ == "__main__":
    {"control": main_control, "oos": main_oos, "tiles": main_tiles}[sys.argv[1]]()
