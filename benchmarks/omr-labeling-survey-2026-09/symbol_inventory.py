#!/usr/bin/env python3
"""The living symbol inventory — every element that can appear on a score,
annotated with WHO OWNS IT and what labeled evidence exists.

Sean's ask (2026-09-03): an exhaustive list of score elements to label
systematically. The refinement this file implements: exhaustive means
exhaustive ASSESSMENT — about half the elements are owned by layers where
YOLO boxes buy nothing (classical CV, the template readers, OCR, the
exporter), and labeling them is wasted hands or worse (CV structurals train
as background). So every class in the training space gets a row, every row
gets an owner, and only rows owned by the DETECTOR are labeling targets.

Counts are computed from data/user-labeled/v*/labels; annotations are the
curated knowledge of SURVEY_DESIGN.md / CLAUDE.md / NOTES.md, kept here so
the table regenerates instead of going stale:

    python3 benchmarks/omr-labeling-survey-2026-09/symbol_inventory.py
        → rewrites INVENTORY.md beside this script

Run from a checkout whose data/user-labeled is current. The generated file
says so in its header; do not hand-edit it.
"""
from __future__ import annotations

import collections
import datetime as _dt
import glob
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.path.join(REPO, "data", "user-labeled")
OUT = os.path.join(HERE, "INVENTORY.md")

# Version directory -> engraving-house column(s) it contributes (curated;
# per-version granularity — v8 mixes five columns by design).
VERSION_PUBLISHERS = {
    "v1-2026-05-18-orchestral": "mixed (early orchestral)",
    "v2-2026-06-08-beet5": "Litolff",
    "v3-2026-06-09-mahler5": "Peters",
    "v4-2026-06-10-la-mer": "Durand",
    "v5-2026-07-12-clef": "clef cells (EXCLUDED from catalog)",
    "v6-2026-07-13-clef-diverse": "clef cells (EXCLUDED from catalog)",
    "v7-2026-09-02-hollow": "Litolff",
    "v8-2026-09-02-hollow2-5pub": "Litolff+Breitkopf+Peters+Eulenburg+Simrock",
    "v9-2026-09-03-hollow3-mahler1": "Universal",
    "v10-2026-09-03-hollow3-elgar1": "Novello",
    "v11-2026-09-03-hollow3-lamer": "Durand",
    "v12-2026-09-03-hollow3-tchaikovsky1-lowres": "Jurgenson (low-res)",
}

# Owner buckets, in the order the report prints them.
DETECTOR = "detector — LABELING TARGET"
DETECTOR_CAPPED = "detector — precision-capped, not a recall target"
SPECIALIST = "specialist slot ONLY (never the shared catalog)"
TEMPLATE = "CV template reader primary — detector secondary (REVISIT flag)"
CV = "classical CV — NEVER label (trains as background)"
PARKED = "parked custom class (nc=208 cap; Phase-3.4 collapse)"
UNASSESSED = "UNASSESSED — needs an owner before any labeling"

