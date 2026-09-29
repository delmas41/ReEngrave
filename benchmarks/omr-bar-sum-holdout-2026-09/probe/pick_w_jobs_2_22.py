"""ROADMAP 2.22 -- pick the crops for the Brahms `W` question.

`W` bars (a lone, unmarked, dotless whole rest -- 2.8 holds it because the
bar sums 4.0 against the file's 6/8) whose system's `Q.METER` ABSTAINS, with
nothing refused in the cell, spread one per page across the movement, first
by page then by system. Writes a jobs file for `crop_held_mvt_2_22.py`.

    python3 .../pick_w_jobs_2_22.py <held dump> <partition> <jobs out> [n]
"""
import json
import sys


def main():
    dump, part, out = sys.argv[1:4]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    d = json.load(open(dump))
    rows = {tuple(r["cell"]): r for r in json.load(open(part))["rows"]}
    cand = []
    for b in d["bars"]:
        r = rows.get(tuple(b["cell"]))
        sm = b.get("system_meter") or {}
        if not r or r["chosen"] != "W" or sm.get("outcome") == "decided":
            continue
        if b["refused_in_cell"] or b["n_streams"] != 1:
            continue
        cand.append((b, sm))
    by_page = {}
    for b, sm in sorted(cand, key=lambda t: t[0]["cell"]):
        by_page.setdefault(b["cell"][0], []).append((b, sm))
    pages = sorted(by_page)
    step = max(1, len(pages) // n)
    jobs = []
    for p in pages[::step][:n]:
        b, sm = by_page[p][len(by_page[p]) // 2]
        e = b["streams"][0][0]
        jobs.append({
            "name": "W-meter-abstains",
            "cell": b["cell"],
            "subjects": e["glyphs"],
            "measure_in_file": (b.get("report") or {}).get("measure"),
            "part": (b.get("report") or {}).get("part"),
            "system_meter": [sm.get("outcome"), sm.get("reason")],
            "says": (f"One {e['classes'][0]} (read {e['beats']}q), nothing else "
                     f"in the bar. Q.METER on this system ABSTAINS "
                     f"({sm.get('reason')}); the FILE writes 6/8 here anyway, "
                     f"so 2.8 sums 4.0 against 3.0 and HOLDS the bar. "
                     f"size_measure_rest needs a DECIDED meter to mark it."),
        })
    json.dump(jobs, open(out, "w"), indent=1)
    print(f"{len(cand)} candidates on {len(pages)} pages; {len(jobs)} jobs")


if __name__ == "__main__":
    main()
