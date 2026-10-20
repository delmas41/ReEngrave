"""2.167e probe 10: from 2.167d's labelled lost items (90 held bars, my look, not evidence): the lost eighth rests and the lost augmentation dots by stage."""
import json
import collections

for pl in ("lit", "bra"):
    d = json.load(open("probe/2.167d/data/%s_items_analysed.json" % pl))
    its = d["items"] if "items" in d else list(d.values())[0]
    print("==", pl, "items", len(its), "keys", list(d.keys()))
    kinds = collections.Counter(i["kind"] for i in its)
    print(kinds)
    for tag, test in (("rest", lambda i: i["kind"] == "missing_rest"),
                      ("dot", lambda i: "dot" in i["what"].lower() and i["kind"] != "extra"),
                      ("flag", lambda i: "flag" in i["what"].lower() and i["kind"] != "extra")):
        sel = [i for i in its if test(i)]
        print(tag, len(sel), "bars", len({i["key"] for i in sel}))
        for i in sel:
            print("   ", i["bar"], i["key"], i["sure"], i["stage"][:70], "|", i["what"][:90])