#: (prefix-or-exact, owner, survey row / note). First match wins; exact
#: names take precedence over prefixes. The reasons live in SURVEY_DESIGN.md
#: §1 and NOTES.md's PARKED entry — this column is the pointer, not the essay.
ANNOTATIONS: list[tuple[str, str, str]] = [
    # --- classical CV structurals: boxing them trains background ---
    ("staff", CV, "staff_detector"),
    ("stem", CV, "line_detection (Phase 4f)"),
    ("beam", CV, "line_detection (Phase 4f)"),
    ("brace", CV, "system grouping"),
    ("ledgerLine", CV, "ledger-ladder evidence in transcribe"),
    # --- template-read header elements: detector is at best a second voter ---
    ("timeSig", TEMPLATE, "time_signature_locator reads meters 12/0; "
                          "REVISIT per NOTES.md 🅿️ 2026-09-03 (Sean)"),
    ("keyFlat", TEMPLATE, "key_signature_template reads 11/12 vs detector 2/12"),
    ("keySharp", TEMPLATE, "key_signature_template"),
    ("keyNatural", TEMPLATE, "key_signature_template"),
    # --- clefs: labels feed OMR_CLEF_WEIGHTS, never the shared catalog ---
    ("gClef", SPECIALIST, "v5/v6 held out; density-collapse precedent 2506→114"),
    ("cClef", SPECIALIST, "same"),
    ("fClef", SPECIALIST, "same"),
    ("unpitchedPercussionClef1", SPECIALIST, "same"),
    ("clef8", SPECIALIST, "same"),
    ("clef15", SPECIALIST, "same"),
    # the catalog's own clef spellings (the 208-name list differs from the
    # DSv2 snapshot; two ids even share the name clefF)
    ("clefG", SPECIALIST, "same"),
    ("clefF", SPECIALIST, "same"),
    ("clefC", SPECIALIST, "same"),
    ("clefUnpitchedPercussion", SPECIALIST, "same"),
    ("legerLine", CV, "ledger-ladder evidence in transcribe (catalog spelling)"),
    ("arpeggio", DETECTOR, "unmeasured"),
    ("noteheadFull", DETECTOR, "catalog alias family for filled noteheads"),
    ("tuple", DETECTOR, "tuplet family (catalog spelling)"),
    # --- detector-owned, precision-capped ---
    ("slur", DETECTOR_CAPPED, "over-fires on bled arcs; 2026-09 wins were pairing/export"),
    ("tie", DETECTOR_CAPPED, "same as slur"),
    # --- detector-owned labeling rows (survey rows + supporting cast) ---
    ("noteheadBlack", DETECTOR, "well-covered baseline class"),
    ("noteheadHalf", DETECTOR, "survey R1 — SHIPPED 2026-09-03 (hollow-ft)"),
    ("noteheadWhole", DETECTOR, "survey R1 — shipped (the thin half of the row; Phase 2 fed it)"),
    ("noteheadDoubleWhole", DETECTOR, "R1 family; rare on orchestral pages"),
    ("graceNote", DETECTOR, "survey R2 — NEXT; selector: grace_score.py"),
    ("dynamic", DETECTOR, "survey R3 — small dynamics letters + hairpins"),
    ("ornament", DETECTOR, "survey R4 — deep scope"),
    ("rest", DETECTOR, "restQuarter well-covered; long rests interplay with MMR logic"),
    ("accidental", DETECTOR, "inline accidentals; header ones are the template's"),
    ("artic", DETECTOR, "exported since 2026-09-01"),
    ("fermata", DETECTOR, "exported (fermata gap closed)"),
    ("augmentationDot", DETECTOR, "dot geometry fixed 2026-09-01 (asymmetric window)"),
    ("flag", DETECTOR, "duration evidence"),
    ("tremolo", DETECTOR, "scan behavior unmeasured"),
    ("tuplet", DETECTOR, "consumed since 2026-09-01; fingering3 positional twin"),
    ("fingering", DETECTOR, "fingering3 doubles as a triplet digit (positional gate)"),
    ("caesura", DETECTOR, "unmeasured"),
    ("arpeggiato", DETECTOR, "unmeasured"),
    ("stringsDownBow", DETECTOR, "unmeasured"),
    ("stringsUpBow", DETECTOR, "unmeasured"),
    ("keyboardPedal", DETECTOR, "keyboard rep only"),
    ("ottavaBracket", DETECTOR, "8va — not yet consumed downstream"),
    ("repeatDot", DETECTOR, "repeat barlines are an export gap (NOTES item 6)"),
    ("segno", DETECTOR, "rare; unmeasured"),
    ("coda", DETECTOR, "rare; unmeasured"),
]

#: Elements with NO class in the training space at all — they can never be a
#: labeling row, and the inventory says who owns each instead.
CLASSLESS = [
    ("printed directions (legato, Allegro…)", "OCR — direction-text reader (Surya+Tesseract union)"),
    ("instrument margin labels", "OCR — staff_labels / Surya / vision ladder"),
    ("barline types (single/double/final/repeat)", "classical CV (measure_extractor); repeat emission = export gap, NOTES item 6"),
    ("textDynamic words (cresc., dim.)", "parked custom class (Phase-3.4 collapse); direction-text reads them meanwhile"),
    ("lyrics", "no path (export_coverage KNOWN_GAPS)"),
    ("metronome marks", "export gap, pinned by test (KNOWN_GAPS 'metronome')"),
    ("trill extension wavy lines", "nothing reads them"),
    ("rehearsal letters/numbers", "nothing reads them; margin-adjacent OCR candidate"),
]


