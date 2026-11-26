"""Item 2 both sides: at every head read with one stroke up and one down where a partner head stands on one stroke reading it that way, the other
stroke's reach and whether its ink touches the partner's ink. Usage: item2_sides.py DUMPDIR"""
import glob, os, pickle, sys
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS
DD = sys.argv[1]
PS.R25_PARTNER_INK = False
rows = []
for plate in ("litolff", "brahms"):
    for f in sorted(glob.glob(f"{DD}/{plate}/p*.pkl"), key=lambda s: int(s.split("/p")[-1][:-4])):
        D = pickle.load(open(f, "rb"))
        out = PS.read(D["heads"], D["verticals"], D["held"], crossers=D["crossers"], strokes=D["strokes"])
        hink = PS.head_ink(D["heads"], D["strokes"], D["held"])
        tch = PS.touch_map(D["strokes"])
        runs, _ = PS.join_runs(D["verticals"], D["heads"], D["crossers"], D["held"])
        mem = {r["ord"]: r["members"] for r in runs}

        def ti(hid, o):
            mine = hink.get(hid) or set()
            return any(t in mine for m in mem.get(int(o), [int(o)]) for t in tch.get(int(m), ()))
        hb = {h["id"]: h for h in D["heads"]}
        for h in D["heads"]:
            r = out["heads"][h["id"]]
            cs = r.get("candidates") or []
            by = {c["direction"]: c for c in cs}
            if set(by) != {"up", "down"} or len(cs) != 2:
                continue
            mine = hink.get(h["id"]) or set()
            for d, other in (("up", "down"), ("down", "up")):
                s = out["stems"].get(int(by[d]["stroke"]))
                if not s or set(s["directions"]) != {d}:
                    continue
                ps = [k for k in s["heads"] if k != h["id"] and k in hb and not ((hink.get(k) or set()) & mine)]
                if not ps:
                    continue
                o2 = int(by[other]["stroke"])
                cy = (h["box"][1] + h["box"][3]) / 2
                tw = [k for k in ps if ((hb[k]["box"][1] + hb[k]["box"][3]) / 2 > cy) == (other == "down")]
                tp = any(ti(k, o2) for k in tw)
                on2 = (out["stems"].get(o2) or {}).get("heads")
                rows.append((plate, h["members"][0], r["state"], r["how"], r.get("why"), other, by[other].get("reach"), tp, bool(on2)))
for row in sorted(rows, key=lambda r: (r[7], r[6] or 0)):
    print(*row)
