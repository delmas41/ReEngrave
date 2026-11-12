"""2.300 compare two dump_events.py outputs (flag OFF vs ON, same pages, same stages).
    python3 benchmarks/one-chord-one-event-2026-11/compare.py OFF.json ON.json [OUT.json]
Prints, per plate: red bars before/after and the notes inside them; bars that stopped being red; bars that BECAME red or
partial; every note (glyph) present OFF and absent ON, present ON and absent OFF; every value that changed; every bar whose
event grouping changed (chords formed).
"""
import json
import sys


def heads(bar):
    out = {}
    for ei, e in enumerate(bar["events"]):
        for h in e["heads"]:
            out[h["glyph"]] = {"beats": h["beats"], "type": h["type"], "pitch": h["pitch"], "ev": ei, "n_in_event": len(e["heads"]),
                               "ev_beats": e["beats"], "status": h.get("status"), "page_box": h.get("page_box")}
    return out


def status(b):
    return "red" if b["red"] else "partial" if b["partial"] else "plain"


def main():
    off = json.load(open(sys.argv[1]))
    on = json.load(open(sys.argv[2]))
    assert off["plate"] == on["plate"] and off["pages"] == on["pages"], "same plate and pages"
    ob = {tuple(b["key"]): b for b in off["bars"]}
    nb = {tuple(b["key"]): b for b in on["bars"]}
    res = {"plate": off["plate"], "pages": off["pages"], "bars": len(ob), "bars_on": len(nb), "_off_path": sys.argv[1], "_on_path": sys.argv[2]}
    stat = {"off": {"red": 0, "partial": 0, "red_notes": 0}, "on": {"red": 0, "partial": 0, "red_notes": 0}}
    stopped, became_red, became_partial, partial_to_plain, chords_formed = [], [], [], [], []
    lost, gained, changed = [], [], []
    for k in sorted(set(ob) | set(nb)):
        a, b = ob.get(k), nb.get(k)
        for arm, bar in (("off", a), ("on", b)):
            if bar is None:
                continue
            if bar["red"]:
                stat[arm]["red"] += 1
                stat[arm]["red_notes"] += sum(len(e["heads"]) for e in bar["events"])
            elif bar["partial"]:
                stat[arm]["partial"] += 1
        if a is None or b is None:
            continue
        sa, sb = status(a), status(b)
        if sa == "red" and sb != "red":
            stopped.append((list(k), sa, sb))
        if sa != "red" and sb == "red":
            became_red.append((list(k), sa, sb))
        if sa == "plain" and sb == "partial":
            became_partial.append((list(k), sa, sb))
        if sa == "partial" and sb == "plain":
            partial_to_plain.append((list(k), sa, sb))
        ha, hb = heads(a), heads(b)
        for g in sorted(set(ha) - set(hb)):
            lost.append({"key": list(k), "glyph": g, **ha[g]})
        for g in sorted(set(hb) - set(ha)):
            gained.append({"key": list(k), "glyph": g, **hb[g]})
        for g in sorted(set(ha) & set(hb)):
            if ha[g]["beats"] != hb[g]["beats"] or ha[g]["type"] != hb[g]["type"]:
                changed.append({"key": list(k), "glyph": g, "off": [ha[g]["beats"], ha[g]["type"]], "on": [hb[g]["beats"], hb[g]["type"]],
                                "page_box": ha[g]["page_box"]})
        if [len(e["heads"]) for e in a["events"]] != [len(e["heads"]) for e in b["events"]]:
            chords_formed.append({"key": list(k), "off": [[e["kind"], len(e["heads"]), e["beats"]] for e in a["events"]],
                                  "on": [[e["kind"], len(e["heads"]), e["beats"]] for e in b["events"]],
                                  "status": [sa, sb]})
    res.update({"red_bars_off_on": [stat["off"]["red"], stat["on"]["red"]], "red_bar_notes_off_on": [stat["off"]["red_notes"], stat["on"]["red_notes"]],
                "partial_off_on": [stat["off"]["partial"], stat["on"]["partial"]],
                "stopped_being_red": stopped, "became_red": became_red, "became_partial": became_partial, "partial_to_plain": partial_to_plain,
                "notes_present_off_absent_on": lost, "notes_present_on_absent_off": gained, "values_changed": changed,
                "bars_whose_events_changed": chords_formed})
    print("%s pages %s: red %s -> %s; notes inside red bars %s -> %s; partial %s -> %s" % (
        res["plate"], res["pages"], *res["red_bars_off_on"], *res["red_bar_notes_off_on"], *res["partial_off_on"]))
    print("  stopped being red %d | became red %d | became partial %d | partial->plain %d" % (len(stopped), len(became_red), len(became_partial), len(partial_to_plain)))
    print("  notes present OFF absent ON: %d | present ON absent OFF: %d | values changed: %d | bars whose events changed: %d" % (
        len(lost), len(gained), len(changed), len(chords_formed)))
    for x in lost:
        print("   LOST", x["key"], x["glyph"], x["pitch"], x["type"], x["page_box"])
    for x in gained:
        print("   GAINED", x["key"], x["glyph"], x["pitch"], x["type"], x["page_box"])
    for x in changed:
        print("   VALUE", x["key"], x["glyph"], x["off"], "->", x["on"], x["page_box"])
    for x in became_red + became_partial:
        print("   BECAME", x)
    if len(sys.argv) > 3:
        json.dump(res, open(sys.argv[3], "w"), default=str)


main()
