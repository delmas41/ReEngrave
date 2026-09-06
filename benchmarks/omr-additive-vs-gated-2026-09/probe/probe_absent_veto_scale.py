"""`absent_instrument` at document scale -- the one identity gate whose
population is not structurally empty on a single page.

Reads the committed whole-work extract (Beethoven 5 / Litolff, 88 pages, 1616
staff records) that the veto session wrote. Both standing benchmarks run ONE
page per row, and attestation distance is always 0 on a single page, so neither
can see this gate at all -- this is the only committed artefact that can.

Asks: how much of the document does it touch, what does refusing cost in named
staves, and does the quantity it already computes (`distance`/`outside`) have
any spread for a graded form to use?
"""
from __future__ import annotations

import collections
import json
import os

P = os.environ.get("EXTRACT", "/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
                   "omr-absent-instrument-veto-2026-09/out/"
                   "whole-report2.extract.json")


def main():
    d = json.load(open(P))
    ctx = d["contextual"]
    veto = ctx.get("absent_instrument_veto") or {}
    print("source:", d.get("source_pdf", "").split("/")[-1])
    print("veto block keys:", list(veto))
    n = collections.Counter()
    src = collections.Counter()
    for page in d["pages"]:
        for s in page.get("systems", []):
            for st in s.get("staves", []):
                n["staves"] += 1
                if st.get("instrument"):
                    n["named"] += 1
                else:
                    n["unnamed"] += 1
                if st.get("instrument_veto"):
                    n["vetoed"] += 1
                src[st.get("instrument_source") or "(none)"] += 1
    print("\nstaff records:", dict(n))
    print("instrument_source:", dict(src))
    print("labelled_staves (contextual):", ctx.get("labelled_staves"))

    vet = veto.get("vetoes") or veto.get("records") or []
    print(f"\nveto records: {len(vet)}")
    if vet:
        print("record keys:", list(vet[0]))
        dists = [v.get("distance") for v in vet
                 if isinstance(v.get("distance"), int)]
        outs = collections.Counter(v.get("outside") for v in vet)
        names = collections.Counter(v.get("instrument") or v.get("name")
                                    for v in vet)
        print("distance spread:", sorted(dists))
        print("outside:", dict(outs))
        print("instruments refused:", dict(names))
    ev = veto.get("label_evidence") or []
    print(f"\nlabel_evidence rows: {len(ev)}")


if __name__ == "__main__":
    main()
