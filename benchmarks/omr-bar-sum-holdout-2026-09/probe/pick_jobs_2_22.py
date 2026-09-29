"""ROADMAP 2.22 -- pick held bars of one CHOSEN class (or `none_of_these`)
for `crop_held_mvt_2_22.py`, spread across the movement (one per page, in
page order, then every k-th), with the record's own reading in the caption:
each voice's events (type, dots, beats, x) and every refusal in the cell.

    python3 .../pick_jobs_2_22.py <held dump> <partition> <class> <jobs out> [n] [name]
"""
import json
import sys


def main():
    dump, part, klass, out = sys.argv[1:5]
    n = int(sys.argv[5]) if len(sys.argv) > 5 else 10
    name = sys.argv[6] if len(sys.argv) > 6 else klass
    d = json.load(open(dump))
    rows = {tuple(r["cell"]): r for r in json.load(open(part))["rows"]}
    want = None if klass == "none_of_these" else klass
    cand = [b for b in d["bars"] if rows.get(tuple(b["cell"]))
            and rows[tuple(b["cell"])]["chosen"] == want]
    by_page = {}
    for b in sorted(cand, key=lambda b: b["cell"]):
        by_page.setdefault(b["cell"][0], []).append(b)
    order = []
    i = 0
    while len(order) < min(n, len(cand)):
        for p in sorted(by_page):
            if i < len(by_page[p]) and len(order) < n:
                order.append(by_page[p][(i * 7 + len(by_page[p]) // 2)
                                        % len(by_page[p])])
        i += 1
    jobs = []
    for b in order:
        r = rows[tuple(b["cell"])]
        voices = []
        subs = []
        for s in b["streams"]:
            voices.append(" ".join(
                f"{e['type'] or e['kind']}{'.' * int(e['dots'] or 0)}"
                f"({e['beats']}@{int(e['x'])})" for e in s))
            subs += [g for e in s for g in e["glyphs"] if g]
        refs = sorted({x["refusal"] for x in b["refused_in_cell"]})
        jobs.append({
            "name": name, "cell": b["cell"], "subjects": subs,
            "measure_in_file": (b.get("report") or {}).get("measure"),
            "part": (b.get("report") or {}).get("part"),
            "judged_quarters": b["detail"]["want_quarters"],
            "voice_sums": r["voice_sums"], "minimal": r["minimal"],
            "says": (f"class {klass}; judged {b['detail']['want_quarters']}q; "
                     f"voice sums {r['voice_sums']}. READ: "
                     + " || ".join(voices)
                     + (f". REFUSED in cell: {', '.join(refs)}" if refs else "")),
        })
    json.dump(jobs, open(out, "w"), indent=1)
    print(f"{len(cand)} bars of class {klass} on {len(by_page)} pages; "
          f"{len(jobs)} jobs")


if __name__ == "__main__":
    main()
