"""What evidence about a key signature is actually on a page — and where it sits.

Phase 1 of "infer the key signature from the music" (roadmap #4b / handoff #9).
This probe does NOT infer anything. It separates the two things that a naive
count of "inline flat detections" fuses together, because the whole question
turns on the difference:

  * **signature-region** accidentals — detections in the staff-start cell that
    stand LEFT of that cell's first notehead. Those are the printed key
    signature. `benchmarks/omr-keysig-blindspot-2026-08/` showed the detector
    reads them as `accidentalFlat` rather than `keyFlat`, so they are discarded
    by every key reader and then counted by anyone grepping for flats.
  * **inline** accidentals — everything else. Those are the music's own
    chromaticism, and they are the only thing an inference layer could use.

For inline accidentals the LETTER is taken from the notehead the accidental
alters, not from the glyph's own y — a flat's bowl is centred while its
ascender rises a space above, so a glyph-anchored letter is a calibration
problem this probe does not need to have. Pairing replicates
`transcribe._pair_accidentals_to_noteheads` (same rule, read off the JSON).

    python3 benchmarks/omr-keysig-from-music-2026-09/probe_keysig_signal.py \
        --pdf <score.pdf> --page 15 --dpi 600 --label beet5-p15

Transcriptions are cached under `artifacts/<label>.omr.json`; re-running is
free. `--summarize` re-reads every cached artifact without touching the model.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"
ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = ROOT / "tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"

# Circle-of-fifths accidental order. Index i is the letter altered by the
# (i+1)-th accidental of a signature.
FLAT_ORDER = "BEADGCF"
SHARP_ORDER = "FCGDAEB"


def altered_letters(fifths: int) -> set[str]:
    if fifths > 0:
        return set(SHARP_ORDER[:fifths])
    if fifths < 0:
        return set(FLAT_ORDER[: -fifths])
    return set()


def fifths_name(f: int) -> str:
    if f > 0:
        return f"{f}#"
    if f < 0:
        return f"{-f}b"
    return "0"


# --------------------------------------------------------------------------
# transcription
# --------------------------------------------------------------------------

def transcribe_cached(pdf: Path, page: int, dpi: int, label: str,
                      force: bool = False) -> dict:
    out = ART / f"{label}.omr.json"
    if out.exists() and not force:
        return json.loads(out.read_text())
    from tools.omr.transcribe import transcribe  # noqa: E402
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    res = transcribe(pdf_path=pdf, pages=[page], weights=WEIGHTS, dpi=dpi)
    res["_probe"] = {"pdf": str(pdf), "page": page, "dpi": dpi,
                     "seconds": round(time.time() - t0, 1)}
    out.write_text(json.dumps(res, default=str))
    print(f"  transcribed in {res['_probe']['seconds']}s -> {out}")
    return res


# --------------------------------------------------------------------------
# per-staff evidence extraction
# --------------------------------------------------------------------------

def _acc_kind(cls: str) -> str | None:
    s = (cls or "").lower()
    if not (s.startswith("accidental") or s in {"keyflat", "keysharp", "keynatural"}):
        return None
    if "double" in s:
        return None            # rare; not evidence about a signature
    if "sharp" in s:
        return "#"
    if "flat" in s:
        return "b"
    if "natural" in s:
        return "n"
    return None


def _pair(acc: dict, noteheads: list[dict]) -> dict | None:
    """transcribe._pair_accidentals_to_noteheads, replayed on JSON bboxes."""
    ax, ay, aw, ah = acc["bbox"]
    acc_right, acc_cy, acc_h = ax + aw, ay + ah / 2.0, max(1.0, ah)
    best, best_score = None, float("inf")
    for nh in noteheads:
        nx, ny, nw, nh_h = nh["bbox"]
        if nx + nw < acc_right:
            continue
        ncy = ny + nh_h / 2.0
        ydist = abs(ncy - acc_cy)
        if ydist > acc_h * 0.6:
            continue
        score = max(0.0, nx - acc_right) + 3 * ydist
        if score < best_score:
            best_score, best = score, nh
    return best


def staff_evidence(staff: dict) -> dict:
    """Split one staff's accidental detections into signature-region and
    inline, and give each inline one the letter of the note it alters."""
    sig_region: Counter = Counter()      # kind -> n
    sig_region_dets: list[dict] = []
    inline: Counter = Counter()          # (kind, letter) -> n
    unpaired: Counter = Counter()        # kind -> n  (no notehead found)
    n_noteheads = 0

    for mi, m in enumerate(staff.get("measures") or []):
        dets = m.get("detections") or []
        noteheads = [d for d in dets if d.get("category") == "notehead"]
        n_noteheads += len(noteheads)
        accs = [(d, k) for d in dets if (k := _acc_kind(d.get("class", ""))) is not None]
        if not accs:
            continue
        # The signature region exists only in the staff-start cell, and only
        # left of that cell's first notehead.
        first_nh_x = min((n["bbox"][0] for n in noteheads), default=None)
        for d, kind in accs:
            x, _, w, _ = d["bbox"]
            in_sig = (mi == 0 and (first_nh_x is None or x + w <= first_nh_x))
            if in_sig:
                sig_region[kind] += 1
                sig_region_dets.append(d)
                continue
            nh = _pair(d, noteheads)
            if nh is None:
                unpaired[kind] += 1
                continue
            pitch = nh.get("pitch") or ""
            letter = pitch[0] if pitch and pitch[0] in "ABCDEFG" else None
            if letter is None:
                unpaired[kind] += 1
                continue
            inline[(kind, letter)] += 1

    ks = staff.get("key_signature") or {}
    fifths = int(ks.get("sharps") or 0) - int(ks.get("flats") or 0)
    return {
        "staff_index": staff.get("staff_index"),
        "clef": staff.get("clef"),
        "clef_source": staff.get("clef_source"),
        "part": (staff.get("part") or {}).get("instrument") if isinstance(staff.get("part"), dict) else staff.get("instrument"),
        "fifths": fifths,
        "key_read": bool(staff.get("key_signature_read")),
        "key_source": staff.get("key_signature_source"),
        "key_reason": staff.get("key_signature_reason"),
        "key_unread_reason": staff.get("key_signature_unread_reason"),
        "n_noteheads": n_noteheads,
        "sig_region": dict(sig_region),
        "sig_region_dets": sig_region_dets,
        "inline": {f"{k}:{l}": n for (k, l), n in sorted(inline.items())},
        "inline_raw": inline,
        "unpaired": dict(unpaired),
    }


def page_staves(result: dict) -> list[tuple[int, int, dict]]:
    """(system_index, ordinal, staff) for every staff on the (single) page."""
    out = []
    for pg in result.get("pages", []):
        for sysm in pg.get("systems", []):
            for ordinal, st in enumerate(sysm.get("staves", [])):
                out.append((sysm.get("system_index", 0), ordinal, st))
    return out


# --------------------------------------------------------------------------
# scoring a key hypothesis from inline evidence
# --------------------------------------------------------------------------

def score_naturals(inline: Counter, lo: int = -7, hi: int = 7) -> list[tuple[int, float]]:
    """Model N. A natural exists to CANCEL something. A natural on letter L is
    evidence that L is altered by the signature; a natural on a letter the
    signature does not alter is only explicable as an in-bar cancellation, and
    counts against.

    Returns [(fifths, score)] sorted best first.
    """
    nat = Counter({l: n for (k, l), n in inline.items() if k == "n"})
    scores = []
    for f in range(lo, hi + 1):
        A = altered_letters(f)
        s = sum(n if l in A else -n for l, n in nat.items())
        scores.append((f, float(s)))
    scores.sort(key=lambda t: (-t[1], abs(t[0])))
    return scores


def score_flats(inline: Counter, lo: int = -7, hi: int = 7) -> list[tuple[int, float]]:
    """Model F — the hypothesis the roadmap states: a missed 3-flat signature
    shows as systematic inline flats on B/E/A. Scored the way that sentence
    reads: a flat on a letter the signature would flatten supports it.
    """
    flats = Counter({l: n for (k, l), n in inline.items() if k == "b"})
    sharps = Counter({l: n for (k, l), n in inline.items() if k == "#"})
    scores = []
    for f in range(lo, hi + 1):
        A = altered_letters(f)
        if f < 0:
            s = sum(n if l in A else -n for l, n in flats.items())
        elif f > 0:
            s = sum(n if l in A else -n for l, n in sharps.items())
        else:
            s = -sum(flats.values()) - sum(sharps.values())
        scores.append((f, float(s)))
    scores.sort(key=lambda t: (-t[1], abs(t[0])))
    return scores


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def report(label: str, result: dict) -> dict:
    rows = []
    for sysi, ordinal, st in page_staves(result):
        ev = staff_evidence(st)
        ev["system"] = sysi
        ev["ordinal"] = ordinal
        rows.append(ev)

    print(f"\n{'='*100}\n{label}  —  {len(rows)} staves\n{'='*100}")
    hdr = (f"{'sys':>3} {'ord':>3} {'clef':>7} {'csrc':>10} {'key':>5} "
           f"{'rd':>2} {'ksrc':>14} {'nh':>4} {'sigreg':>14} {'inline':>34}")
    print(hdr)
    for r in rows:
        sig = ",".join(f"{k}x{v}" for k, v in sorted(r["sig_region"].items())) or "-"
        inl = ",".join(f"{k}x{v}" for k, v in sorted(r["inline"].items())) or "-"
        print(f"{r['system']:>3} {r['ordinal']:>3} {str(r['clef'])[:7]:>7} "
              f"{str(r['clef_source'] or '-')[:10]:>10} {fifths_name(r['fifths']):>5} "
              f"{'Y' if r['key_read'] else 'n':>2} {str(r['key_source'] or '-')[:14]:>14} "
              f"{r['n_noteheads']:>4} {sig[:14]:>14} {inl[:34]:>34}")

    pooled: Counter = Counter()
    pooled_sig: Counter = Counter()
    for r in rows:
        pooled.update(r["inline_raw"])
        pooled_sig.update(r["sig_region"])

    print(f"\n-- pooled over the page --")
    print(f"  signature-region accidentals: {dict(pooled_sig)}")
    for kind, name in (("b", "flat"), ("#", "sharp"), ("n", "natural")):
        d = {l: n for (k, l), n in sorted(pooled.items()) if k == kind}
        print(f"  inline {name:<8}: total {sum(d.values()):>4}   by letter {d}")

    nat = score_naturals(pooled)
    fl = score_flats(pooled)
    print(f"\n  Model N (naturals cancel the signature): "
          f"best {fifths_name(nat[0][0])} = {nat[0][1]:.0f}, "
          f"runner-up {fifths_name(nat[1][0])} = {nat[1][1]:.0f}, "
          f"margin {nat[0][1]-nat[1][1]:.0f}")
    print(f"  Model F (inline flats on the signature letters): "
          f"best {fifths_name(fl[0][0])} = {fl[0][1]:.0f}, "
          f"runner-up {fifths_name(fl[1][0])} = {fl[1][1]:.0f}, "
          f"margin {fl[0][1]-fl[1][1]:.0f}")
    print(f"  full N ladder: " + "  ".join(
        f"{fifths_name(f)}:{s:.0f}" for f, s in sorted(nat, key=lambda t: t[0])))

    out = {"label": label, "staves": [
        {k: v for k, v in r.items() if k not in ("inline_raw", "sig_region_dets")}
        for r in rows]}
    out["pooled_inline"] = {f"{k}:{l}": n for (k, l), n in sorted(pooled.items())}
    out["pooled_sig_region"] = dict(pooled_sig)
    out["model_n"] = nat
    out["model_f"] = fl
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf")
    ap.add_argument("--page", type=int)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--label", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    cached = ART / f"{args.label}.omr.json"
    if cached.exists() and not args.force:
        result = json.loads(cached.read_text())
    else:
        result = transcribe_cached(Path(args.pdf), args.page, args.dpi,
                                   args.label, args.force)
    summary = report(args.label, result)
    (HERE / "artifacts" / f"{args.label}.signal.json").write_text(
        json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
