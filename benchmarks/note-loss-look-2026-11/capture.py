"""2.289 capture: replay the 2.286 conservation slices and keep, for EVERY glyph subject, its fate (written / the reason it was
not), its page box, its staff, its owner verdict. MEASURE ONLY: it wraps `export._place_notes` to read the `fates` out-param and the
Record it was handed; no pipeline code changes, the exported file is the one `conservation` writes.

    python3 benchmarks/note-loss-look-2026-11/capture.py OUTDIR      (about 2 min)

Writes OUTDIR/<plate>.fates.json and OUTDIR/<plate>.musicxml.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import conservation as C   # noqa: E402
from tools.omr.staged import export as E         # noqa: E402
from tools.omr.staged.record import Q           # noqa: E402

CAP = {}
_orig = E._place_notes


def _wrap(rec, runs, *a, **k):
    CAP["rec"] = rec
    CAP["fates"] = k.get("fates")
    return _orig(rec, runs, *a, **k)


E._place_notes = _wrap


def dump(plate, pages, out):
    rec = C.load_pages(plate, pages, C.DEFAULT_TAG)
    res = C.export_pages(rec)
    r, fates = CAP["rec"], CAP["fates"]
    rows = []
    for o in r.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None:
            continue
        own_v = r.verdict(Q.GLYPH_OWNER, sub) or {}
        nh = r.obs(Q.NOTEHEAD_CLASS, sub)
        isr = bool(r.obs(Q.REST, sub))
        rows.append({
            "sub": sub, "page": s["page"], "system": s["system"], "staff": s["staff"], "cell": s["cell"], "glyph": s["glyph"],
            "fate": (fates or {}).get(sub), "box": E._page_box_of(o), "head": bool(nh), "rest": isr,
            "owner": own_v.get("value") if own_v.get("outcome") == "decided" else None,
            "owner_outcome": own_v.get("outcome"), "owner_reason": own_v.get("reason"), "owner_decider": own_v.get("decider"),
            "nh_cls": (nh[-1].get("value") if nh else None),
        })
    staves = {o["subject"]: {"value": o.get("value"), "detail": o.get("detail")} for o in r.obs_of(Q.STAFF_LINES)}
    pathlib.Path(out, plate + ".staves.json").write_text(json.dumps(staves, default=str))
    pathlib.Path(out, plate + ".fates.json").write_text(json.dumps(rows))
    pathlib.Path(out, plate + ".musicxml").write_text(res["xml"])
    print(plate, len(rows), "glyph rows", res["seconds"], "s")
    return res


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for plate, pages in C.DEFAULT_PAGES.items():
        dump(plate, pages, out)
