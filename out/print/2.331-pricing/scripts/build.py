"""Tile specs per item for one plate from the analysis outputs (seeded sample where a cap applies)."""
import sys, json, re, random, collections
plate, base, pages_s = sys.argv[1:4]
pages = {int(p) for p in pages_s.split(",")}
pg = lambda k: int(str(k).split("/")[1])
I = json.load(open(base + ".items.json"))
B = I["boxes_of"]
xml = open(base.replace("/" + plate, "/" + plate + ".readj") + ".musicxml").read()
rnd = random.Random(2331)
U = {"litolff": 15.75, "brahms": 32.0}[plate]
S = {}


def union(bs):
    bs = [b for b in bs if b]
    return [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)] if bs else None


# item 1: every far fold
S[1] = []
for o in json.load(open(base + ".item1.json")):
    if not o["far"]:
        continue
    ch = next(m for m in o["members"] if m["sub"] == o["chosen"])
    S[1].append(dict(plate=plate, page=o["page"], box=ch["box"], half_h_sp=8, key=dict(
        chosen_box=o["chosen"], twins=[[m["sub"], m["pitch"], m["rounded"]] for m in o["members"]], how=o["how"], ink_witness=o["witness"],
        file_writes=(o["written"] or {}).get("pitch"), file_marks=("blue" if (o["written"] or {}).get("blue") else "plain") if o["written"] else "not written",
        note="rounded = staff position, 0 = top line, 8 = bottom line; outside -1..9 = a far head")))
# item 2: slurs the FILE writes twice on the same two notes (by the chord's first note)
dups = []
for part in re.findall(r"<part id=.*?</part>", xml, re.S):
    open_, fx, first_of = {}, collections.defaultdict(int), {}
    cur = None
    for m in re.finditer(r'<note rg="([^"]+)"(.*?)</note>', part, re.S):
        g, body = m.group(1), m.group(2)
        if "<chord/>" not in body:
            cur = g
        first_of.setdefault(cur, []).append(g)
        for n, t in re.findall(r'<slur[^>]*number="(\d+)"[^>]*type="(start|stop)"', body):
            if t == "start":
                open_[n] = cur
            elif n in open_:
                fx[(open_.pop(n), cur)] += 1
    for (a, b), c in fx.items():
        if c > 1 and pg(a) in pages:
            dups.append((a, b, c, first_of.get(a, [a]), first_of.get(b, [b])))
runs = [w for p_, ws in I["written_runs"].items() for w in ws]
S[2] = []
for a, b, c, ma, mb in (rnd.sample(dups, 6) if len(dups) > 6 else dups):
    box = union([B.get(x) for x in ma + mb])
    hit = [w for w in runs if str(w.get("start")) in ma + mb or str(w.get("stop")) in ma + mb]
    S[2].append(dict(plate=plate, page=pg(a), box=[box[0], box[1] - 2 * U, box[2], box[3] + 2 * U], half_h_sp=7, key=dict(
        start_event=ma, stop_event=mb, slurs_written=c, writer="_page_bound_slur_spans (page-bound curves)",
        page_arc_runs_on_these_ends=[[w["row"], w["kind"], w.get("start"), w.get("stop")] for w in hit])))
S["2_count"] = len(dups)
# item 3: marks refused by an arc_trace claim (no head or rest is): flags / ledgers, up to 6
r3 = [r for r in I["item3"]["rows"] if r["by"] in ("arc", "arc_trace")]
S[3] = []
for r in (rnd.sample(r3, 6) if len(r3) > 6 else r3):
    S[3].append(dict(plate=plate, page=pg(r["sub"]), box=r["box"], key=dict(subject=r["sub"], refused_as=r["quantity"], reason=r["reason"], by=r["by"],
                     ink_share_held=r["share"], also=r["also"], written_arc_over_the_claim=r["written_arc_over_claim"])))
# item 4: every written dynamic whose letters lie in a read word (<= 12)
S[4] = []
for r in I["item4"]["rows"][:12]:
    S[4].append(dict(plate=plate, page=pg(r["cell"]), box=r["box"], half_w_sp=max(7, (r["word_box"][2] - r["word_box"][0]) / U / 2 + 2), key=dict(
        cell=r["cell"], file_writes_dynamic=r["text"], outcome=r["outcome"], letters=r["letters"], read_word=r["word"])))
# item 5: A's stem-beam join vs the one beam count, 3 of each kind
S[5] = []
rows5 = I["item5"]["rows"]
for kind in ("A_joins_a_beam__one_count_reads_none", "one_count_reads_a_beam__A_joins_none"):
    rs = [r for r in rows5 if r["kind"] == kind and r["box"]]
    for r in (rnd.sample(rs, 3) if len(rs) > 3 else rs):
        b = r["box"]
        side = ((r["one"].get("stems") or [{}])[0]).get("side")
        bb = [b[0] - 0.6 * U, b[1] - 3.8 * U, b[2] + 0.6 * U, b[1]] if side == "up" else [b[0] - 0.6 * U, b[3], b[2] + 0.6 * U, b[3] + 3.8 * U]
        S[5].append(dict(plate=plate, page=pg(r["sub"]), box=bb, key=dict(
            head=r["sub"], head_box=b, which=kind, reader_A_strokes_joined_to_stem=r["A_joined"], one_beam_count=[r["one"]["certain"], r["one"]["possible"]],
            stem_side=side, flags_attached=r["flags_attached"], file_writes=r["written_type"], file_beam_on_this_note=r["written_beam"],
            box_note="red box = where the beam would meet this note's stem (from the head toward the stem tip, 3.8 spaces)")))
# item 6
S[6] = []
for r in json.load(open(base + ".item6.json"))["rows"][:12]:
    S[6].append(dict(plate=plate, page=r["page"], box=r["box"], key=dict(tile_item=r["item"], judged_tile=r["tile"], sean=r["answer"], scored_on_dropped_twin=r["scored_on"],
                     written_by=r["written_by"], file_writes=r["file_type"], file_blue=r["file_blue"])))
json.dump(S, open(base + ".specs.json", "w"), indent=1, default=str)
print({k: len(v) if isinstance(v, list) else v for k, v in S.items()})
