"""ROADMAP 2.182 -- which two-part witnesses the record carries, per bar, before anything is built.

usage: python3 benchmarks/omr-two-parts-one-staff-2026-10/probe/p2_witness.py RECORD RED_ROWS CENSUS LABELS OUT.json
Per cell (Q.EVENT decided): chords with a DECIDED Q.STEM_DIRECTION up / down / none; head positions
(Q.NOTEHEAD_STAFF_POSITION, half-steps from the TOP line, larger = lower); rest steps (bottom line 0, up positive,
`rhythm._staff_step`'s frame) of rests no gate refused; whether an `a2` word stands in the bar. Then the witnesses:
  sep    -- every up-stem head above every down-stem head (two parts' order)
  inv    -- every down-stem head above every up-stem head (one line whose stems flip at the middle line)
  rest_hi / rest_lo -- a rest at least 1.5 steps above / below the middle line (2.27c's displacement)
and the cross-tab against 2.179's labels (fv = two parts) and the red bars. Read-only.
"""
import collections
import json
import sys

rec_path, red_path, census_path, labels_path, out_path = sys.argv[1:6]
red = {"%d/%d/%d/%d" % (r["page"], r["system"], r["staff"], r["cell"]) for r in json.load(open(red_path))}
census = json.load(open(census_path))
labels = {}
for line in open(labels_path):
    if line.startswith("#") or "|" not in line:
        continue
    i, codes, text = [x.strip() for x in line.split("|", 2)]
    labels[int(i)] = codes.split()
lab = {}
for i, e in enumerate(census):
    lab.setdefault(e["bar"], labels[i])
rec = json.load(open(rec_path))["record"]
events = {}
voices = {}
gv = collections.defaultdict(dict)
for v in rec["verdicts"]:
    s = v.get("subject") or ""
    q = v.get("quantity")
    if q == "event" and s.startswith("cell/") and v.get("outcome") == "decided":
        events[s[5:]] = (v.get("value") or {}).get("events") or []
    elif q == "voices" and s.startswith("cell/"):
        voices[s[5:]] = (v.get("outcome"), v.get("reason"))
    elif s.startswith("glyph/") and q in ("stem_direction", "rest_is_not_a_rest"):
        gv[s][q] = (v.get("outcome"), v.get("value"))
pos, box = {}, {}
lines, space = {}, {}
a2 = set()
for o in rec["observations"]:
    q = o.get("quantity")
    s = o.get("subject") or ""
    if q == "notehead_staff_position":
        pos[s] = o.get("value")
    elif q == "glyph_box" and s not in box:
        box[s] = (o.get("detail") or {}).get("bbox_page_px")
    elif q == "staff_lines":
        lines[s] = o.get("value")
    elif q == "staff_spacing":
        space[s] = o.get("value")
    elif q == "direction_word" and "a2" in ((o.get("detail") or {}).get("terms") or ()):
        a2.add("/".join(s.split("/")[1:5]))


def rest_step(bar, g):
    p, sy, st, _c = bar.split("/")
    sk = "staff/%s/%s/%s" % (p, sy, st)
    b = box.get("glyph/%s/%d" % (bar, g))
    ly, sp = lines.get(sk), space.get(sk)
    if not b or not ly or not sp:
        return None
    return (max(float(y) for y in ly) - (b[1] + b[3]) / 2.0) / (float(sp) / 2.0)


rows = []
for bar, evs in events.items():
    ups, downs, nones, rhi, rlo, rmid = [], [], 0, 0, 0, 0
    for e in evs:
        gs = e.get("glyphs") or ()
        if e.get("kind") == "rest":
            g = gs[0] if gs else None
            if g is None:
                continue
            ref = gv.get("glyph/%s/%d" % (bar, g), {}).get("rest_is_not_a_rest")
            if ref and ref[1] is True:
                continue
            st = rest_step(bar, g)
            if st is None:
                continue
            if st >= 5.5:
                rhi += 1
            elif st <= 2.5:
                rlo += 1
            else:
                rmid += 1
            continue
        dirs = collections.Counter()
        ps = []
        for g in gs:
            s = "glyph/%s/%d" % (bar, g)
            d = gv.get(s, {}).get("stem_direction")
            if d and d[0] == "decided":
                dirs[d[1]] += 1
            if isinstance(pos.get(s), (int, float)):
                ps.append(float(pos[s]))
        dr = dirs.most_common(1)[0][0] if dirs else None
        if e.get("unison"):
            dr = "unison"
        if dr == "up":
            ups.extend(ps)
        elif dr == "down":
            downs.extend(ps)
        else:
            nones += 1
    sep = bool(ups and downs and max(ups) < min(downs))
    inv = bool(ups and downs and max(downs) < min(ups))
    rows.append(dict(bar=bar, red=bar in red, label=lab.get(bar), voices=voices.get(bar), n_up=len(ups), n_down=len(downs),
                     n_none=nones, sep=sep, inv=inv, rest_hi=rhi, rest_lo=rlo, rest_mid=rmid, a2=bar in a2))
json.dump(rows, open(out_path, "w"))


def cls(r):
    if r["label"] and "fv" in r["label"]:
        return "fv"
    if r["red"]:
        return "red_other"
    return "not_red"


tab = collections.defaultdict(collections.Counter)
for r in rows:
    k = cls(r)
    tab[k]["bars"] += 1
    both = r["n_up"] > 0 and r["n_down"] > 0
    tab[k]["both_dirs"] += both
    tab[k]["sep"] += r["sep"]
    tab[k]["inv"] += r["inv"]
    tab[k]["rest_hi"] += r["rest_hi"] > 0
    tab[k]["rest_lo"] += r["rest_lo"] > 0
    tab[k]["rest_hi_and_only_down"] += (r["rest_hi"] > 0 and r["n_down"] > 0 and r["n_up"] == 0)
    tab[k]["rest_lo_and_only_up"] += (r["rest_lo"] > 0 and r["n_up"] > 0 and r["n_down"] == 0)
    tab[k]["sep_or_displaced"] += (r["sep"] or (r["rest_hi"] > 0 and r["n_down"] > 0 and r["n_up"] == 0)
                                   or (r["rest_lo"] > 0 and r["n_up"] > 0 and r["n_down"] == 0))
    tab[k]["a2"] += r["a2"]
for k, c in tab.items():
    print(k, dict(c))
