"""2.204 milestone tiles: 9 CHANGED STEM DECISIONS (3 gained, 2 old_refused, 3 disagree, 1 other change) + 3 controls (2.150 tile 11 and 2.150b tile 20 re-shown,
and one Litolff head the stroke map agreed with and left unchanged). Blind: one neutral orange box, nothing of ours drawn; key outside the folder.
Usage: python3 -m benchmarks.shared-ink-map... no -- run as: python3 benchmarks/shared-ink-map-2026-10/tiles_2_204.py WORK_DIR OUT_DIR [seed]
WORK_DIR holds {litolff,brahms}.{off,on}.gathered.record.json from a lane_report run (the unfrozen subset or the frozen sample)."""
import json, pathlib, random, shutil, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as LR

OLD = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fd65f56a127e4f7/out/print")


def load(p):
    r = json.load(open(p))["record"]
    dur = {v["subject"]: v for v in r["verdicts"] if v["quantity"] == "duration"}
    box = {}
    for o in r["observations"]:
        if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead" and o["detail"].get("bbox_page_px"):
            box[o["subject"]] = o["detail"]["bbox_page_px"]
    return dur, box


def main(work, out, seed=2204):
    work, out = pathlib.Path(work), pathlib.Path(out)
    rng = random.Random(seed)
    pools = {"gained": [], "old_refused": [], "disagree": [], "other": []}
    ctrl = []
    for plate in ("litolff", "brahms"):
        off, _ = load(work / f"{plate}.off.gathered.record.json")
        on, box = load(work / f"{plate}.on.gathered.record.json")
        for s, v in on.items():
            sf = (v.get("detail") or {}).get("stems_from_strokes")
            o = off.get(s)
            if not sf or not o or s not in box:
                continue
            page = int(s.split("/")[1])
            item = dict(plate=plate, page=page, box=box[s], rg=s, kind="note", settled=sf["settled"],
                        was=f"{o['outcome']}:{o['value']}", now=f"{v['outcome']}:{v['value']}:{v['reason']}")
            changed = (o["outcome"], json.dumps(o["value"], sort_keys=True)) != (v["outcome"], json.dumps(v["value"], sort_keys=True))
            if sf["settled"] in ("gained", "old_refused", "disagree") and changed:
                pools[sf["settled"]].append(item)
            elif changed and sf["settled"] in ("agrees", "map_cannot_tell", "map_silent", "no_stem_candidate_only"):
                pools["other"].append(item)
            elif not changed and sf["settled"] == "agrees" and plate == "litolff" and o["outcome"] == "decided":
                ctrl.append(item)
    quota = {"gained": 3, "old_refused": 2, "disagree": 3, "other": 1}
    cases = []
    short = 0
    for k, n in quota.items():
        rng.shuffle(pools[k])
        got = pools[k][:n]
        short += n - len(got)
        cases += [dict(c, role="case", side=k) for c in got]
    # a kind with fewer than its quota is topped up from the other kinds (said in the key)
    rest = [c for k in quota for c in pools[k][quota[k]:]]
    rng.shuffle(rest)
    cases += [dict(c, role="case", side=c["settled"] + "(top-up)") for c in rest[:short]]
    rng.shuffle(ctrl)
    items = cases + [dict(ctrl[0], role="control", side="unchanged")]
    rng.shuffle(items)
    LR.cut_tiles(items, out)
    # the two re-shown tiles: copied as the last two tiles, named in the key (the earlier script drew their orange box the same neutral way)
    key = json.load(open(out / "key.json"))
    for name, src in (("2.150 tile 11", OLD / "2.150-review" / "tile_11.png"), ("2.150b tile 20", OLD / "2.150b-review" / "tile_20.png")):
        n = len(key) + 1
        shutil.copy(src, out / "tiles" / f"tile_{n:02d}.png")
        key.append(dict(tile=n, role="control", side="reshown", source=name))
    json.dump(key, open(out / "key.json", "w"), indent=1, default=str)
    print(json.dumps([{k: v for k, v in x.items() if k in ("tile", "plate", "page", "side", "role", "was", "now", "source")} for x in key], indent=0))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2204)
