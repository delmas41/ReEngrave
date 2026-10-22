"""2.167e probe 12 (Q3): every dot box (augmentationDot / staccato classes that carry an aug_dot row) at >=0.25 by its standing dot_role verdict;
for dots decided `augmentation`, whether the head they name carries dots>0 in its standing duration verdict. usage: e12_dots.py ALL.json OUT.json"""
import json
import sys
import collections

G = json.load(open(sys.argv[1]))
tab = collections.Counter()
lost = []
by_reason = collections.defaultdict(list)
heads_by_key = {}
for sub, g in G.items():
    parts = sub.split("/")
    heads_by_key[tuple(parts[1:6])] = sub
head_kinds = collections.Counter()
n_aug_attached = 0
n_aug_head_dotless = 0
for sub, g in G.items():
    if "aug_dot" not in g:
        continue
    cls = g.get("cls")
    v = g.get("V", {}).get("dot_role")
    if v is None:
        tab[(cls, "no_verdict", None)] += 1
        continue
    key = (cls, v[0], v[1] if v[0] != "deci" else str(v[2]))
    tab[key] += 1
    by_reason[key].append(sub)
    if v[0] == "deci" and v[2] == "augmentation":
        head = (v[5] or {}).get("head")
        hsub = None
        if head:
            parts = head.split("/") if isinstance(head, str) else [str(x) for x in head]
            if len(parts) >= 6 and parts[0] == "glyph":
                hsub = "/".join(parts[:6])
        if hsub and hsub in G:
            d = G[hsub].get("V", {}).get("duration")
            dots = d[2].get("dots") if d and isinstance(d[2], dict) else None
            kind = "no_duration_verdict" if not d else ("%s:%s" % (d[0], d[1]) if d[0] != "deci" else ("deci_dots%s" % dots))
            head_kinds[kind if not kind.startswith("narr") and not kind.startswith("abst") else kind.split(":")[0]] += 1
            if dots:
                n_aug_attached += 1
            else:
                n_aug_head_dotless += 1
                lost.append(dict(dot=sub, conf=g.get("conf"), head=hsub, head_dur=d, in_cell_red=None))
        else:
            head_kinds["head_not_found:%s" % ("none" if not head else "other")] += 1
print("dot boxes (aug_dot rows) by (class, outcome, reason/value):")
for k, n in sorted(tab.items(), key=lambda t: -t[1]):
    print("  ", n, k)
print("decided augmentation with a named head: head duration has dots>0:", n_aug_attached, " head duration has NO dots:", n_aug_head_dotless)
print("duration verdict of the head a decided-augmentation dot names:", head_kinds.most_common())
print("conf >= 0.25 dot boxes with role abstained/narrowed, class augmentationDot:",
      sum(1 for k, subs in by_reason.items() if k[0] == "augmentationDot" and k[1] != "deci" for s in subs))
json.dump(dict(lost=lost, by_reason={"|".join(map(str, k)): v for k, v in by_reason.items()}), open(sys.argv[2], "w"))
