"""2.240 step 3: the notes / rests one arm wrote and the other did not (by glyph key), with both arms' glyph_owner verdict.

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-10/s4/lost_hosts.py LANE_REPORT_DIR PLATE OV_OFF.json OV_ON.json
"""
import json
import pathlib
import sys

from tools.omr.staged.judged import iter_array


def main():
    d, plate, ov_off, ov_on = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
    hosts = {}
    for arm in ("off", "on"):
        sym = json.loads((d / "work" / ("%s.%s.symbols.json" % (plate, arm))).read_text())
        hosts[arm] = {(h.get("rg"), h.get("kind")): h for h in sym["hosts"] if h.get("kind") in ("note", "rest")}
    own = {}
    for arm, path in (("off", ov_off), ("on", ov_on)):
        own[arm] = {v["subject"]: (v.get("outcome"), v.get("value"), v.get("reason"), (v.get("detail") or {}).get("page_owner"))
                    for v in iter_array(pathlib.Path(path), "verdicts") if v.get("quantity") == "glyph_owner"}
    for a, b, word in (("off", "on", "LOST"), ("on", "off", "GAINED")):
        for k, h in sorted(hosts[a].items(), key=lambda t: str(t[0])):
            if k not in hosts[b]:
                rg = k[0]
                print(word, k[1], rg, h.get("pitch"), h.get("type"), "| owner OFF", own["off"].get(rg), "| ON", own["on"].get(rg))


if __name__ == "__main__":
    main()
