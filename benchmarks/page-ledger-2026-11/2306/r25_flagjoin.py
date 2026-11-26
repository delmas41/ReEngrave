"""Item 1 check (r23 dumps = the reader's real inputs): at the six shared heads, does the up stroke's ink below the head touch a non-vertical
piece that the down stroke also touches (the lower voice's flag)? And at every OTHER head read `one_stem_passes_the_head`, the same question."""
import glob, os, pickle, sys
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS
DD = "/private/tmp/claude-501/lane-2.306-r23/dump"
SIX = {"glyph/4/1/0/14/2", "glyph/8/1/1/18/9", "glyph/8/1/4/14/5", "glyph/9/0/4/1/4", "glyph/0/0/11/1/13", "glyph/5/1/5/5/4"}
for plate in ("litolff", "brahms"):
    for f in sorted(glob.glob(f"{DD}/{plate}/p*.pkl")):
        D = pickle.load(open(f, "rb"))
        out = PS.read(D["heads"], D["verticals"], D["held"], crossers=D["crossers"], strokes=D["strokes"])
        runs, _ = PS.join_runs(D["verticals"], D["heads"], D["crossers"], D["held"])
        mem = {r["ord"]: r["members"] for r in runs}
        S = D["strokes"]
        for h in D["heads"]:
            r = out["heads"][h["id"]]
            if r.get("why") != "one_stem_passes_the_head" and not (set(h["members"]) & SIX):
                continue
            by = {c["direction"]: c for c in r.get("candidates") or ()}
            if set(by) != {"up", "down"}:
                print(plate, h["members"][0], r["how"], r.get("why"), "no up/down pair"); continue
            up, dn = int(by["up"]["stroke"]), int(by["down"]["stroke"])
            bot = h["box"][3]
            def tch(o):
                return {j for m in mem.get(o, [o]) for j, _c in S[m]["touches"]}
            shared = [j for j in tch(up) & tch(dn) if S[j]["kind"] != "vertical" and S[j]["box"][1] >= bot - 2]
            print(plate, h["members"][0], "SIX" if set(h["members"]) & SIX else "   ", r.get("why"), "up", up, mem.get(up, [up]), "dn", dn,
                  "flag-like pieces both touch below the head:", [(j, S[j]["kind"], [round(v) for v in S[j]["box"]]) for j in shared])
