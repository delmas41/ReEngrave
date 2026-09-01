"""Can a conventional OCR engine read the margin instead of a vision model?

`VISION_CEILING_2026-08-30.md` and `benchmarks/omr-part-staff-join-2026-08/`
measure `staff_labels_vision` at or near ceiling on every page tried. The
obvious question — and one that was being answered from expectation rather than
measurement — is whether Tesseract would do the same job for nothing.

The comparison is deliberately generous to Tesseract:

* it gets **the same margin pixels** the vision reader gets, computed with the
  same geometry as `build_margin_crop`;
* at **native resolution**, not downscaled to the 1568 px the API would impose;
* **without the index gutter**, which is an affordance for the vision reader and
  would only be noise here;
* across a **sweep of page-segmentation modes** and an upscale/binarise grid,
  scored at its own best setting per page rather than a single chosen config.

Staff assignment is done for it too: every recognised word is attached to the
nearest staff centre and the words on one staff are joined in reading order, so
"Fl." above "pic." becomes "Fl. pic." without Tesseract having to know that.

Scoring is what the PIPELINE needs, not string similarity: does the text land on
the right staff and resolve through `instruments.lookup` to the right instrument?
A margin reader that returns perfect strings the lexicon cannot use is worth
nothing here, and one that invents a label for an unlabelled staff is worse than
one that stays quiet — so correct abstentions are counted too.

    python3 benchmarks/omr-margin-labels-2026-08/eval_tesseract.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup                       # noqa: E402
from tools.omr.preprocessing import render_page                # noqa: E402
from tools.omr.staff_detector import detect_staves             # noqa: E402
from tools.omr.staff_labels_vision import (MARGIN_SPACINGS,    # noqa: E402
                                           OVERLAP_SPACINGS, _spacing)

# The two pages whose printed labels are hand-verified against the print, with
# the reading the vision model returned for each (also verified). Ordinals are
# position within the system, top to bottom.
PAGES = [
    {
        "id": "beet5-p48",
        "pdf": "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
               "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf",
        "page_index": 48, "dpi": 600, "n_staves": 17,
        "truth": {0: "Fl. pic.", 1: "Fl.", 2: "Ob.", 3: "Cl.", 4: "Fag.",
                  5: "C. Fag.", 6: "Cor.", 7: "Tr.", 8: "Timp.",
                  9: "Tr. Alt.", 10: "Tr Ten.", 11: "Tr. Bas."},
    },
    {
        "id": "mahler-p4",
        "pdf": "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
               "PDF Scores/Mahler_5_.pdf",
        "page_index": 4, "dpi": 400, "n_staves": 21,
        "truth": {0: "A-Klar.", 1: "Fag.", 2: "Contraf.", 3: "F-Hörner",
                  5: "B-Tromp.", 7: "Posaunen", 8: "Tuba", 9: "Pauken",
                  10: "Becken", 11: "Gr. Tr.", 12: "Kl.Tr.", 13: "Tamtam",
                  14: "Erste Viol.", 15: "Zweite Viol.", 16: "Violen",
                  17: "Vcelle. get.", 19: "Bäss get."},
    },
]

# Tesseract's page-segmentation modes worth trying on a tall sparse strip.
PSMS = [
    (4, "single column of variable-size text"),
    (6, "one uniform block"),
    (11, "sparse text, no order"),
    (12, "sparse text with orientation detection"),
]


def margin_crop(pws, staves):
    """The same pixels `build_margin_crop` sends, minus the index gutter."""
    from PIL import Image

    page = pws.page
    height, width = page.binary.shape
    spacing = _spacing(staves)
    x_starts = sorted(s.x_start for s in staves)
    x_ref = x_starts[len(x_starts) // 2]
    x0 = max(0, int(x_ref - MARGIN_SPACINGS * spacing))
    x1 = min(width, int(x_ref + OVERLAP_SPACINGS * spacing))
    y0 = max(0, min(s.top_y for s in staves) - int(2 * spacing))
    y1 = min(height, max(s.bottom_y for s in staves) + int(2 * spacing))
    return Image.fromarray(page.rgb[y0:y1, x0:x1]).convert("RGB"), y0


def read(img, psm: int, upscale: int, binarise: bool) -> list[tuple[float, str]]:
    """`(y centre, word)` for every word Tesseract is confident about."""
    import pytesseract
    from PIL import Image

    work = img
    if binarise:
        work = work.convert("L").point(lambda v: 0 if v < 128 else 255).convert("RGB")
    if upscale > 1:
        work = work.resize((work.width * upscale, work.height * upscale),
                           Image.LANCZOS)
    data = pytesseract.image_to_data(
        work, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    out = []
    for text, conf, top, h in zip(data["text"], data["conf"], data["top"],
                                  data["height"]):
        text = (text or "").strip()
        if not text or float(conf) < 30:
            continue
        out.append(((top + h / 2.0) / upscale, text))
    return out


def score(words, staves, y0, truth, n_staves):
    """Attach every word to its nearest staff, then score the instrument."""
    centres = [((s.top_y + s.bottom_y) / 2.0) - y0 for s in staves]
    by_staff: dict[int, list[tuple[float, str]]] = {}
    for y, text in words:
        ordinal = min(range(len(centres)), key=lambda i: abs(centres[i] - y))
        by_staff.setdefault(ordinal, []).append((y, text))
    got = {o: " ".join(t for _, t in sorted(ws))
           for o, ws in by_staff.items()}

    right = wrong = missed = 0
    abstain_ok = abstain_bad = 0
    detail = []
    for ordinal in range(n_staves):
        want_text = truth.get(ordinal)
        want = lookup(want_text) if want_text else None
        want_name = want.instrument.name if want else None
        raw = got.get(ordinal)
        hit = lookup(raw) if raw else None
        name = hit.instrument.name if hit else None
        if want_name is None:
            if name is None:
                abstain_ok += 1
            else:
                abstain_bad += 1
                detail.append((ordinal, "—", raw, name, "INVENTED"))
        elif name == want_name:
            right += 1
        elif name is None:
            missed += 1
            detail.append((ordinal, want_text, raw, None, "missed"))
        else:
            wrong += 1
            detail.append((ordinal, want_text, raw, name, "WRONG"))
    return right, wrong, missed, abstain_ok, abstain_bad, detail


# What the two readers' labels DO, which is the number that matters. Label
# accuracy understates the gap badly, because a missing label does not cost one
# staff — it collapses the pinned block that label opens.
TESSERACT_P48 = {0: "Fl. pic.", 1: "Fl.", 2: "Ob.", 3: "Cl.", 4: "Fag.",
                 5: "C. Fag.", 6: "Cor.", 7: "Tr.", 8: "Timp", 9: "A.",
                 10: "Tr Ten.", 11: "Tr. Bas."}


def downstream() -> None:
    """Beethoven 5 p.48: the same join, from each reader's labels."""
    from tools.omr.dossier import join_parts_to_slots

    truth_path = (REPO / "benchmarks/omr-part-staff-join-2026-08"
                  / "ground-truth-beet5-p48.json")
    evidence = (REPO / "benchmarks/omr-part-staff-join-2026-08/evidence"
                / "p48-vision-labels.json")
    if not (truth_path.exists() and evidence.exists()):
        return
    truth = json.loads(truth_path.read_text())
    vision = {int(k): v for k, v in json.loads(
        evidence.read_text())["labels_by_staff_ordinal"].items()}
    dossier = json.loads((REPO / f"data/dossiers/{truth['work_id']}.json").read_text())
    want_part = [s["parts"][0] for s in truth["slots"]]
    want_clef = [s["clef"] for s in truth["slots"]]

    print("\n=== DOWNSTREAM: beet5-p48, the same join from each reader ===")
    for name, labels in (("vision", vision), ("tesseract", TESSERACT_P48)):
        facts = join_parts_to_slots(len(want_part), dossier, labels)
        parts = sum(1 for f, w in zip(facts, want_part) if f and f["part"] == w)
        clefs = sum(1 for f, w in zip(facts, want_clef) if f and f.get("clef") == w)
        print(f"  {name:<10} parts {parts}/{len(want_part)}   "
              f"clefs {clefs}/{len(want_clef)}")
    print("  the three tesseract loses are the trombones: `Tr. Alt.` reads as "
          "`A.`,\n  so the block starts one staff late and the alto, tenor and "
          "bass clefs all move.")


