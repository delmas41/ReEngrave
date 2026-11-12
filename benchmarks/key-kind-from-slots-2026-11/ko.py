"""Print the key_object / marker evidence behind every FILLED key.   python3 ko.py X.json"""
import json
import sys

d = json.load(open(sys.argv[1]))
for k, v in sorted(d["staffs"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
    if not v["key"][0]["decider"].startswith("infer"):
        continue
    rows = v["evidence"].get("claimed_area", [])
    found = False
    for r in rows:
        dt = r["detail"]
        if isinstance(dt, dict) and dt.get("key_object"):
            ko = dt["key_object"]
            print(k, "KEY_OBJECT", {x: ko.get(x) for x in ko if x not in ("read_pieces", "pieces")}, "pieces", [(p.get("src"), p.get("fill")) for p in (ko.get("read_pieces") or [])])
            found = True
            break
        elif isinstance(dt, str) and "key_object" in dt:
            print(k, "KEY_OBJECT(trunc)", dt[:700])
            found = True
            break
    if not found:
        print(k, "no key_object row;", [(r["reader"], str(r["detail"])[:60]) for r in rows][:3])
    kp = v["key"][-1].get("detail") or {}
    print("      markers:", len(v["evidence"].get("keysig_marker", [])), "refused:", kp.get("header_ink_refused"), "cv_header/template fits:",
          [(r["reader"], r["value"]) for r in v["evidence"].get("keysig_clef_fit", []) + v["evidence"].get("keysig_template_fit", [])])
