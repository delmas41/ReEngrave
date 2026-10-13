"""Split the `report` out of a run_2_97.py result json (the record in it is GBs).
   python3 report_only_2_97.py RESULT.json REPORT.json"""
import json
import sys

d = json.load(open(sys.argv[1]))
rep = d["report"]
json.dump(rep, open(sys.argv[2], "w"), default=str)
b = rep["bars_held_out_sum"]
print(len(b["held"]), {k: v for k, v in b.items() if k != "held"})
print(rep.get("notes_not_written"), rep.get("written"))
