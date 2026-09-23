"""base vs arm, one tree, one record per document: what ROADMAP 2.8 cost."""
import json, sys, xml.etree.ElementTree as ET

def load(p): return json.load(open(p))

def notes(x):
    return len(ET.parse(x).getroot().findall(".//note"))

for doc in sys.argv[1:]:
    O = "benchmarks/omr-bar-sum-holdout-2026-09/out/"
    b, a = load(O + "base-%s.report.json" % doc), load(O + "arm-%s.report.json" % doc)
    held = a["bars_held_out_sum"]
    print("\n=== %s ===" % doc)
    print("  staff-bars with events        %d" % held["of_bars_with_events"])
    print("  ... without a meter (unassessable) %d" % held["bars_with_events_without_a_meter"])
    print("  bars HELD OUT by 2.8          %d  (%.1f%%)  [%d on a doubled staff]"
          % (held["bars"], 100.0 * (held["fraction"] or 0), held["bars_on_a_doubled_staff"]))
    print("  noteheads+rests moved         %d" % held["noteheads_and_rests"])
    print("  bar_does_not_add_up           %d" % a["notes_not_written"].get("bar_does_not_add_up", 0))
    print("  <note> base -> arm            %d -> %d" % (notes(O+"base-%s.musicxml"%doc), notes(O+"arm-%s.musicxml"%doc)))
    print("  written.notes  base -> arm    %d -> %d" % (b["written"].get("notes",0), a["written"].get("notes",0)))
    print("  written.rests  base -> arm    %d -> %d" % (b["written"].get("rests",0), a["written"].get("rests",0)))
    print("  measure_rests_read base->arm  %d -> %d" % (b["written"].get("measure_rests_read",0), a["written"].get("measure_rests_read",0)))
    print("  empty_bars_padded base->arm   %d -> %d" % (b["written"].get("empty_bars_padded",0), a["written"].get("empty_bars_padded",0)))
    print("  balance balanced base/arm     %s / %s" % (b["balance"]["balanced"], a["balance"]["balanced"]))
    print("  events in log / written / not %d / %d / %d"
          % (a["balance"]["events_in_log"], a["balance"]["events_written"], a["balance"]["events_not_written"]))
    print("  census unaccounted            %r" % (a["status_census"]["unaccounted"],))
    for k in ("articulation_balance","ornament_balance","wedge_balance","fermata_balance","direction_balance"):
        print("  %-22s base=%s arm=%s" % (k, b[k]["balanced"], a[k]["balanced"]))
    print("  notes_not_written base: %s" % b["notes_not_written"])
    print("  notes_not_written arm : %s" % a["notes_not_written"])
    print("  arcs_not_written arm  : %s" % a["arcs_not_written"])
