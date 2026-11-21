"""Items 3-6 + the F3 case from one load of a re-adjudicated record (read-only). Writes <out>.items.json and <out>.mini-record.json."""
import sys, json, re, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.omr.staged.record_io import load_record
from tools.omr.staged import claims as CL
from tools.omr.staged import judged as J

rec_path, probe_path, xml_path, doc, pages_s, out = sys.argv[1:7]
pages = {int(p) for p in pages_s.split(",")}
pg = lambda k: int(str(k).split("/")[1])
res = load_record(rec_path)
r = res["record"]
obs = r["observations"]
vs = r["verdicts"]
P = json.load(open(probe_path))
fates = P["fates"]
xml = open(xml_path).read()
notes = {}
for m in re.finditer(r'<note rg="([^"]+)"(.*?)</note>', xml, re.S):
    notes.setdefault(m.group(1), m.group(0))

box = {}
for o in obs:
    if o["quantity"] == "glyph_box":
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b:
            box[o["subject"]] = [float(x) for x in b]
live = {}
sup = {v.get("supersedes") for v in vs if v.get("supersedes")}
for v in vs:
    if v["id"] in sup:
        continue
    live[(v["subject"], v["quantity"])] = v
OUT = {}

# ---------- item 3: heads / rests refused by an arc claim (reason claimed_by:page_claim, ink_consult.by arc*)
arc_claims = [o for o in obs if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("owner") in ("arc", "arc_trace")]
runs = J.written_arc_runs(pathlib.Path(rec_path), pages) if False else None   # pooled file: computed below from the loaded rows instead
pa_rows = {o["id"]: (o.get("detail") or {}) for o in obs if o["quantity"] == "page_arc" and o.get("value") == "run"}
written_runs = collections.defaultdict(list)
for (subj, q), v in live.items():
    if q == "page_arc_binding":
        for e in (v.get("detail") or {}).get("runs") or ():
            d = pa_rows.get(e.get("row"))
            if e.get("status") == "written" and d and d.get("bbox_page_px"):
                written_runs[pg(subj)].append(dict(row=e["row"], kind=e.get("kind"), bbox=[float(x) for x in d["bbox_page_px"]],
                                                   start=e.get("start"), stop=e.get("stop"), x_range=e.get("x_range")))
OUT["written_runs"] = written_runs
OUT["boxes_of"] = {}
i3 = []
any_arc_reason = collections.Counter()
for (subj, q), v in live.items():
    if not q.endswith("_is_not_a_" + q.split("_is_not_a")[0].split("_")[0]) and q not in ("notehead_is_not_a_notehead", "rest_is_not_a_rest", "flag_is_not_a_flag", "ledger_is_not_a_ledger", "accidental_is_not_an_accidental", "arpeggiato_is_not_an_arpeggiato", "dot_is_not_a_dot"):
        continue
    if not subj.startswith("glyph/"):
        continue
    d = v.get("detail") or {}
    ic = d.get("ink_consult") or d.get("claim_final") or {}
    fams = [ic.get("by")] + list(ic.get("also") or ())
    if any(f in ("arc", "arc_trace") for f in fams if f):
        any_arc_reason[(q, v.get("outcome"), v.get("reason"), ic.get("by"))] += 1
        if pg(subj) not in pages:
            continue
        b = box.get(subj)
        # the arc claim on this staff whose pieces lie nearest the box
        p_, s_, st_ = subj.split("/")[1:4]
        cand = [o for o in arc_claims if o["subject"] == "staff/%s/%s/%s" % (p_, s_, st_)]
        def cbox(o):
            bs = [box[k] for k in (o["detail"].get("pieces") or ()) if k in box]
            return [min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs)] if bs else None
        best = None
        for o in cand:
            cb = cbox(o)
            if cb and b and CL.overlaps([cb[0] - 20, cb[1] - 20, cb[2] + 20, cb[3] + 20], b):
                best = (o, cb)
                break
        backed = None
        if best:
            cb = best[1]
            backed = [w for w in written_runs.get(pg(subj), ()) if CL.overlaps(w["bbox"], cb)]
        i3.append(dict(sub=subj, quantity=q, outcome=v.get("outcome"), reason=v.get("reason"), by=ic.get("by"), also=ic.get("also"),
                       share=ic.get("share"), box=b, fate=fates.get(subj), claim=(best[0]["id"] if best else None), claim_box=(best[1] if best else None),
                       written_arc_over_claim=[(w["row"], w["kind"]) for w in (backed or ())]))
OUT["item3"] = dict(reasons=[[list(k), n] for k, n in any_arc_reason.items()], rows=i3, arc_claims=len(arc_claims))

# ---------- item 4: written dynamics whose letters `letters_of_the_word` gives to a read word
nb = {o["subject"]: o.get("value") for o in obs if o["quantity"] == "dynamic_letter_neighbours"}
words_by_sys = collections.defaultdict(list)
for o in obs:
    if o["quantity"] == "direction_word" and isinstance(o.get("value"), str):
        wb = (o.get("detail") or {}).get("bbox_page_px")
        if wb:
            words_by_sys[tuple(o["subject"].split("/")[1:3])].append(dict(id=o["id"], text=o["value"], box=[float(x) for x in wb]))
