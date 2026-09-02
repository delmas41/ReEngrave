"""The CEILING: could inline accidentals identify a key signature even with
PERFECT recognition?

Measured on ground truth rather than on OMR output, deliberately and first. If
the printed accidentals of real orchestral music do not identify the printed
signature when every one of them is read correctly, then no amount of detector
work makes an inference layer viable and the OMR measurement is beside the
point. MusicXML's `<accidental>` element is exactly what is PRINTED on the page
(`<alter>` is what SOUNDS, and already contains the signature), so it is the
right ground truth for this question and it is free.

Three scopes, because the amount of evidence is the whole question:

  A  per part, whole movement        — the loosest possible upper bound
  B  per part, an 8-measure window   — what ONE STAFF of ONE PAGE actually has
  C  pooled over the parts of a movement in CONCERT space, 8-measure window
     — the design under consideration: one movement-level hypothesis,
       reconciled per staff through each part's transposition offset

Two scoring models:

  N  naturals cancel the signature. A natural on letter L is evidence that L is
     altered; a natural on a letter the signature leaves alone is only
     explicable as an in-bar cancellation and counts against.
  F  the roadmap's stated hypothesis — a missed 3-flat signature shows as
     systematic inline FLATS on B/E/A.

    python3 benchmarks/omr-keysig-from-music-2026-09/probe_ceiling_from_truth.py \
        --works 40 --window 8
"""
from __future__ import annotations

import argparse
import io
import json
import random
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
FLAT_ORDER = "BEADGCF"
SHARP_ORDER = "FCGDAEB"


def altered_letters(fifths: int) -> set[str]:
    if fifths > 0:
        return set(SHARP_ORDER[:fifths])
    if fifths < 0:
        return set(FLAT_ORDER[: -fifths])
    return set()


def fname(f: int) -> str:
    return f"{f}#" if f > 0 else (f"{-f}b" if f < 0 else "0")


# --------------------------------------------------------------------------
# reading a score
# --------------------------------------------------------------------------

def load_musicxml(path: Path) -> ET.Element | None:
    try:
        if path.suffix.lower() == ".mxl":
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist()
                         if n.endswith((".xml", ".musicxml"))
                         and not n.startswith("META-INF")]
                if not names:
                    return None
                # container.xml points at the rootfile; the heuristic below is
                # enough for this corpus and avoids a second parse.
                pick = max(names, key=lambda n: z.getinfo(n).file_size)
                return ET.fromstring(z.read(pick))
        return ET.parse(path).getroot()
    except Exception:
        return None


def parts_of(root: ET.Element) -> list[tuple[str, ET.Element]]:
    ids = []
    for sp in root.findall(".//score-part"):
        ids.append((sp.get("id"), (sp.findtext("part-name") or "").strip()))
    out = []
    for p in root.findall("part"):
        pid = p.get("id")
        name = next((n for i, n in ids if i == pid), pid or "")
        out.append((name, p))
    return out


def part_evidence(part: ET.Element) -> tuple[int | None, list[tuple[int, str, str, bool]]]:
    """(opening written fifths, [(measure_ordinal, kind, letter, clean)]).

    `clean` is the constraint the first cut of this probe was missing, and it
    is the one that decides whether the idea has a signal at all. An accidental
    applies for the rest of its measure, so a natural can be doing one of two
    unrelated jobs:

      * cancelling the KEY SIGNATURE — unambiguous evidence that the signature
        alters that letter;
      * cancelling an accidental printed EARLIER IN THE SAME BAR — evidence
        about that bar and nothing else.

    Only the first is evidence about the signature, and the two are separable
    from the page alone: track each (letter, octave)'s accidental state through
    the measure in document order, and a natural is `clean` when nothing has
    altered that pitch yet in this bar. Symmetrically a flat or sharp is
    `clean` when nothing has cancelled the pitch yet.

    Measures are numbered by ORDINAL, so a part with a pickup lines up with its
    neighbours. Only the OPENING key is returned: a movement with a key change
    is dropped by the caller, since a single hypothesis cannot describe it.
    """
    fifths_seen: list[int] = []
    evidence: list[tuple[int, str, str, bool]] = []
    for ordinal, m in enumerate(part.findall("measure")):
        for k in m.findall("attributes/key"):
            t = k.findtext("fifths")
            if t is not None:
                try:
                    fifths_seen.append(int(t))
                except ValueError:
                    pass
        bar_state: dict[tuple[str, str], str] = {}   # (letter, octave) -> kind
        for n in m.findall("note"):
            step = n.findtext("pitch/step")
            octv = n.findtext("pitch/octave") or ""
            acc = n.findtext("accidental")
            if not step:
                continue
            letter = step.strip().upper()
            if not acc:
                continue
            a = acc.strip().lower()
            kind = ("#" if a in ("sharp", "sharp-sharp", "double-sharp")
                    else "b" if a in ("flat", "flat-flat")
                    else "n" if a == "natural" else None)
            if not kind:
                continue
            prior = bar_state.get((letter, octv))
            clean = prior is None
            bar_state[(letter, octv)] = kind
            evidence.append((ordinal, kind, letter, clean))
    if not fifths_seen:
        return None, evidence
    # A key change mid-part makes one hypothesis wrong by construction.
    if len(set(fifths_seen)) > 1:
        return None, evidence
    return fifths_seen[0], evidence


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def score_n(counts: Counter) -> list[tuple[int, float]]:
    """Model N, corrected.

    A natural on L is positive evidence that L IS altered by the signature.
    That alone is UNDER-DETERMINED — a natural on B is equally consistent with
    1, 2, 3 … flats, so every one of them ties and the tie-break silently
    invents an answer. What separates them is the other direction: a printed
    FLAT on a letter the signature already flattens is a thing an engraver does
    not do (only a courtesy re-assertion after a natural in the same bar), so
    it is evidence AGAINST that signature.

    A printed flat on a letter the signature does NOT alter is ordinary
    chromaticism and carries no information at all — scored 0, not −1.
    """
    nat = Counter({l: n for (k, l), n in counts.items() if k == "n"})
    flat = Counter({l: n for (k, l), n in counts.items() if k == "b"})
    sharp = Counter({l: n for (k, l), n in counts.items() if k == "#"})
    out = []
    for f in range(-7, 8):
        A = altered_letters(f)
        s = sum(n if l in A else -n for l, n in nat.items())
        contra = flat if f < 0 else (sharp if f > 0 else Counter())
        s -= sum(n for l, n in contra.items() if l in A)
        out.append((f, float(s)))
    out.sort(key=lambda t: (-t[1], abs(t[0])))
    return out


