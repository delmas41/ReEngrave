"""Page/system/cell layout from the shared cell maps: cumulative bar numbers per system (from detected barlines)."""
import gzip, json, sys, glob, os

CM = {"litolff": "library/_shared-records/cell-maps/55d95838e0709b92-dpi600",
      "brahms": "library/_shared-records/cell-maps/be40c09fbd9f55f0-dpi600"}


def layout(plate):
    out = []
    for f in sorted(glob.glob(os.path.join(CM[plate], "pages", "p*.json.gz"))):
        d = json.load(gzip.open(f))
        pg = d["page_index"]
        systems = {}
        for c in d["cells"]:
            v = c["v"]
            s = systems.setdefault(v["system_index"], {"staves": set(), "cells": set()})
            s["staves"].add(v["staff_index"])
            s["cells"].add(v["measure_index"])
        for si in sorted(systems):
            s = systems[si]
            out.append((pg, si, len(s["staves"]), len(s["cells"])))
    return out


if __name__ == "__main__":
    plate = sys.argv[1]
    bar = 1
    for pg, si, nst, nc in layout(plate):
        print(f"p{pg} s{si} staves={nst} cells={nc} bars {bar}-{bar + nc - 1}")
        bar += nc