def main() -> int:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        print("pytesseract not installed", file=sys.stderr)
        return 1

    grand = {"right": 0, "wrong": 0, "missed": 0, "ab_ok": 0, "ab_bad": 0, "n": 0}
    for spec in PAGES:
        pdf = Path(spec["pdf"])
        if not pdf.exists():
            print(f"{spec['id']}: SKIP (missing {pdf.name})")
            continue
        pws = detect_staves(render_page(pdf, spec["page_index"], dpi=spec["dpi"]))
        staves = sorted(pws.staves, key=lambda s: s.top_y)
        img, y0 = margin_crop(pws, staves)
        n_printed = len(spec["truth"])
        print(f"\n=== {spec['id']}: {len(staves)} staves, "
              f"{n_printed} printed labels, crop {img.width}x{img.height} ===")

        best = None
        for psm, note in PSMS:
            for upscale in (1, 2):
                for binarise in (False, True):
                    words = read(img, psm, upscale, binarise)
                    r, w, m, ao, ab, detail = score(
                        words, staves, y0, spec["truth"], spec["n_staves"])
                    tag = f"psm{psm} x{upscale}{' bin' if binarise else ''}"
                    print(f"  {tag:<16} correct {r:>2}/{n_printed}  wrong {w}  "
                          f"missed {m}  invented {ab}  ({len(words)} words read)")
                    if best is None or (r, -w, -ab) > (best[0], -best[1], -best[4]):
                        best = (r, w, m, ao, ab, detail, tag)
        r, w, m, ao, ab, detail, tag = best
        print(f"  -> BEST {tag}: {r}/{n_printed} correct, {w} wrong, {m} missed, "
              f"{ab} invented, {ao} correct abstentions")
        for ordinal, want, raw, name, why in detail[:12]:
            print(f"       {why:<9} staff {ordinal:>2}  printed={str(want):<14} "
                  f"tesseract={str(raw)!r:<26} -> {name}")
        grand["right"] += r; grand["wrong"] += w; grand["missed"] += m
        grand["ab_ok"] += ao; grand["ab_bad"] += ab; grand["n"] += n_printed

    downstream()

    if grand["n"]:
        print(f"\n=== TOTAL, each page at its own best setting ===")
        print(f"  printed labels          {grand['n']}")
        print(f"  correct instrument      {grand['right']}")
        print(f"  wrong instrument        {grand['wrong']}")
        print(f"  missed entirely         {grand['missed']}")
        print(f"  invented on a blank staff {grand['ab_bad']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
