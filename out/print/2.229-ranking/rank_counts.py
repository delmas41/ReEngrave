"""2.229: per-kind fix-action counts from an exported arm: report.json (exporter's own accounting) + symbols.json (place-keyed file symbols).
usage: rank_counts.py WORKDIR PLATE ARM COUNTPAGES"""
import json, sys, collections
work, plate, arm, cp = sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4].split(",")]
R = json.load(open("%s/%s.%s.report.json" % (work, plate, arm)))
S = json.load(open("%s/%s.%s.symbols.json" % (work, plate, arm)))
cps = set(cp)
n = len(cp)
out = collections.OrderedDict()
by = collections.defaultdict(lambda: collections.Counter())
for b in R["bars_written_red"]["bars_list"]:
    by["red_bar"][b["page"]] += 1
    by["red_bar_notes"][b["page"]] += b["noteheads_and_rests"]
for b in R["unread_empty_bars"]["list"]:
    by["unread_empty_bar"][b["page"]] += 1
DUR = ("duration_narrowed", "duration_abstained", "chord_value_undecided", "rest_duration_abstained", "rest_duration_narrowed")
for sysk, d in R["notes_not_written_by_system"].items():
    pg = int(sysk.split("/")[0])
    for k, v in d.items():
        if k in DUR: by["dropped_unknown_duration"][pg] += v
        elif k == "no_pitch": by["dropped_no_pitch"][pg] += v
        elif k == "owned_by_another_staff": by["dropped_owned_elsewhere"][pg] += v
        elif k == "unread_gap_in_partial_bar": by["unread_gap"][pg] += v
        elif k.startswith("not_a_notehead") or k.startswith("not_a_rest") or k in ("mark_group_duplicate", "ink_is_a_whole_rest"): by["refused_ink_not_a_symbol"][pg] += v
        else: by["other_" + k][pg] += v
for h in S["hosts"]:
    if h["blue"]:
        by["blue_" + h["kind"]][h["page"]] += 1
    by["written_" + h["kind"]][h["page"]] += 1
rows = {}
for k, c in sorted(by.items()):
    rows[k] = dict(per_page={str(p): c.get(p, 0) for p in sorted(set(cp) | set(c))}, counted_total=sum(c.get(p, 0) for p in cp), counted_per_page=round(sum(c.get(p, 0) for p in cp) / n, 1))
tot = dict(guessed_by_rule=R["guessed"]["by_rule"], accidental_reading=R["accidental_reading"], dot_role_not_placed=R["dot_role_not_placed"],
           fermatas_not_written=R["fermatas_not_written"], arcs_not_written=R["arcs_not_written"], tie_contradictions=len(R.get("tie_contradictions") or []),
           inferred_clefs=len(R.get("inferred_clefs") or []), part_join={k: R["part_join"].get(k) for k in ("unidentified_parts", "held_out_staves")},
           bars_held_out=R["bars_held_out_sum"]["bars"], tacet=R["tacet_padding"]["tacet_bar_total"], decided_and_unwritten=R["decided_and_unwritten"])
print(json.dumps(dict(rows=rows, totals_over_loaded_pages=tot, loaded_pages_note="totals cover ALL loaded pages incl. context page"), indent=1, default=str))
