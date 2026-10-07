"""night 2026-10-07: noteheads written 2+ times / written nowhere, per PHYSICAL MARK (boxes of one page+system whose IoU > 0.3
are one mark, the gather's own rule), from `mark_identity_relocate_eval.py --fates` (per-glyph fate with the relocation /
mark-group flags' export OFF vs ON, on the rebuilt record).  Marks whose every box was refused as not a notehead are counted
separately (nothing was lost there: the ink is not a head).

  python3 night_1007_marks.py <fates.json> <x7 extract json>
"""
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import night_1007_report as NR


def main(fates, ext):
    F = json.loads(Path(fates).read_text())
    N = json.loads(Path(ext).read_text())
    items = [(s, b) for s, c, b in N["boxes"] if str(c).startswith("notehead")]
    by = collections.defaultdict(list)
    for s, b in items:
        by[tuple(s.split("/")[1:3])].append((s, b))
    marks = []
    for L in by.values():
        par = list(range(len(L)))

        def f(i):
            while par[i] != i:
                par[i] = par[par[i]]
                i = par[i]
            return i
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                if NR.R.iou(L[i][1], L[j][1]) > 0.3:
                    par[f(i)] = f(j)
        g = collections.defaultdict(list)
        for i in range(len(L)):
            g[f(i)].append(L[i][0])
        marks += list(g.values())
    out = {}
    for mode in ("off", "on"):
        fa = F[mode]
        c = collections.Counter()
        reasons = collections.Counter()
        for m in marks:
            fs = [fa.get(s) for s in m]
            w = sum(1 for x in fs if x and x.startswith("written"))
            if w >= 2:
                c["written_2plus"] += 1
            elif w == 1:
                c["written_once"] += 1
            else:
                nat = all(x and x.startswith("not_a_notehead") for x in fs)
                c["not_a_head_only" if nat else "written_nowhere_real"] += 1
                if not nat:
                    reasons[max(set(map(str, fs)), key=lambda z: list(map(str, fs)).count(z))] += 1
        c["marks"] = len(marks)
        out[mode] = dict(c, top_reasons_nowhere=dict(reasons.most_common(8)))
        print(mode, out[mode])
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
