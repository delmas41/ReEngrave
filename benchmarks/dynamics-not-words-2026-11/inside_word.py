"""ROADMAP 2.303: every dynamic claim of a page whose ink lies inside a READ word's box or inside a text candidate nobody accepted, from a saved gather record + its probe.

    python3 benchmarks/dynamics-not-words-2026-11/inside_word.py REC PAGE [--probe PROBE.json] [--json OUT]

A dynamic claim = a claimed_area row of owner `word`, source `dynamic_letters` (the register files a printed dynamic under that owner: 2.296).
  inside READ word  = the claim's CENTRE lies inside the box of a `direction_word` row (accepted by the lexicon); `compound_of` = it is the dynamic split from that marking.
  inside REJECTED candidate = a probe candidate whose box holds >= half the claim and no READ word's box overlaps that candidate; its readings (what the OCR said, all refused) are listed.
"""
import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def share(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max(1.0, (a[2] - a[0]) * (a[3] - a[1]))


def centre_in(v, b):
    cx, cy = (v[0] + v[2]) / 2, (v[1] + v[3]) / 2
    return b[0] <= cx <= b[2] and b[1] <= cy <= b[3]


def analyse(rec, page, probe_path=None):
    from tools.omr.staged import claim_readout as CR
    rows = CR.read_rows(CR.resolve_source(rec), [page])
    obs = rows["observations"]
    words = [(o["detail"]["bbox_page_px"], o["value"], o["detail"].get("dynamics") or [], o["id"]) for o in obs
             if o["quantity"] == "direction_word" and (o.get("detail") or {}).get("bbox_page_px")]
    probe = json.load(open(probe_path))[0] if probe_path else None
    cands = probe["candidates"] if probe else []
    reads = {}
    for r in (probe["readings"] if probe else []):
        reads.setdefault(r["candidate"], []).append(r["text"])
    out = []
    for o in obs:
        d = o.get("detail") or {}
        if o["quantity"] != "claimed_area" or d.get("owner") != "word" or d.get("source") != "dynamic_letters":
            continue
        v = [float(t) for t in o["value"]]
        inw = [dict(text=w[1], box=w[0], dyn=w[2], row=w[3]) for w in words if centre_in(v, w[0])]
        rej = []
        for c in cands:
            if share(v, c["box"]) >= 0.5 and not any(share(c["box"], w[0]) > 0.3 or share(w[0], c["box"]) > 0.3 for w in words):
                rej.append(dict(i=c["i"], box=c["box"], readings=reads.get(c["i"], [])))
        if inw or rej:
            out.append(dict(id=o["id"], box=[round(t, 1) for t in v], text=d.get("text"), letter=d.get("detector_letter"), lone=d.get("lone"), compound_of=d.get("compound_of"),
                            standing=d.get("standing", "READ"), inside_read_word=inw, inside_rejected_candidate=rej, sub=o["subject"], letter_rows=d.get("letter_rows")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rec")
    ap.add_argument("page", type=int)
    ap.add_argument("--probe")
    ap.add_argument("--json")
    a = ap.parse_args()
    out = analyse(a.rec, a.page, a.probe)
    for it in out:
        print("%s %s %-5s box=%s compound=%s | READ word: %s | rejected cand: %s" % (
            it["id"], it["standing"], it["text"] or ("letter " + str(it["letter"])), it["box"], bool(it["compound_of"]),
            "; ".join("%r %s" % (w["text"], [round(x) for x in w["box"]]) for w in it["inside_read_word"]) or "-",
            "; ".join("cand %d %s %s" % (c["i"], [round(x) for x in c["box"]], c["readings"][:3]) for c in it["inside_rejected_candidate"]) or "-"))
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
