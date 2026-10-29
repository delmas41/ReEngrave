"""First-pass classes for every red bar, from the record's own marks (OURS, not the print). usage: classify.py PLATE FEAT.json OUT.json"""
import json, sys, collections, itertools
plate, fp, outp = sys.argv[1:4]
U = {"litolff": 15.5, "brahms": 15.5}
bars = json.load(open(fp))
STD = [0.25, 0.375, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8]


def events(b):
    """group rows into onset events by page x (chord = one event). returns [(x, beats, [rows])]"""
    rows = sorted(b["rows"], key=lambda r: (r["xc"] if r["xc"] is not None else 1e9))
    ev = []
    for r in rows:
        if ev and r["xc"] is not None and ev[-1][0] is not None and abs(r["xc"] - ev[-1][0]) < 0.8 * 15.5 and r["kind"] == "note" and ev[-1][2][-1]["kind"] == "note":
            ev[-1][2].append(r)
        else:
            ev.append([r["xc"], r["beats"], [r]])
    return ev


def classify(b):
    want, cnt = b["want"], max(b["counted"])
    diff = round(cnt - want, 4)
    rows = b["rows"]
    c = dict(key=b["key"], page=b["page"], over=diff > 0, diff=diff, want=want, counted=b["counted"], two_voice=b["two_voice"], doubled=b["doubled"], n_rows=len(rows))
    rests = [r for r in rows if r["kind"] == "rest"]
    wholerest = [r for r in rests if r.get("measure_rest") or r.get("cls") == "restWhole" or (r["beats"] or 0) >= want - 1e-6]
    c["whole_rest_in_bar"] = bool(wholerest)
    evs = events(b)
    c["n_events"] = len(evs)
    # one extra event: removing it fixes
    ex = []
    for i, e in enumerate(evs):
        if abs(sum(x[1] or 0 for j, x in enumerate(evs) if j != i) - want) < 1e-6:
            ex.append(i)
    c["remove_one_fixes"] = [(evs[i][2][0]["cls"], evs[i][2][0]["glyph"], evs[i][1]) for i in ex]
    # one value change fixes
    ch = []
    for i, e in enumerate(evs):
        need = round(want - sum(x[1] or 0 for j, x in enumerate(evs) if j != i), 4)
        if need > 0 and any(abs(need - s) < 1e-6 for s in STD) and abs(need - (e[1] or 0)) > 1e-6:
            ch.append((evs[i][2][0]["cls"], evs[i][2][0]["glyph"], evs[i][1], need))
    c["one_value_fixes"] = ch
    # missing symbol (short): gap is a standard value
    if diff < 0:
        gap = round(-diff, 4)
        c["gap"] = gap
        c["gap_std"] = any(abs(gap - s) < 1e-6 for s in STD)
    # other staves in the cell
    c["others_red"] = b["others_red"]
    c["n_staves"] = b["n_staves"]
    c["same_cell_other_red_n"] = len(b["others_red"])
    c["meter_reason"] = (b["meter"] or {}).get("reason")
    c["why"] = b["why"]
    c["fates"] = [f for f in b["fates"] if f[2] not in ("written", "written_relocated")]
    c["fate_reasons"] = sorted({f[2] for f in c["fates"]})
    c["classes"] = collections.Counter(r["cls"] for r in rows)
    return c


res = [classify(b) for b in bars]
json.dump(res, open(outp, "w"), default=str)
n = len(res)
print(plate, n)
over = [c for c in res if c["over"]]; short = [c for c in res if not c["over"]]
print("over", len(over), "short", len(short))
print("two_voice", sum(c["two_voice"] for c in res), "doubled copy", sum(c["doubled"] for c in res))
print("whole rest in bar: over", sum(c["whole_rest_in_bar"] for c in over), "short", sum(c["whole_rest_in_bar"] for c in short))
print("over: remove-one fixes", sum(bool(c["remove_one_fixes"]) for c in over), "value-change fixes", sum(bool(c["one_value_fixes"]) for c in over))
print("short: gap std", sum(c.get("gap_std", False) for c in short))
print("diff over", collections.Counter(c["diff"] for c in over).most_common(10))
print("diff short", collections.Counter(c["diff"] for c in short).most_common(10))
print("n_events over", collections.Counter(c["n_events"] for c in over).most_common(8))
print("n_events short", collections.Counter(c["n_events"] for c in short).most_common(8))
print("meter reason", collections.Counter(c["meter_reason"] for c in res))
print("same-cell other staves red: over", collections.Counter(min(c["same_cell_other_red_n"], 5) for c in over), "short", collections.Counter(min(c["same_cell_other_red_n"], 5) for c in short))
print("want", collections.Counter(c["want"] for c in res))
print("fate reasons over", collections.Counter(r for c in over for r in c["fate_reasons"]).most_common(8))
print("fate reasons short", collections.Counter(r for c in short for r in c["fate_reasons"]).most_common(8))
print("classes over", collections.Counter(k for c in over for k in c["classes"]).most_common(12))
print("classes short", collections.Counter(k for c in short for k in c["classes"]).most_common(12))
print("why", collections.Counter((c["over"], c["why"]) for c in res))
