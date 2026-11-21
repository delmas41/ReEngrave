"""Item 1: the folds `_settle_folded_pitches` settled among twins that disagree in pitch (replicating its head filter), far members flagged."""
import sys, json, re
probe, xml_path, pages = sys.argv[1], sys.argv[2], {int(p) for p in sys.argv[3].split(",")}
L = json.load(open(probe))
xml = open(xml_path).read()
# the written note for a glyph key: its <note ...rg="key"> element
notes = {}
for m in re.finditer(r'<note rg="([^"]+)"(.*?)</note>', xml, re.S):
    notes[m.group(1)] = m.group(0)


def written(sub):
    n = notes.get(sub)
    if n is None:
        return None
    st = re.search(r"<step>(\w)</step>", n)
    oc = re.search(r"<octave>(\d)</octave>", n)
    al = re.search(r"<alter>(-?\d)</alter>", n)
    blue = 'color="#1F6FEB"' in n
    return dict(pitch=(st.group(1) if st else "?") + (("#" if al and al.group(1) == "1" else "b" if al and al.group(1) == "-1" else "")) + (oc.group(1) if oc else "?"),
                blue=blue)


out = []
for f in L["folds"]:
    m0 = f["members"][0]
    pg = int(m0["sub"].split("/")[1])
    if pg not in pages:
        continue
    heads = []
    for m in f["members"]:
        sp, pb = m["spacing"], m["box"]
        if tuple(m["run"]) != tuple(m0["run"]) or sp <= 0 or not pb:
            continue
        bw, bh = pb[2] - pb[0], pb[3] - pb[1]
        if bh > 1.6 * sp or min(bw, bh) < 0.6 * sp:
            continue
        heads.append(m)
    if len({m["pitch"] for m in heads}) < 2:
        continue
    wit = [m["hole"] if isinstance(m["hole"], (int, float)) else m["centre"] for m in heads]
    wit = [w for w in wit if isinstance(w, (int, float))]
    how = "no_witness_blue"
    if wit:
        step = int(round(sum(wit) / len(wit)))
        on = [m for m in heads if m["rounded"] == step]
        how = "decided_by_ink" if len(on) == 1 else "witness_matches_%d_blue" % len(on)
    far = any(m["rounded"] is not None and not (-1 <= m["rounded"] <= 9) for m in heads)
    w = written(f["after"])
    out.append(dict(gid=f["gid"], page=pg, how=how, far=far, chosen=f["after"], before=f["before"], witness=wit,
                    members=[dict(sub=m["sub"], pitch=m["pitch"], rounded=m["rounded"], conf=round(m["conf"], 3), box=m["box"]) for m in heads],
                    written=w))
json.dump(out, open(sys.argv[4], "w"), indent=1)
import collections
print("settled folds with differing pitch:", len(out), collections.Counter(o["how"] for o in out))
print("with a far member:", sum(o["far"] for o in out), collections.Counter((o["how"], (o["written"] or {}).get("blue")) for o in out if o["far"]))
for o in out:
    if o["far"]:
        print(o["page"], o["how"], [(m["pitch"], m["rounded"], m["conf"]) for m in o["members"]], "witness", o["witness"], "->", o["chosen"], o["written"])