obs_by_id = {o["id"]: o for o in obs if o["quantity"] == "dynamic_letter"}
i4 = []
n_written = 0
for (subj, q), v in live.items():
    if q != "dynamic" or not v.get("value") or pg(subj) not in pages:
        continue
    for w in (v.get("detail") or {}).get("words") or ():
        n_written += 1
        lets = [obs_by_id[i] for i in w.get("letters") or () if i in obs_by_id]
        lb = [[float(x) for x in l["detail"]["bbox_page_px"]] for l in lets if (l.get("detail") or {}).get("bbox_page_px")]
        if not lb:
            continue
        rb = [min(b[0] for b in lb), min(b[1] for b in lb), max(b[2] for b in lb), max(b[3] for b in lb)]
        near = any(isinstance(nb.get(l["subject"]), dict) and (nb[l["subject"]].get("left") or nb[l["subject"]].get("right")) for l in lets)
        sysk = tuple(subj.split("/")[1:3])
        holding = [x for x in words_by_sys.get(sysk, ()) if CL.overlaps(rb, x["box"])]
        if not holding:
            continue
        says = [CL.letters_of_the_word(lb, x["box"], x["text"], near) for x in holding]
        if all(s == "letters_of_a_word" for s in says):
            i4.append(dict(cell=subj, text=w.get("text"), outcome=v.get("outcome"), identity=w.get("identity"), letters=[l["subject"] for l in lets],
                           box=rb, word=holding[0]["text"], word_box=holding[0]["box"], neighbour_ink=near))
OUT["item4"] = dict(written_dynamic_words=n_written, rows=i4)

# ---------- item 5: reader A's stem-beam join vs the one beam count, on written notes
i5 = []
tot = collections.Counter()
for (subj, q), v in live.items():
    if q != "duration" or not subj.startswith("glyph/") or pg(subj) not in pages or fates.get(subj) != "written":
        continue
    d = v.get("detail") or {}
    ob = d.get("one_beam_count")
    if not isinstance(ob, dict):
        tot["no_one_count"] += 1
        continue
    a = int(d.get("beams_by_stem") or 0)
    st = ob.get("state")
    c_, p_ = ob.get("certain"), ob.get("possible")
    one_yes = st != "silent" and ((c_ or 0) > 0)
    one_no = st == "read" and (c_ or 0) == 0 and (p_ or 0) == 0
    tot["written_with_count"] += 1
    kind = None
    if a > 0 and one_no:
        kind = "A_joins_a_beam__one_count_reads_none"
    elif a == 0 and one_yes:
        kind = "one_count_reads_a_beam__A_joins_none"
    if kind:
        tot[kind] += 1
        n = notes.get(subj, "")
        typ = re.search(r"<type>(\w+)</type>", n)
        i5.append(dict(sub=subj, kind=kind, A_joined=a, one=dict(state=st, certain=c_, possible=p_, why=ob.get("why"), stems=ob.get("stems")),
                       flags_attached=d.get("flags_attached"), outcome=v.get("outcome"), value=v.get("value"),
                       written_type=typ.group(1) if typ else None, written_beam=bool(re.search(r"<beam ", n)), blue='#1F6FEB' in n, box=box.get(subj)))
OUT["item5"] = dict(totals=dict(tot), rows=i5)

# ---------- mini-record for the judged scorer
mini = {"observations": [o for o in obs if o["quantity"] == "glyph_box"], "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in J._QUANTITIES]}
mp = pathlib.Path(out + ".mini-record.json")
mp.write_text(json.dumps(mini, default=str))
# mark groups for item 6
mg = {}
for o in obs:
    if o["quantity"] == "mark_group":
        mg.setdefault(o["subject"], o.get("value") if isinstance(o.get("value"), str) else (o.get("detail") or {}).get("group"))
OUT["mark_group"] = mg
# the F3 case: Litolff 2/1/3 measure 37 -- every written note on staff 2/1/3 with its clef-claim share
f3 = []
for (subj, q), v in live.items():
    if q == "notehead_is_not_a_notehead" and subj.startswith("glyph/2/1/3/"):
        d = v.get("detail") or {}
        f3.append(dict(sub=subj, value=v.get("value"), reason=v.get("reason"), ink=d.get("ink_consult"), cf=d.get("claim_final"), fate=fates.get(subj), box=box.get(subj)))
OUT["f3_candidates"] = f3
OUT["boxes_of"] = {k: b for k, b in box.items() if k in fates}
pathlib.Path(out + ".items.json").write_text(json.dumps(OUT, default=str, indent=1))
print("item3 reasons", OUT["item3"]["reasons"], "rows", len(i3))
print("item4 written dynamic words", n_written, "letters of a word", len(i4))
print("item5", dict(tot))
