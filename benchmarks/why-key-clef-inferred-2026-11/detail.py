"""One line per filled key staff-system with the evidence that decided its cause.   python3 detail.py X.json [cause-prefix]"""
import json
import sys

d = json.load(open(sys.argv[1]))
want = sys.argv[2] if len(sys.argv) > 2 else ""
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from classify import key_cause, ko_of  # noqa

for k, v in sorted(d["staffs"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
    if not (v["key"] and v["key"][0]["decider"].startswith("infer")):
        continue
    c, info = key_cause(v)
    if want and not c.startswith(want):
        continue
    p = v["key"][-1].get("detail") or {}
    cls = sorted(set(str(m["value"]) for m in v["evidence"].get("keysig_marker", [])))
    ko = ko_of(v) or {}
    print("%-13s %-3s fill %2s | markers %d %s | own_slots %s of sys %s %s | refused=%s | header_ink_slots=%s | clefmeas=%s | read=%s by %s | inst=%s" % (
        k, c[:2], info["fill"], info["markers"], cls, info["own_slots"], info["system_count"], "MORE" if info["more_than_system"] else "",
        p.get("header_ink_refused"), p.get("header_ink_slots"), info["clef_measured"], info["staff_read"], info["read_by"],
        (v["instrument"][0]["detail"] or {}).get("reader_text") if v["instrument"] else None))
