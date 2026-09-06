"""Insert this workstream's section into CLAUDE.md, above "Reading and
reproduction". Idempotent — re-running does nothing.
"""
from __future__ import annotations

from pathlib import Path

ANCHOR = "## Reading and reproduction are different questions, and now measured apart"

SECTION = r"""## A staff that contradicts its own label

**Free evidence, and the only identity check that needs NO TRUTH FILE** — it
asks the document to agree with itself. A staff whose OWN margin label the
reader read on THAT page, exported under a different name. Nothing new is
detected or read: `absent_instrument.label_evidence` already holds the per-staff
labels and the slot names are already on the record.

Computed on **every** contextual pass (`tools/omr/label_contradiction.py`, no
flag — it renames nothing and refuses nothing, so there is no behaviour to
gate). It lands in `summary["label_contradiction"]`, on each offending
`staff["label_contradiction"]`, and in a `logger.warning` when it fires. Ask it
of any stored transcription or artefact:

```bash
python3 -m tools.omr.label_contradiction out.json
```

**Adjudicated against the printed page, all 158 firings of the two whole-work
runs** (Beethoven 5 / Litolff 88pp: 110 of 973 labelled staff records; Brahms 1
/ Breitkopf 86pp: 48 of 1713): **138 (0.873) the EXPORT is wrong, 20 (0.127) the
LABEL is, 0 both right.** The largest single population is 93 Beethoven staves
printed `Tp.` and exported `Trumpet` — the `Tp.` defect diagnosed on
`claude/agitated-bassi-e3a0ab` and not in main, worth 93 wrong `<part-name>`
elements on one document, and invisible to everything standing (musicdiff does
not score `<part-name>`, and the absent-instrument veto exempts a staff that
speaks for itself, so all 93 are exempt BY RULE).

**It caught a 149-staff regression it was never told about.** On Brahms the
count reads 44 with spans off, **167** under `OMR_SPAN_REFERENCE_FIT=off` with
spans on — the arm that names 149 staves an instrument the work has not got —
and 48 once `search` lands. The "impossible name" column needs the work's
roster; this needs nothing. ⚠️ And `impossible` can only ever FALL, so it scores
a categorically-wrong name traded for an ordinarily-wrong one as free: that is
why `search` reads 48 against `refuse`'s 44 while `impossible` reads 0 against
36 — it fixes 149 and creates 6.

⚠️ **`instrument_source` is a SPLIT TO REPORT, NEVER A FILTER.** The 93 `Tp.`
rows carry `score_order_ambiguity`, the same source as the three CORRECT
`Basso.` → Contrabass overturns on the same document. Dropping the source
because three of its rows are known-good hides ninety-three that are not.

⚠️ **It says the chain `staff → slot → name` is broken, not WHICH LINK.** Seven
Brahms rows carry `source: roster` and the roster's name is *right* — the SLOT
ASSIGNMENT is wrong. And nothing on the record predicts the direction: three
side-signals were measured and the sharpest (*the READ name is already carried,
with agreement, by another staff of this system*) is **13/13 `label_wrong` on
Beethoven and 11/13 `export_wrong` on Brahms — it inverts.** So it is **additive
evidence, not a gate**, which is Sean's governing principle applied literally.

⚠️ **The structural false positive is a CONDENSED STAFF** (`Violoncello e
Basso`: the margin names one instrument, the slot the other, both right). Zero
of 158 here because neither edition condenses that way — a fact about two
publishers, not about the check.

⚠️ **The obvious field is VACUOUS.** `staff["instrument_label"]` is
slot-carried — one raw text per SLOT stamped onto every staff of that slot on
every page — so an audit on it *cannot disagree*, and `contextual.py` says so in
its own comment. Use `label_evidence`. Asserted by AST in
`test_label_contradiction.py`, whose five wiring assertions were each verified
to go RED with their call site removed (`probe/mutate_wiring.py`) — one of them
was vacuous when first written and that run is what caught it.

Full reading:
[benchmarks/omr-label-contradiction-2026-09/FINDINGS.md](benchmarks/omr-label-contradiction-2026-09/FINDINGS.md).

---

"""


def main() -> None:
    p = Path("CLAUDE.md")
    text = p.read_text()
    if "## A staff that contradicts its own label" in text:
        print("already present")
        return
    if ANCHOR not in text:
        raise SystemExit("anchor not found — CLAUDE.md moved; re-point this")
    p.write_text(text.replace(ANCHOR, SECTION + ANCHOR, 1))
    print("inserted")


if __name__ == "__main__":
    main()
