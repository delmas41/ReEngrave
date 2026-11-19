"""ROADMAP 2.321 small test -- the tally, from measure.py's snapshots (pure; no record loaded).

    python3 benchmarks/voice-line-of-time-2026-11/analyse.py DIR      # reads DIR/litolff.json, DIR/brahms.json; writes DIR/tally.json

(1) the population and the code's own fate per bar: written split by the flag / kept as flag OFF (the code's reason word) / red.
(2) the LOOSER rule, asked of every fallback or red bar, from the record's DECIDED values only (a GUESSED or missing value is not used, it is a cause):
    ONE line of time per staff, at most two players. The marks at one place start together; a later place starts when one player's last mark ends
    (so the line is never broken); one mark alone may belong to either player; two marks at one place need both players free; a player with no mark is
    silent and nothing is printed for it. The bar adds up when some such reading ends exactly at the barline with no player over it. A whole rest beside
    notes is one player's whole bar. NOTHING is invented: no rest, no value. Wrong: a value not read, more than two marks at one place, short, overfull.
    The rule does not look at stem direction (that is the point of asking it); rule C (a head on a dynamic letter / whole-rest box) is a fake-note guard
    and is reported apart.
(3) stem-direction columns: two different decided stems at one place whose directions were READ the same way.
"""
import collections
import json
import sys
from pathlib import Path


def columns(events, factor=1.0):
    """Places, as the code's `_place_columns` groups them: a mark within one head width (x `factor`) of the last mark of a place joins it."""
    ws = [h["w"] for e in events for h in e.get("heads") or () if h.get("w")]
    tol = factor * (sum(ws) / len(ws) if ws else 30.0)
    order = sorted(range(len(events)), key=lambda k: events[k]["x"])
    cols = []
    for k in order:
        if cols and events[k]["x"] - events[cols[-1][-1]]["x"] <= tol:
            cols[-1].append(k)
        else:
            cols.append([k])
    return cols


def line_of_time(row, factor=1.0):
    """('adds_up', n_readings) or (cause word, detail)."""
    ev, want = row["events"], row["want"]
    if want is None:
        return "no_meter", None
    units = []
    for e in ev:
        if e["kind"] == "rest" and (e.get("rest_class") == "restWhole" or e.get("measure_rest")):
            units.append(want if len(ev) > 1 else e["units"])
        else:
            units.append(e["units"])
    if any(u is None for u in units) or not all(e["certain"] for e in ev):
        return "value_not_read", None
    cols = columns(ev, factor)
    if any(len(c) > 2 for c in cols):
        return "three_or_more_marks_at_one_place", max(len(c) for c in cols)
    ends = collections.Counter()
    sols = set()

    def walk(ci, ea, eb, last, trail):
        if ci == len(cols):
            m = max(ea, eb)
            ends["adds" if m == want else ("short" if m < want else "over")] += 1
            if m == want:
                sols.add(trail)
            return
        col = cols[ci]
        cands = {0} if ci == 0 else {ea, eb}
        for t in sorted(cands):
            if t <= last:
                continue
            if len(col) == 1:
                u = units[col[0]]
                for p in (0, 1):
                    e = (ea, eb)[p]
                    if e > t:
                        continue
                    n = t + u
                    if n > want:
                        ends["over"] += 1
                        continue
                    na, nb = (n, eb) if p == 0 else (ea, n)
                    walk(ci + 1, min(na, nb), max(na, nb), t, trail + (t,))
            else:
                if max(ea, eb) > t:
                    continue
                a, b = t + units[col[0]], t + units[col[1]]
                if max(a, b) > want:
                    ends["over"] += 1
                    continue
                walk(ci + 1, min(a, b), max(a, b), t, trail + (t,))

    walk(0, 0, 0, -1, ())
    if sols:
        return "adds_up", len(sols)
    if ends["short"] and not ends["over"]:
        return "short", None
    if ends["over"] and not ends["short"]:
        return "overfull", None
    return "short_or_overfull", dict(ends)


