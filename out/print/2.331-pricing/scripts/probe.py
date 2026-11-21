"""2.331 pricing probe (read-only): load a re-adjudicated record, export it with read-only wrappers that LOG what
`_settle_folded_pitches`, the four slur writers and `_place_notes` did, and dump the logs. Changes no pipeline code."""
import sys, json, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.omr.staged.record_io import load_record
from tools.omr.staged import export as E
from tools.omr.staged.lane_report import traced_export
from tools.omr.staged.record import Q

rec_path, out_json, xml_cmp = sys.argv[1:4]
result = load_record(rec_path)
LOG = {"folds": [], "spans": [], "fates": None}

# ---- item 1: the fold settle
orig_settle = E._settle_folded_pitches


def settle(rec, queued, best):
    by_gid = collections.defaultdict(list)
    for q in queued:
        gid, conf, sub, run, ci, det, s = q
        if gid is None or det.get("category") != "notehead" or not det.get("pitch"):
            continue
        by_gid[gid].append(q)
    before = {g: best[g][1] for g in by_gid if g in best}
    orig_settle(rec, queued, best)
    for gid, members in by_gid.items():
        if len(members) < 2:
            continue
        pitches = {q[5]["pitch"] for q in members}
        if len(pitches) < 2:
            continue
        ident = rec.obs(Q.MARK_GROUP, members[0][2])
        idn = (ident[-1].get("detail") or {}).get("identity") if ident else None
        mem = []
        for q in members:
            rows = rec.obs(Q.NOTEHEAD_STAFF_POSITION, q[2])
            d = (rows[-1].get("detail") or {}) if rows else {}
            gb = rec.obs(Q.GLYPH_BOX, q[2])
            pb = ((gb[-1].get("detail") or {}).get("bbox_page_px") if gb else None)
            mem.append(dict(sub=q[2], conf=q[1], pitch=q[5]["pitch"], rounded=d.get("rounded"),
                            hole=d.get("hole_ink_position"), centre=d.get("ink_centre_position_float"),
                            ledger=d.get("ledger_lines") if "ledger_lines" in d else d.get("ledger_count"),
                            detail_keys=sorted(d.keys())[:40], box=pb, run=(q[3].page, q[3].system, q[3].staff),
                            spacing=float(getattr(q[3], "spacing", 0) or 0), guess=bool(q[5].get("guess"))))
        LOG["folds"].append(dict(gid=gid, identity=idn, before=before.get(gid), after=best[gid][1], members=mem))


E._settle_folded_pitches = settle

# ---- item 2: the slur writers
TAG = {}
KEEP = []


def tagger(fn, name):
    def w(*a, **k):
        out = fn(*a, **k)
        for s in out or ():
            TAG.setdefault(id(s), name)
            KEEP.append(s)
        return out
    return w


E._legacy._paired_spans = tagger(E._legacy._paired_spans, "box_paired")
E._anchored_slur_spans = tagger(E._anchored_slur_spans, "anchored")
E._page_bound_slur_spans = tagger(E._page_bound_slur_spans, "page_bound")
orig_join = E._with_across_system_joins


def join(kind, spans, xs, xt, counters):
    out = orig_join(kind, spans, xs, xt, counters)
    for s in out:
        TAG.setdefault(id(s), "across_systems")
        KEEP.append(s)
    for s in out:
        if s[2] is not None:
            pass
    LOG["spans"].append(dict(stage="join", kind=kind, n=len(out)))
    return out


E._with_across_system_joins = join
orig_drop_unison = E._drop_unison_same_pitch_slurs


def drop_unison(spans, counters):
    out = orig_drop_unison(spans, counters)
    for s in out:
        KEEP.append(s)
        LOG["spans"].append(dict(stage="final_slur", writer=TAG.get(id(s), "?"),
                                 first=s[2].get("glyph"), last=s[3].get("glyph"), fid=id(s[2]), lid=id(s[3]),
                                 sm=s[0][0], tm=s[1][0]))
    return out


E._drop_unison_same_pitch_slurs = drop_unison
orig_rts = E._record_tie_spans


def rts(*a, **k):
    out = orig_rts(*a, **k)
    for s in out:
        KEEP.append(s)
        LOG["spans"].append(dict(stage="tie", writer="record_tie", first=s[2].get("glyph"), last=s[3].get("glyph"),
                                 fid=id(s[2]), lid=id(s[3]), sm=s[0][0], tm=s[1][0]))
    return out


E._record_tie_spans = rts

# ---- item 6: fates
orig_place = E._place_notes


def place(*a, **k):
    out = orig_place(*a, **k)
    LOG["fates"] = dict(k.get("fates") or {})
    return out


E._place_notes = place

with traced_export():
    xml, report = E.to_musicxml(result)
same = pathlib.Path(xml_cmp).read_text() == xml
print("xml identical to the plain re-export:", same)
LOG["xml_identical"] = same
pathlib.Path(out_json).write_text(json.dumps(LOG, default=str))
print("folds", len(LOG["folds"]), "spans rows", len(LOG["spans"]), "fates", len(LOG["fates"] or {}))