def annotate(name: str) -> tuple[str, str]:
    for key, owner, note in ANNOTATIONS:
        if name == key:
            return owner, note
    for key, owner, note in ANNOTATIONS:
        if name.startswith(key):
            return owner, note
    return UNASSESSED, ""


def main() -> None:
    names = yaml.safe_load(open(os.path.join(ROOT, "catalog.yaml")))["names"]
    if isinstance(names, dict):
        names = [names[i] for i in sorted(names)]

    per_class_total = collections.Counter()
    per_class_versions: dict[int, set] = collections.defaultdict(set)
    for vd in sorted(glob.glob(os.path.join(ROOT, "v*"))):
        if not os.path.isdir(vd):
            continue
        vn = os.path.basename(vd)
        for lf in glob.glob(os.path.join(vd, "labels", "*.txt")):
            for line in open(lf):
                line = line.strip()
                if line:
                    cid = int(line.split()[0])
                    per_class_total[cid] += 1
                    per_class_versions[cid].add(vn)

    rows = []
    for cid, name in enumerate(names):
        owner, note = annotate(name)
        pubs = sorted({VERSION_PUBLISHERS.get(v, v)
                       for v in per_class_versions.get(cid, set())})
        rows.append({"name": name, "boxes": per_class_total.get(cid, 0),
                     "owner": owner, "note": note,
                     "pubs": "; ".join(pubs) if pubs else "—"})
    extra = {cid: n for cid, n in per_class_total.items() if cid >= len(names)}

    order = [DETECTOR, DETECTOR_CAPPED, SPECIALIST, TEMPLATE, CV, PARKED,
             UNASSESSED]
    by_owner: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        by_owner[r["owner"]].append(r)

    lines = []
    lines.append("# Symbol inventory — every element, its owner, and its labeled evidence")
    lines.append("")
    lines.append(f"**Generated — do not hand-edit.** Rebuild with "
                 f"`python3 benchmarks/omr-labeling-survey-2026-09/symbol_inventory.py` "
                 f"(last: {_dt.date.today().isoformat()}). Curated annotations "
                 f"live in the script; counts come from `data/user-labeled/v*/labels`. "
                 f"Rationale per owner bucket: `SURVEY_DESIGN.md` §1, CLAUDE.md "
                 f"\"Hand-label cells\", NOTES.md 🅿️ 2026-09-03.")
    lines.append("")
    n_classes = len(names)
    n_covered = sum(1 for r in rows if r["boxes"])
    n_targets = len(by_owner[DETECTOR]) + len(by_owner[DETECTOR_CAPPED])
    n_blind = sum(1 for r in by_owner[DETECTOR] if r["boxes"] == 0)
    lines.append(f"Training space: **{n_classes} classes** — {n_covered} carry "
                 f"any labeled box, {n_targets} are detector-owned, and "
                 f"**{n_blind} detector-owned labeling targets have ZERO "
                 f"boxes** (the blind spots the survey works through).")
    lines.append("")

    for owner in order:
        group = by_owner.get(owner, [])
        if not group:
            continue
        lines.append(f"## {owner} ({len(group)})")
        lines.append("")
        lines.append("| class | boxes | publisher columns covered | note |")
        lines.append("|---|--:|---|---|")
        for r in sorted(group, key=lambda r: (-r["boxes"], r["name"])):
            lines.append(f"| `{r['name']}` | {r['boxes']} | {r['pubs']} | {r['note']} |")
        lines.append("")

    lines.append("## Elements with no class at all")
    lines.append("")
    lines.append("| element | owner |")
    lines.append("|---|---|")
    for name, owner in CLASSLESS:
        lines.append(f"| {name} | {owner} |")
    lines.append("")
    if extra:
        lines.append(f"(Custom-class boxes beyond the nc={n_classes} space, "
                     f"filtered by the catalog cap: "
                     + ", ".join(f"id {c}×{n}" for c, n in sorted(extra.items()))
                     + " — the parked barline/textDynamic collection.)")
        lines.append("")

    with open(OUT, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}: {n_classes} classes, {n_covered} covered, "
          f"{n_blind} zero-box detector targets")


if __name__ == "__main__":
    main()