def same_way_columns(row):
    out = []
    for c in row["stem_pair_columns"]:
        a, b = set(c["read_a"]), set(c["read_b"])
        if len(a) == 1 and a == b and "None" not in a:
            out.append(dict(c, way=next(iter(a))))
    return out


def main():
    d = Path(sys.argv[1])
    tally = {}
    for plate in ("litolff", "brahms"):
        p = d / ("%s.json" % plate)
        if not p.exists():
            continue
        f = json.load(open(p))
        rows = f["rows"]
        t = collections.OrderedDict()
        t["population"] = len(rows)
        t["with_stem_pair"] = sum(1 for r in rows if r["stem_pair_columns"])
        t["with_divisi_pair_only"] = sum(1 for r in rows if not r["stem_pair_columns"] and r["divisi_pairs"])
        fate = collections.Counter()
        reasons = collections.Counter()
        for r in rows:
            if r["verdict"] is None:
                k = "written_split" if r["n_streams"] == 2 else "written_one_voice_by_flag"
            else:
                k = "kept_as_flag_off"
                reasons[r["verdict"]] += 1
            fate[k + ("_red" if r["red"] else "")] += 1
        t["fate"] = dict(fate)
        t["fallback_reasons"] = dict(reasons.most_common())
        loose = collections.Counter()
        loose_half = collections.Counter()      # sensitivity: one place = within HALF a head width (heads printed side by side are two moments)
        loose_by_reason = collections.defaultdict(collections.Counter)
        detail = []
        for r in rows:
            if r["verdict"] is None and not r["red"]:
                continue
            res, extra = line_of_time(r)
            res_half, _ = line_of_time(r, 0.5)
            loose_half[res_half] += 1
            cause = res
            if res == "adds_up" and r["unplaced"]:
                cause = "adds_up_but_a_mark_of_the_bar_was_refused"
            if res != "adds_up" and r["unplaced"] and res != "value_not_read":
                cause = res + "+refused_mark"
            loose[cause] += 1
            loose_by_reason[r["verdict"] or ("red_written_split" if r["n_streams"] == 2 else "red_one_voice")][cause] += 1
            detail.append(dict(page=r["page"], system=r["system"], staff=r["staff"], cell=r["cell"], name=r["name"], verdict=r["verdict"], red=r["red"],
                               loose=cause, readings=extra if res == "adds_up" else None,
                               guessed=sum(1 for e in r["events"] if not e["certain"]), no_units=sum(1 for e in r["events"] if e["units"] is None),
                               unplaced=[u["reason"] for u in r["unplaced"]]))
        t["looser_rule_on_fallback_or_red"] = dict(loose.most_common())
        t["looser_rule_half_head_place"] = dict(loose_half.most_common())
        t["looser_rule_by_code_reason"] = {k: dict(v) for k, v in loose_by_reason.items()}
        t["looser_adds_up_readings"] = dict(collections.Counter(min(x["readings"], 3) for x in detail if x["readings"]))
        sw = [(r, c) for r in rows for c in same_way_columns(r)]
        t["stem_pair_columns"] = sum(len(r["stem_pair_columns"]) for r in rows)
        t["same_way_columns"] = len(sw)
        t["same_way_by_way"] = dict(collections.Counter(c["way"] for _, c in sw))
        t["same_way_bars"] = len({(r["page"], r["system"], r["staff"], r["cell"]) for r, _ in sw})
        t["opposite_way_columns"] = sum(1 for r in rows for c in r["stem_pair_columns"]
                                        if {*c["read_a"]} in ({"up"}, {"down"}) and {*c["read_b"]} in ({"up"}, {"down"}) and set(c["read_a"]) != set(c["read_b"]))
        t["unread_way_columns"] = t["stem_pair_columns"] - t["same_way_columns"] - t["opposite_way_columns"]
        tally[plate] = dict(t, detail=detail)
        print("==", plate)
        for k, v in t.items():
            print("  %s: %s" % (k, v))
    json.dump(tally, open(d / "tally.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