def consistent_fifths(counts: Counter, min_votes: int = 1) -> list[int]:
    """Model C — the abstaining set form, and the one a shipped rule would use.

    Rather than score, ask which signatures the page's evidence is CONSISTENT
    with, and speak only when exactly one survives:

      * every letter carrying a natural must be altered by the signature
      * no letter carrying a printed flat may already be flattened by it
        (same for sharps)

    Returns the surviving fifths, so `len(...) == 1` is the speak condition and
    anything else is an abstention with its reason legible.
    """
    nat = {l for (k, l), n in counts.items() if k == "n" and n >= min_votes}
    flat = {l for (k, l), n in counts.items() if k == "b" and n >= min_votes}
    sharp = {l for (k, l), n in counts.items() if k == "#" and n >= min_votes}
    out = []
    for f in range(-7, 8):
        A = altered_letters(f)
        if not nat <= A:
            continue
        contra = flat if f < 0 else (sharp if f > 0 else set())
        if contra & A:
            continue
        out.append(f)
    return out


def score_f(counts: Counter) -> list[tuple[int, float]]:
    flats = Counter({l: n for (k, l), n in counts.items() if k == "b"})
    sharps = Counter({l: n for (k, l), n in counts.items() if k == "#"})
    out = []
    for f in range(-7, 8):
        A = altered_letters(f)
        if f < 0:
            s = sum(n if l in A else -n for l, n in flats.items())
        elif f > 0:
            s = sum(n if l in A else -n for l, n in sharps.items())
        else:
            s = -sum(flats.values()) - sum(sharps.values())
        out.append((f, float(s)))
    out.sort(key=lambda t: (-t[1], abs(t[0])))
    return out


def verdict(scores: list[tuple[int, float]], truth: int) -> tuple[str, float]:
    """('correct'|'wrong'|'silent', margin).

    Silent when the top score is <= 0 (no positive evidence for anything) OR
    when the top is TIED — a tie is not a reading, and letting the tie-break
    pick is how an under-determined model reports a confident answer. The first
    cut of this probe did exactly that and every margin came back 0.0.
    """
    best_f, best_s = scores[0]
    runner = scores[1][1]
    if best_s <= 0 or best_s == runner:
        return "silent", 0.0
    return ("correct" if best_f == truth else "wrong"), best_s - runner


