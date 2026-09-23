"""Render funnel.json + neighbours.json as the markdown tables in FINDINGS.md.

Written so no number in FINDINGS.md is typed by hand.
"""
from __future__ import annotations
import argparse, collections, json
from pathlib import Path

NAMES = {0: "Flauti", 1: "Oboi", 2: "Clarinetti", 3: "Fagotti", 4: "Corni",
         5: "Trombe", 6: "Timpani", 7: "Violino I", 8: "Violino II",
         9: "Viola", 10: "Vc e Basso"}
NAMES2 = {0: "Flauti", 1: "Clarinetti", 2: "Fagotti", 3: "Corni",
          4: "Violino I", 5: "Violino II", 6: "Viola", 7: "Vc e Basso"}

BUCKETS = ["not_a_notehead:too_narrow", "not_a_notehead:clipped_fragment",
           "ink_is_a_whole_rest", "no_pitch", "duration_narrowed",
           "owned_by_another_staff", "staff_not_identified"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--funnel", required=True)
    ap.add_argument("--first-printed-bar", type=int, default=49)
    a = ap.parse_args()
    F = json.loads(Path(a.funnel).read_text())
    ref = {int(k): v for k, v in F["reference"]["heads"].items()}

    print("### Table 1 — Viola, `staff/3/0/9`, printed bars 49-64\n")
    cols = ["bar", "ref heads", "ink comps", "all boxes", "notehead boxes"] \
        + ["R:" + b.replace("not_a_notehead:", "") for b in BUCKETS] \
        + ["no verdict", "WRITTEN"]
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    tot = collections.Counter()
    for ci in sorted(F["subject_funnel"], key=int):
        r = F["subject_funnel"][ci]
        bar = a.first_printed_bar + int(ci)
        row = [str(bar), str(ref.get(bar, "-")), str(r.get("ink_components", 0)),
               str(r.get("boxes_all", 0)), str(r.get("boxes_notehead", 0))]
        for b in BUCKETS:
            row.append(str(r.get("refused:" + b, 0)))
        row += [str(r.get("no_notehead_class", 0)), str(r.get("written", 0))]
        print("| " + " | ".join(row) + " |")
        tot["ref"] += ref.get(bar, 0)
        for k in ("ink_components", "boxes_all", "boxes_notehead",
                  "no_notehead_class", "written"):
            tot[k] += r.get(k, 0)
        for b in BUCKETS:
            tot[b] += r.get("refused:" + b, 0)
    row = ["**total**", f"**{tot['ref']}**", f"**{tot['ink_components']}**",
           f"**{tot['boxes_all']}**", f"**{tot['boxes_notehead']}**"] \
        + [f"**{tot[b]}**" for b in BUCKETS] \
        + [f"**{tot['no_notehead_class']}**", f"**{tot['written']}**"]
    print("| " + " | ".join(row) + " |")
    bal = (tot["boxes_notehead"] == tot["written"] + sum(tot[b] for b in BUCKETS)
           + tot["no_notehead_class"])
    print(f"\nBalance: notehead boxes {tot['boxes_notehead']} = written "
          f"{tot['written']} + refused {sum(tot[b] for b in BUCKETS)} + "
          f"no verdict {tot['no_notehead_class']} -> **{bal}**\n")

    print("\n### Table 2 — every staff on pdf page 3\n")
    cols2 = ["staff", "part as printed", "clef", "ink comps", "notehead boxes"] \
        + ["R:" + b.replace("not_a_notehead:", "") for b in BUCKETS] \
        + ["WRITTEN"]
    print("| " + " | ".join(cols2) + " |")
    print("|" + "---|" * len(cols2))
    grand = collections.Counter()
    sysfoot = {}
    for key in sorted(F["page_funnel"], key=lambda k: [int(x) for x in k.split("/")]):
        p, sy, st = (int(x) for x in key.split("/"))
        agg = collections.Counter()
        for c in F["page_funnel"][key].values():
            for k, v in c.items():
                agg[k] += v
        ident = F["identity"].get(key, {}).get("clef", {})
        clef = ident.get("value") if ident.get("outcome") == "decided" \
            else f"ABSTAINED ({ident.get('reason')})"
        nm = (NAMES if sy == 0 else NAMES2).get(st, "?")
        row = [f"3/{sy}/{st}", nm, str(clef), str(agg["ink_components"]),
               str(agg["boxes_notehead"])]
        row += [str(agg["refused:" + b]) for b in BUCKETS]
        row.append(str(agg["written"]))
        print("| " + " | ".join(row) + " |")
        for k in ("ink_components", "boxes_notehead", "written"):
            grand[k] += agg[k]
            sysfoot.setdefault(sy, collections.Counter())[k] += agg[k]
        for b in BUCKETS:
            grand[b] += agg["refused:" + b]
            sysfoot[sy][b] += agg["refused:" + b]
    for sy in sorted(sysfoot):
        t = sysfoot[sy]
        print("| **system " + str(sy) + "** | | | " +
              f"**{t['ink_components']}** | **{t['boxes_notehead']}** | " +
              " | ".join(f"**{t[b]}**" for b in BUCKETS) +
              f" | **{t['written']}** |")
    print("| **PAGE** | | | " + f"**{grand['ink_components']}** | "
          f"**{grand['boxes_notehead']}** | " +
          " | ".join(f"**{grand[b]}**" for b in BUCKETS) +
          f" | **{grand['written']}** |")
    r = sum(grand[b] for b in BUCKETS)
    print(f"\nBalance: page notehead boxes {grand['boxes_notehead']} = written "
          f"{grand['written']} + refused {r} -> "
          f"**{grand['boxes_notehead'] == grand['written'] + r}**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
