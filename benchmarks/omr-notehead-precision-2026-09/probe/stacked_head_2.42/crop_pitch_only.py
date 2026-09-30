"""Crop groups where a pitch changed but NO member was refused -- the
`glyph/3/0/0/2/4`+`/9` shape (2.42's own second proof case), which the
changed-only crop pass (`crop_groups.py --changed-only`) does not reach
since it filters on a REFUSAL, not a pitch change."""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-notehead-precision-2026-09/probe/stacked_head_2.42")
import crop_groups as CG  # noqa: E402


def main(pdf, base_path, new_path, page, out_dir):
    base = CG.load(base_path)
    new = CG.load(new_path)

    def latest(rec, q):
        out = {}
        for v in rec.get("verdicts", []):
            if v["quantity"] == q:
                out[v["subject"]] = v
        return out

    bp = latest(base, "pitch")
    npz = latest(new, "pitch")
    changed = {s for s in (set(bp) & set(npz)) if bp[s]["value"] != npz[s]["value"]}
    print("changed pitch subjects:", len(changed))

    groups = CG.build_groups(new)
    refused = {s: v for s, v in latest(new, "notehead_is_not_a_notehead").items()
              if v["reason"] == "stacked_head_duplicate"}
    pitch_only_groups = []
    for key, members in groups.items():
        subs = {m["subject"] for m in members}
        if subs & changed and not (subs & set(refused)):
            pitch_only_groups.append(key)
    print("pitch-changed-but-not-refused groups:", len(pitch_only_groups))

    cache = CG.PageRenderCache(pdf)
    outp = Path(out_dir)
    manifest = []
    for i, key in enumerate(pitch_only_groups):
        cell_key, stem_id, side = key
        tag = f"P{i+1:02d}-{cell_key.replace('/', '-')}-{side}"
        result = CG.crop_group(new, cache, page, cell_key, groups[key],
                               refused, outp / f"{tag}.png", tag)
        if result:
            manifest.append(result)
            print(tag, result["legend"])
    outp.mkdir(parents=True, exist_ok=True)
    with open(outp / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=1, default=str)
    print(len(manifest), "crops written")


if __name__ == "__main__":
    a = sys.argv[1:6]
    main(a[0], a[1], a[2], int(a[3]), a[4])
