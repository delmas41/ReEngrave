"""ROADMAP 2.253 step 0: how often do the five page-wide kinds occur, and what does their ink become today?

STAGED GATHER rows, read-only. Usage:
    python3 benchmarks/page-claim-order-2026-11/count.py classes SLICEDIR      # detector classes of the five kinds + wedge rows
    python3 benchmarks/page-claim-order-2026-11/count.py pages OUTDIR          # low-res renders of the 16 frozen pages
    python3 benchmarks/page-claim-order-2026-11/count.py reference             # the five kinds in the reference encodings
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys
import zipfile

KINDS = ("ottav", "pedal", "segno", "coda", "trill", "rehears", "ornament", "wiggle", "hairpin", "cresc", "dim",
         "wedge", "text", "fermata", "tremolo", "repeat", "volta")
LIBP = "/Users/seanjohnson/Desktop/ReEngrave/library/"
SLICES = pathlib.Path(LIBP) / "_shared-records" / "lane-report-slices-20261029-night"
EDITIONS = {
    "litolff": (LIBP + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
                [2, 4, 6, 8, 9, 10, 11, 16]),
    "brahms": (LIBP + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
               [0, 4, 5, 8, 12, 14, 19, 25]),
}
REFERENCE = {
    "litolff": LIBP + "reference/beethoven/symphony-5/beethoven--symphony-5--mvt1--gradus.mxl",
    "brahms": LIBP + "reference/brahms/symphony-1/brahms--symphony-1--mvt1--gradus.mxl",
}


def rows(d: pathlib.Path, name: str = "observations.jsonl"):
    with open(d / name) as fh:
        for line in fh:
            yield json.loads(line)


def classes(d: pathlib.Path) -> None:
    cls = collections.Counter()
    pages_ = collections.Counter()
    wb = []
    for o in rows(d):
        if o["quantity"] == "glyph_box":
            cls[o["value"][0]] += 1
            pages_[o["subject"].split("/")[1]] += 1
        elif o["quantity"] == "wedge_box":
            wb.append((o["subject"], o["value"], o["reader"], (o.get("detail") or {}).get("bbox_page_px")))
    print("pages", sorted(pages_.items()))
    print("classes of interest", {k: v for k, v in cls.items() if any(t in k.lower() for t in KINDS)})
    print("wedge rows", len(wb), collections.Counter((w[2], w[1]) for w in wb))
    ab = collections.Counter()
    for a in rows(d, "abstentions.jsonl"):
        if a.get("quantity") == "wedge_box":
            ab[((a.get("detail") or {}).get("why") or a.get("reason"))] += 1
    print("wedge abstentions", dict(ab))


def pages(out: pathlib.Path) -> None:
    """Low-resolution renders of the 16 frozen pages, for the lane's own look at what the print holds (rehearsal frames etc.)."""
    import fitz
    out.mkdir(parents=True, exist_ok=True)
    for pl, (f, pp) in EDITIONS.items():
        d = fitz.open(f)
        for p in pp:
            d[p].get_pixmap(dpi=110).save(str(out / ("%s_p%02d.png" % (pl, p))))


def reference(_unused=None) -> None:
    """Whole-movement counts of the five kinds (and wedges) in the reference encoding: a source that is not our reading."""
    for pl, f in REFERENCE.items():
        z = zipfile.ZipFile(f)
        name = [n for n in z.namelist() if n.endswith(".xml") and "META" not in n][0]
        s = z.read(name).decode("utf8", "replace")
        c = {
            "octave-shift starts": len(re.findall(r'<octave-shift[^>]*type="(?:up|down)"', s)),
            "pedal": len(re.findall(r"<pedal[\s>/]", s)),
            "segno": len(re.findall(r"<segno[\s>/]", s)),
            "coda": len(re.findall(r"<coda[\s>/]", s)),
            "rehearsal": len(re.findall(r"<rehearsal[\s>/]", s)),
            "trill-mark": len(re.findall(r"<trill-mark[\s>/]", s)),
            "wavy-line starts": len(re.findall(r'<wavy-line[^>]*type="start"', s)),
            "wedge starts": len(re.findall(r'<wedge[^>]*type="(?:crescendo|diminuendo)"', s)),
            "words": len(re.findall(r"<words[\s>/]", s)),
        }
        # measure numbers of trills (to place them on pages)
        trills = []
        for m in re.finditer(r'<measure[^>]*number="([^"]+)"(.*?)</measure>', s, re.S):
            if "trill-mark" in m.group(2) or "wavy-line" in m.group(2):
                trills.append(m.group(1))
        print(pl, c, "trill bars:", sorted(set(trills), key=lambda x: int(re.sub(r"\D", "", x) or 0)))


if __name__ == "__main__":
    fn = {"classes": classes, "pages": pages, "reference": reference}[sys.argv[1]]
    fn(pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None)
