"""Write `out/adjudication.json` — every contradiction of the two whole-work
runs, with a HAND verdict and the evidence it rests on.

Each verdict was settled by opening the printed page (`render_margin.py`) and
reading the margin, plus `count_staves.py` where the detected staff count was
in doubt; the work's roster in `data/score-library/catalog.json` settles Tuba.
The rules below are how those readings generalise over identical rows — every
DISTINCT (page, read, exported) triple in the two corpora was looked at, and a
rule stands for a reading, never for a guess.

⚠️ Verdicts, not scores: `export_wrong` means the name written to the file is
not the instrument the page prints; `label_wrong` means the reader misread the
margin and the exported name is right. `both_right` is the structural false
positive (a condensed staff naming two instruments) and did not occur here.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "benchmarks/omr-label-contradiction-2026-09/out"

# (work, predicate) -> (verdict, evidence)
BEET = [
    (lambda r: r["read"] == "Timpani" and r["exported"] == "Trumpet",
     "export_wrong",
     "p37 s5 / p50 s8 / p64 s8 all print `Tp.` (Timpani) and export Trumpet; "
     "slot 7 already carries a label-agreeing Trumpet on the same system. "
     "This is the `Tp.` ambiguity fixed on claude/agitated-bassi-e3a0ab "
     "(5d6e76a8), not in main."),
    (lambda r: r["read"] == "Flute" and r["exported"] == "Piccolo",
     "label_wrong",
     "p50 s0 / p64 s0 print `Fl. pic.` on two lines; the reader keeps `Fl.` "
     "and drops the qualifier. Slot 0 = Piccolo is right."),
    (lambda r: r["read"] == "Trumpet" and r["exported"] == "Trombone",
     "label_wrong",
     "p64 s11 prints `Tr. Bas.` (bass trombone); the reader falls back to the "
     "bare `tr` -> Trumpet. Slots 9-11 = Trombone are right."),
    (lambda r: r["read"] == "Bass voice",
     "label_wrong",
     "`Basso.` at the foot of the string section. Settled by c0a80ae7's "
     "score-order overturn; the export (Contrabass) is right and the lexicon's "
     "first answer is the ambiguous one on purpose."),
    (lambda r: r["read"] == "Contrabass" and r["exported"] == "Oboe",
     "label_wrong",
     "p37 s1 prints `Ob.`, clipped at the left edge in this scan and read as a "
     "Cb. Export right."),
]

BRAHMS = [
    (lambda r: r["page_index"] in (33, 34, 35),
     "export_wrong",
     "p33 prints Fl, Ob, Klar, Fag, Hr, Trpt, Pk, Viol.Solo, 1.Viol, 2.Viol, "
     "Br, Vcl, K.-B. The aligner consumes slot 6 (the second Horn) on a system "
     "that has one horn staff, so Trpt/Pk/Viol.Solo export as "
     "Horn/Trumpet/Timpani. Labels right, names shifted by one slot."),
    (lambda r: r["page_index"] == 36,
     "label_wrong",
     "p36 is a movement-opening page whose ROSTER block prints `4 Hörner in Es "
     "/ in H basso`; `basso` there is a horn key, read as a Bass voice."),
    (lambda r: r["page_index"] in (60, 67),
     "export_wrong",
     "Both pages print TWO systems (14+13 and 14+14, counted off the page) "
     "that phase 1 merged into one 27/28-staff system; the 16-slot reference "
     "is then laid on the last 16 staves and every name below the join is "
     "wrong. The labels on those staves are correct."),
    (lambda r: r["page_index"] == 63,
     "label_wrong",
     "p63 system 1 staff 1 prints `Ob.`, scanned so the O reads as a C; the "
     "reader returns Contrabass. Export right."),
    (lambda r: r["exported"] == "Tuba",
     "export_wrong",
     "Brahms 1 has NO tuba: catalog.json InstrDetail `2, 2, 2, 2+1 - 4, 2, 3, "
     "0, timp, strs` (source_kind catalog, independent of the encodings). "
     "Slot 9 is a score-order invention; the page prints Pos. there."),
    (lambda r: r["page_index"] == 72 and r["read"] == "Clarinet",
     "label_wrong",
     "p72 system 1 staff 5 prints `Hr. (C)`; the key qualifier is read as a "
     "Clarinet. Export (Horn) right."),
    (lambda r: r["page_index"] == 85,
     "export_wrong",
     "p85 prints 16 staves (count_staves) and phase 1 found 17; the 16 slots "
     "land one staff too high, so Ob/Klar/Fag/K-Fag/Trpt/Pk export as "
     "Fl/Ob/Klar/Fag/Horn/Tuba. Labels right."),
]


def find(pattern: str) -> Path:
    files = subprocess.run(["git", "ls-files", "*.json"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split()
    hits = [f for f in files if pattern in f]
    assert len(hits) == 1, hits
    return ROOT / hits[0]


def main() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from scan_artefacts import contradictions

    out = []
    for work, pattern, rules in (
            ("beet5", "beet5/-fitsearch-spans-on.json", BEET),
            ("brahms1", "brahms1/-fitsearch-spans-on.json", BRAHMS)):
        rows, _ = contradictions(json.loads(find(pattern).read_text()))
        for r in rows:
            hit = [(v, e) for pred, v, e in rules if pred(r)]
            if not hit:
                raise SystemExit(f"no rule matches {work} {r}")
            if len({v for v, _ in hit}) != 1:
                raise SystemExit(f"rules disagree on {work} {r}: {hit}")
            verdict = hit[0][0]
            out.append({"work": work, **r, "verdict": verdict,
                        "evidence": " | ".join(e for _, e in hit)})
    (OUT / "adjudication.json").write_text(json.dumps(out, indent=1))
    from collections import Counter
    for work in ("beet5", "brahms1"):
        c = Counter(r["verdict"] for r in out if r["work"] == work)
        n = sum(c.values())
        print(f"{work:8} n={n:4d}  " + "  ".join(f"{k}={v}" for k, v in
                                                 sorted(c.items())))
    c = Counter(r["verdict"] for r in out)
    n = sum(c.values())
    print(f"{'POOLED':8} n={n:4d}  " + "  ".join(f"{k}={v}" for k, v in
                                                 sorted(c.items())))


if __name__ == "__main__":
    main()
