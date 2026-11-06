"""H2 table: among real arcs with a barline-cut piece (suspected crossing), the stage that lost them, and whether the losing rule is a cell-keyed search.
Cell-keyed losing rules: `tie_pair:no_start_head | no_stop_head | no_head_near_the_arc` (ownership._flank_search: heads of own cell +-1 only) and
`export:arc_binds_fewer_than_two_notes_or_not_in_file` (legacy export._noteheads_under: heads of each segment's own measure; chain joins only if a box
begins at the next cell's left edge). Everything else (not_adjacent, enters_from_previous_system, runs_off, pitch contradiction, head not written ...) is not cell-keyed."""
import collections
import json

CELL_KEYED = ("tie_pair:no_start_head", "tie_pair:no_stop_head", "tie_pair:no_head_near_the_arc", "export:arc_binds_fewer_than_two_notes_or_not_in_file")


def main():
    for plate in ("litolff", "brahms"):
        led = json.load(open("../deep-dive-2026-11/results/%s.base.ledger.json" % plate))["rows"]
        d = json.load(open("results/%s.cut.json" % plate))
        eb = json.load(open("results/edge_is_barline.%s.json" % plate))["edges"]
        rows = {r["key"]: r for r in d["rows"]}

        def cut_bar(r):
            ck = "cell/" + "/".join(r["key"].split("/")[1:5])
            return (r["cut_l"] and eb.get(ck + "|l")) or (r["cut_r"] and eb.get(ck + "|r"))
        stage = collections.Counter()
        cellk = collections.Counter()
        n = 0
        for r in led:
            if r["fate"] == "not_an_arc":
                continue
            ps = [rows[p] for p in r["pieces"] if p in rows]
            if not any(cut_bar(p) for p in ps):
                continue
            n += 1
            if r["fate"] in ("written", "written_as_slur"):
                stage["written"] += 1
                continue
            if r["fate"] in ("wrong_note", "two_arcs"):
                stage[r["fate"] + " (written, to the wrong note / split in two)"] += 1
                continue
            at = r.get("lost_at")
            stage["lost at " + {"K": "ADJUDICATE kind", "P": "ADJUDICATE binding/tie_pair", "X": "EXPORT pairing"}.get(at, str(at))] += 1
            rule = str(r.get("lost_rule"))
            ck = any(rule.startswith(c) for c in CELL_KEYED)
            cellk[(at, "cell-keyed rule" if ck else "other rule")] += 1
        print("==", plate, "cut arcs (printed barline)", n)
        for k, v in stage.most_common():
            print("   %-60s %4d  %.0f%%" % (k, v, 100 * v / n))
        lost = sum(v for k, v in stage.items() if k.startswith("lost"))
        print("   of the %d lost: cell-keyed rule %d, other %d | %s" % (lost, sum(v for (a, k), v in cellk.items() if k == "cell-keyed rule"), sum(v for (a, k), v in cellk.items() if k == "other rule"), dict(cellk)))


main()
