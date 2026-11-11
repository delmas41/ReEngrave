import json
import sys

for k in json.load(open(sys.argv[1])):
    print(k["tile"], k["plate"], "p%s s%s st%s c%s" % (k["page"], k["system"], k["staff"], k["cell"]), k["our_family"], k["want_quarters"], k["counted_quarters_per_voice"], k["our_events_in_order"])