def verdict_set(surviving: list[int], truth: int) -> str:
    if len(surviving) != 1:
        return "silent"
    return "correct" if surviving[0] == truth else "wrong"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores-dir",
                    default="/Users/seanjohnson/Desktop/gradus-vercel/public/scores")
    ap.add_argument("--works", type=int, default=40)
    ap.add_argument("--window", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--clean-only", action="store_true",
                    help="use only accidentals that are not cancelling "
                         "an earlier accidental in their own bar")
    ap.add_argument("--out", default=str(HERE / "artifacts" / "ceiling.json"))
    args = ap.parse_args()

    files = sorted(Path(args.scores_dir).glob("*.mxl"))
    if not files:
        print(f"no .mxl under {args.scores_dir}")
        sys.exit(1)
    random.Random(args.seed).shuffle(files)
    files = files[: args.works]

    tallies: dict[str, Counter] = defaultdict(Counter)
    margins: dict[str, list[float]] = defaultdict(list)
    evidence: dict[str, list[int]] = defaultdict(list)
    per_work = []

    for f in files:
        root = load_musicxml(f)
        if root is None:
            continue
        rows = []
        for name, part in parts_of(root):
            truth, ev = part_evidence(part)
            if truth is None:
                continue
            rows.append((name, truth, ev))
        if len(rows) < 2:
            continue
        n_meas = max((e[0] for _, _, ev in rows for e in ev), default=0) + 1

        def judge(scope: str, c: Counter, truth: int) -> None:
            for model, fn in (("N", score_n), ("F", score_f)):
                v, m = verdict(fn(c), truth)
                tallies[f"{scope}-{model}"][v] += 1
                if v != "silent":
                    margins[f"{scope}-{model}-{v}"].append(m)
            tallies[f"{scope}-S"][verdict_set(consistent_fifths(c), truth)] += 1
            nat_n = sum(n for (k, _), n in c.items() if k == "n")
            evidence[scope].append(nat_n)

        def tally(ev, lo=None, hi=None) -> Counter:
            return Counter((k, l) for mo, k, l, clean in ev
                           if (clean or not args.clean_only)
                           and (lo is None or lo <= mo < hi))

        # --- A: per part, whole movement
        for name, truth, ev in rows:
            judge("A", tally(ev), truth)

        # --- B: per part, one window
        starts = list(range(0, max(1, n_meas - args.window), args.window))
        for name, truth, ev in rows:
            for s in starts:
                judge("B", tally(ev, s, s + args.window), truth)

        # --- C: pooled over the parts, in CONCERT space, one window
        #     Concert fifths of a part = its written fifths minus its offset;
        #     here the offset is taken from the truth itself (the most
        #     generous possible assumption — see PHASE1.md).
        concert = Counter(truth for _, truth, _ in rows).most_common(1)[0][0]
        for s in starts:
            pooled: Counter = Counter()
            for name, truth, ev in rows:
                shift = truth - concert          # this part's written offset
                for mo, k, l, clean in ev:
                    if not (s <= mo < s + args.window):
                        continue
                    if args.clean_only and not clean:
                        continue
                    # Re-letter the part's evidence into the concert frame.
                    pooled[(k, _shift_letter(l, -shift))] += 1
            judge("C", pooled, concert)

        per_work.append({"file": f.name, "parts": len(rows),
                         "measures": n_meas,
                         "keys": sorted({t for _, t, _ in rows})})

    print(f"\n{len(per_work)} works, "
          f"{sum(w['parts'] for w in per_work)} parts, window {args.window}\n")
    print(f"{'scope':<32} {'correct':>8} {'wrong':>7} {'silent':>7} "
          f"{'acc(spoken)':>12} {'spoke on':>9} {'med margin ok':>14} "
          f"{'med margin wrong':>17}")
    for key in ("A-N", "A-S", "A-F", "B-N", "B-S", "B-F", "C-N", "C-S", "C-F"):
        t = tallies[key]
        spoken = t["correct"] + t["wrong"]
        total = spoken + t["silent"]
        acc = t["correct"] / spoken if spoken else 0.0
        mo = margins.get(f"{key}-correct") or [0]
        mw = margins.get(f"{key}-wrong") or [0]
        label = {"A": "A whole movement, per part",
                 "B": f"B {args.window}-bar window, per part",
                 "C": f"C {args.window}-bar window, pooled"}[key[0]] + f" [{key[-1]}]"
        print(f"{label:<32} {t['correct']:>8} {t['wrong']:>7} {t['silent']:>7} "
              f"{acc:>11.1%} {spoken/total if total else 0:>8.1%} "
              f"{statistics.median(mo):>14.1f} {statistics.median(mw):>17.1f}")

    print("\n-- how much natural evidence there is to work with --")
    for scope in ("A", "B", "C"):
        v = evidence[scope]
        if not v:
            continue
        zero = sum(1 for x in v if x == 0) / len(v)
        print(f"  {scope}: n={len(v):>5}  median naturals {statistics.median(v):>5.1f}  "
              f"mean {statistics.mean(v):>6.2f}  none at all {zero:>6.1%}")

    out = {"works": per_work, "window": args.window,
           "tallies": {k: dict(v) for k, v in tallies.items()},
           "evidence": {k: v for k, v in evidence.items()},
           "margins": {k: v for k, v in margins.items()}}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out))
    print(f"\nwrote {args.out}")


_LETTERS = "CDEFGAB"


def _shift_letter(letter: str, fifths_shift: int) -> str:
    """Move a letter by `fifths_shift` steps of a transposition. A part written
    a fifth higher spells the same sounding note one letter-step up per fifth,
    modulo the octave — this is the diatonic-step shift, which is what matters
    for WHICH LETTER an accidental lands on."""
    if fifths_shift == 0:
        return letter
    i = _LETTERS.index(letter)
    # A transposition of n fifths moves the letter by 4n diatonic steps.
    return _LETTERS[(i + 4 * fifths_shift) % 7]


if __name__ == "__main__":
    main()
