"""Every number in FINDINGS.md, re-derived from the committed artefacts.

⚠️ **THE PROSE IS THE THING THAT DRIFTS**, and this repo's ledger is full of
figures that were right when written and wrong a week later. This asserts each
headline against the JSON it came from, so a reader can check the write-up
without re-running a gather — **it needs no weights, no library and no PDF.**

    python3 benchmarks/omr-document-identity-2026-09/verify_findings.py

Exit 0 = the write-up matches the artefacts. Non-zero names each figure that
does not, with both values.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
FAIL: list[str] = []


def chk(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else '⚠️ '} {name:44s} {got!r:>28}"
          f"{'' if ok else f'   FINDINGS SAY {want!r}'}")
    if not ok:
        FAIL.append(name)


def main() -> int:
    lib = json.loads((OUT / "library-domains.json").read_text())
    tab = {(r["image_type"], r["verdict"]): r["n"] for r in lib["cross_tab"]}
    rows = lib["rows"]
    print("§1  the label against the measurement, 289 editions")
    chk("editions", lib["n"], 289)
    chk("Normal Scan -> scanned", tab.get(("Normal Scan", "scanned")), 272)
    chk("Typeset -> engraved", tab.get(("Typeset", "engraved")), 7)
    chk("no label -> scanned", tab.get(("None", "scanned")), 7)
    chk("no label -> engraved", tab.get(("None", "engraved")), 3)
    # ⚠️ THE CLAIM IS "ZERO DISAGREEMENTS WHERE THE LABEL EXISTS", so it is
    # asserted as a partition rather than read off two happy cells.
    labelled = [r for r in rows if r.get("image_type") in ("Normal Scan",
                                                           "Typeset")]
    agree = [r for r in labelled
             if (r["image_type"] == "Typeset") == (r["verdict"] == "engraved")]
    chk("labelled editions", len(labelled), 279)
    chk("of which AGREE", len(agree), 279)

    print("\n§4  what the catalog can supply")
    for f, n in (("publisher", 285), ("publisher_year", 195), ("plate", 177)):
        chk(f"{f} present", sum(1 for r in rows if r.get(f)), n)
    chk("has_text_layer present", sum(1 for r in rows if "has_text_layer" in r),
        289)
    chk("scans carrying a text layer",
        sum(1 for r in rows
            if r["verdict"] == "scanned" and r.get("has_text_layer")), 54)

    print("\n§5  the A/B")
    arm = json.loads((OUT / "keysig-domain-arm.json").read_text())
    chk("reach: the domain row", arm["reach"]["input_domain"], ["engraved"])
    chk("reach: the catalog ABSTAINS",
        arm["reach"]["document_identity_abstained"], ["not_in_catalog"])
    chk("quantities moved", sorted(arm["quantities_moved"]),
        ["accidental", "key_signature"])
    for k, n in (("off", 26), ("on", 47)):
        chk(f"{k.upper()} right", arm["accuracy"][k]["right"], n)
    for k, n in (("off", 24), ("on", 3)):
        chk(f"{k.upper()} wrong", arm["accuracy"][k]["wrong"], n)
    chk("OFF fitted_by_template",
        arm["key_signature"]["off"]["reasons"].get("fitted_by_template"), 20)
    chk("ON  engraved tier",
        arm["key_signature"]["on"]["reasons"]
        .get("fitted_by_template_engraved"), 47)
    chk("ON  fitted residue",
        arm["key_signature"]["on"]["reasons"].get("fitted"), 3)

    print("\n§5b the file, and the residue")
    a = json.loads((OUT / "note-accuracy-arm-0.json").read_text())
    b = json.loads((OUT / "note-accuracy-arm-1.json").read_text())
    chk("part-bars scored", a["part_bars"], 360)
    chk("bars exact OFF", a["bars_exact"], 313)
    chk("bars exact ON", b["bars_exact"], 322)
    key = "same count, differs ONLY by an accidental"
    chk("accidental-only OFF", a["disagreements"][key], 43)
    chk("accidental-only ON", b["disagreements"][key], 34)
    A = {p["part"]: p for p in a["per_part"]}
    B = {p["part"]: p for p in b["per_part"]}
    chk("parts BETTER",
        sum(1 for k in A if B[k]["bars_exact"] > A[k]["bars_exact"]), 4)
    chk("parts WORSE",
        sum(1 for k in A if B[k]["bars_exact"] < A[k]["bars_exact"]), 0)
    # the residue is on parts whose key is now RIGHT — the in-bar accidental
    chk("non-exact bars on the 2 wrong-key parts",
        sum(20 - B[k]["bars_exact"] for k in B if k in (13, 14)), 8)
    chk("non-exact bars on the 16 correct-key parts",
        sum(20 - B[k]["bars_exact"] for k in B if k not in (13, 14)), 30)
    for f, n in (("arm-0.musicxml", 44), ("arm-1.musicxml", 67)):
        chk(f"{f} <alter>",
            len(re.findall(r"<alter>", (OUT / f).read_text())), n)
    chk("arm-1 <fifths>-3",
        len(re.findall(r"<fifths>-3</fifths>",
                       (OUT / "arm-1.musicxml").read_text())), 14)

    print("\n§6b the scan is untouched")
    sc = json.loads((OUT / "scan-untouched.json").read_text())
    chk("OFF == ON", sc["off_equals_on"], True)
    chk("the control DIFFERS", sc["control_differs"], True)
    chk("verdicts on that page", sc["n_verdicts"], 12)

    print(f"\n{'=' * 78}\n{'FINDINGS.md MATCHES THE ARTEFACTS' if not FAIL else f'⚠️ {len(FAIL)} FIGURES DO NOT MATCH'}")
    for f in FAIL:
        print(f"   {f}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
