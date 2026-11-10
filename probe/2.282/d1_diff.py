"""2.282 step 2 (STAGED, read-only): the disagreements between two re-adjudicated arms of the SAME saved gather (same tree, same rows, one env var apart).
Matched by glyph / cell id (identical across arms: the rows are the same saved GATHER rows), never across different runs.

  stroke   a stroke whose owner (state, family) differs: base -> arm
  head     a head box whose notehead_is_not_a_notehead outcome/reason differs (kept <-> refused)
  after    what follows on a head whose fate is unchanged: duration / head_stem / stem_value / accidental_owner / accidental verdicts that differ
usage: d1_diff.py BASE_DIR ARM_DIR PLATE OUT.json"""
import collections
import json
import sys

base, arm, plate, out = sys.argv[1:5]


def load(d):
    own = {}                       # (cell, ordinal) -> (state, family, [owner keys])
    head = {}                      # glyph -> (outcome, reason)
    other = collections.defaultdict(dict)    # quantity -> glyph -> (outcome, reason, value)
    for line in open(d + "/verdicts.jsonl"):
        v = json.loads(line)
        q = v["quantity"]
        sub = v["subject"]
        if q == "stroke_owner":
            det = (v.get("detail") or {}).get("strokes") or {}
            for o, e in det.items():
                own[(sub, int(o))] = (e[0], e[1], tuple(e[2]), e[3])
            # strokes not listed are plainly unclaimed (or decided single) -- recorded only through `owned` / `contested`
            for o in (v.get("value") or {}).get("owned") or ():
                own.setdefault((sub, int(o)), ("owned", None, (), ""))
            for o in (v.get("value") or {}).get("contested") or ():
                own.setdefault((sub, int(o)), ("contested", None, (), ""))
        elif q == "notehead_is_not_a_notehead":
            head[sub] = (v["outcome"], v["reason"])
        elif q in ("duration", "head_stem", "stem_value", "accidental_owner", "accidental_is_not_an_accidental", "accidental", "pitch", "stem_direction"):
            val = v["value"]
            if isinstance(val, (dict, list)):
                val = json.dumps(val, sort_keys=True)[:200]
            other[q][sub] = (v["outcome"], v["reason"], val)
    return own, head, other


def boxes(d):
    g = {}
    for line in open(d + "/observations.jsonl"):
        if '"glyph_box"' not in line:
            continue
        o = json.loads(line)
        if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px"):
            g[o["subject"]] = dict(cls=o["value"][0], box=o["detail"]["bbox_page_px"], score=o.get("score"))
    return g


b_own, b_head, b_other = load(base)
a_own, a_head, a_other = load(arm)
G = boxes(base)
rows = []
for k in sorted(set(b_own) | set(a_own)):
    x, y = b_own.get(k), a_own.get(k)
    if (x and x[:2]) != (y and y[:2]):
        rows.append(dict(kind="stroke", cell=k[0], ordinal=k[1], page=int(k[0].split("/")[1]), base=x, arm=y))
for s in sorted(set(b_head) | set(a_head)):
    if b_head.get(s) != a_head.get(s):
        g = G.get(s, {})
        rows.append(dict(kind="head", sub=s, page=int(s.split("/")[1]), base=b_head.get(s), arm=a_head.get(s), cls=g.get("cls"), box=g.get("box"), score=g.get("score")))
for q, m in a_other.items():
    for s, v in m.items():
        bv = b_other[q].get(s)
        if bv != v:
            g = G.get(s, {})
            rows.append(dict(kind="after:" + q, sub=s, page=int(s.split("/")[1]) if s.startswith(("glyph/", "cell/")) else -1, base=bv, arm=v, cls=g.get("cls"), box=g.get("box")))
json.dump(rows, open(out, "w"))
c = collections.Counter(r["kind"] for r in rows)
print(plate, "disagreements between", base, "and", arm)
for k, n in sorted(c.items()):
    print("  %-34s %d" % (k, n))
pp = collections.Counter((r["kind"].split(":")[0], r["page"]) for r in rows)
print("  per kind/page:", dict(sorted(pp.items())))
