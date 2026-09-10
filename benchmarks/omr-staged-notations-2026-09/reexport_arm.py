import json, sys
from tools.omr.staged import export as SX
res = json.load(open(sys.argv[1]))
xml, rep = SX.to_musicxml(res)
open(sys.argv[2], "w").write(xml)
w = rep["written"]
print("  dynamics=%s notes=%s rests=%s balanced=%s"
      % (w.get("dynamics", 0), w["notes"], w["rests"], rep["balance"]["balanced"]))
print("  <dynamics> in file: %s" % xml.count("<dynamics>"))
print("  headline 1 record-gap : %s %s" % (rep["detected_and_unrepresented_total"],
                                           rep["detected_and_unrepresented"]))
print("  headline 2 export-gap : %s %s" % (rep.get("decided_and_unwritten_total"),
                                           rep.get("decided_and_unwritten")))
