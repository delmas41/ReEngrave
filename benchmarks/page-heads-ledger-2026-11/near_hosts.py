"""ROADMAP 2.290 build -- for each listed glyph written OFF: every host both arms wrote in the same cell within 40 px (READ-ONLY).

    python3 benchmarks/page-heads-ledger-2026-11/near_hosts.py WORKDIR PLATE GLYPH [GLYPH ...]
"""
import json
import sys


def main(w, plate, rgs):
    s = {a: json.load(open("%s/%s.%s.symbols.json" % (w, plate, a)))["hosts"] for a in ("off", "on")}
    for rg in rgs:
        hs = [x for x in s["off"] + s["on"] if x.get("rg") == rg]
        if not hs:
            print(rg, "not written in either arm")
            continue
        h = hs[0]
        cell = "/".join(rg.split("/")[1:5])
        print(rg, h["kind"], h["type"], h["pitch"], [round(v) for v in h["box"]], "onset", h["onset"], "voice", h["voice"], "chord", h["chord"])
        for arm in ("off", "on"):
            near = [x for x in s[arm] if x.get("rg") and "/".join(x["rg"].split("/")[1:5]) == cell and abs(x["cx"] - h["cx"]) < 40]
            print("   ", arm, [(x["rg"].split("/")[-1], x["kind"], x["type"], x["pitch"], round(x["cx"]), round(x["cy"]), x["onset"], x["voice"], x["chord"])
                               for x in near])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
