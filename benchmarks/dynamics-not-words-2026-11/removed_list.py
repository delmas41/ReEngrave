"""ROADMAP 2.303: every dynamic claim the flag removes (OFF filed it, ON files no dynamic over its ink), one line each, and every claim ON ADDS (a word claim for letters the word's own claim did not hold).

    python3 benchmarks/dynamics-not-words-2026-11/removed_list.py plate=page,page=OFF_REC=ON_REC ...      e.g. litolff=8=OFF=ON brahms=0,14=OFF=ON

A claim's place: page / system / staff / cell (the bar's index in its staff of that system; it restarts per system) from the detector letter rows it was spelled from (`letter_rows` -> the letter
row's subject `glyph/PAGE/SYSTEM/STAFF/CELL/n`), the READ word whose box holds the claim's centre. Reads records; writes nothing.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main():
    from tools.omr.staged import claim_readout as CR
    import tiles_303 as T
    for spec in sys.argv[1:]:
        plate, pages, off, on = spec.split("=")
        for pg in (int(x) for x in pages.split(",")):
            ro = CR.read_rows(CR.resolve_source(off), [pg])
            rn = CR.read_rows(CR.resolve_source(on), [pg])
            letters = {o["id"]: o["subject"] for o in ro["observations"] if o["quantity"] == "dynamic_letter"}
            words = T.words_of(ro)
            oc, nc = T.dyn_claims(ro), T.dyn_claims(rn)
            for c in oc:
                if any(T.share(c["box"], k["box"]) >= 0.5 for k in nc):
                    continue
                subs = sorted({letters[i] for i in c["letters"] if i in letters})
                where = sorted({tuple(s.split("/")[2:5]) for s in subs})
                w = next((w for w in words if T.share(c["box"], w["box"]) >= 0.5), None)
                print("%s p%d REMOVED %-8s %s box=%s sys/staff/cell=%s word=%r" % (plate, pg, c["text"] or "letter " + str(c["letter"]), c["id"], [round(v) for v in c["box"]], where, (w or {}).get("text")))
            offs = {tuple(round(v) for v in c["box"]) for c in oc}
            add = [o for o in rn["observations"] if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("letters_of_word")]
            for o in add:
                print("%s p%d ADDED   word claim for letters of %r box=%s (owner row %s)" % (plate, pg, o["detail"].get("text"), [round(v) for v in o["value"]], o["detail"].get("owner_row")))


main()
