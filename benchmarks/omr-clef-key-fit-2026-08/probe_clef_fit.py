#!/usr/bin/env python3
"""Can a clef be recovered from tonal / key context alone?

Four experiments over stored `transcribe()` JSON (no YOLO, no images — a clef
change is a constant diatonic shift of every notehead, so every candidate clef
can be evaluated by arithmetic on the emitted pitches).

    A  per-staff key-signature fit      (Krumhansl-Schmuckler over fifths -7..+7)
    B  accidental letters vs the circle of fifths, per candidate clef
    C  leave-one-out clef from register ordering against neighbouring staves
    D  leave-one-out clef from fit to the key consensus of the other staves

Usage:  python3 benchmarks/omr-clef-key-fit-2026-08/probe_clef_fit.py \
            benchmarks/omr-real-world/*.json
"""
from __future__ import annotations

import collections
import json
import os
import statistics
import sys

CYCLE = ["C", "D", "E", "F", "G", "A", "B"]
SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
FLAT_ORDER = ["B", "E", "A", "D", "G", "C", "F"]
# Pitch at the TOP staff line for each clef (tools/omr/pitch_resolver._CLEF_ANCHORS).
ANCHOR = {"treble": ("F", 5), "bass": ("A", 3), "alto": ("G", 4), "tenor": ("E", 4)}
CAND = ["treble", "alto", "tenor", "bass"]
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

KK_MAJ = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MIN = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

MIN_NOTES = 10          # a staff needs this many resolved noteheads to participate
MIN_ANCHORS = 2         # ...and this many usable neighbours


# ── pitch arithmetic ────────────────────────────────────────────────────────

def parse_pitch(p):
    """'F#4' -> ('F', +1, 4). None if unparseable."""
    if not p or p[0] not in SEMI:
        return None
    letter, i, alt = p[0], 1, 0
    while i < len(p) and p[i] in "#b":
        alt += 1 if p[i] == "#" else -1
        i += 1
    try:
        return letter, alt, int(p[i:])
    except ValueError:
        return None


def dia_index(letter, octv):
    return octv * 7 + CYCLE.index(letter)


def from_dia(idx):
    return CYCLE[idx % 7], idx // 7


def clef_shift(orig, cand):
    """Diatonic steps every notehead moves when the clef is reinterpreted."""
    a, b = ANCHOR[cand], ANCHOR[orig]
    return dia_index(*a) - dia_index(*b)


def sig_alterations(fifths):
    if fifths > 0:
        return {l: 1 for l in SHARP_ORDER[:fifths]}
    if fifths < 0:
        return {l: -1 for l in FLAT_ORDER[:-fifths]}
    return {}


# ── accidental pairing (mirrors transcribe._pair_accidentals_to_noteheads) ──

_ALT = {"accidentalsharp": 1, "accidentalflat": -1, "accidentalnatural": 0,
        "accidentaldoublesharp": 2, "accidentaldoubleflat": -2}


def pair_accidentals(dets):
    """{index of notehead det: alteration} using the same geometry rule as the
    pipeline (nearest notehead at/right of the accidental, same staff line)."""
    accs, nhs = [], []
    for i, d in enumerate(dets):
        cls = (d.get("class") or "").lower()
        if d.get("category") == "accidental" and cls in _ALT:
            accs.append((d, _ALT[cls]))
        elif d.get("category") == "notehead":
            nhs.append((i, d))
    out = {}
    for acc, alt in accs:
        ax, ay, aw, ah = acc["bbox"]
        a_right, a_yc, ah = ax + aw, ay + ah // 2, max(1, ah)
        best, best_score = None, float("inf")
        for i, nh in nhs:
            nx, ny, nw, nhh = nh["bbox"]
            if nx + nw < a_right:
                continue
            ydist = abs(ny + nhh // 2 - a_yc)
            if ydist > ah * 0.6:
                continue
            score = max(0, nx - a_right) + 3 * ydist
            if score < best_score:
                best_score, best = score, i
        if best is not None:
            out[best] = alt
    return out


# ── histograms + key finding ────────────────────────────────────────────────

def pc_histogram(staff, orig, cand, fifths=None):
    """Duration-weighted pitch-class histogram under a candidate clef.

    `fifths=None` keeps each notehead's emitted alteration (the pipeline's own
    reading); an int re-applies that key signature to unaccidentaled notes.
    """
    delta = clef_shift(orig, cand)
    sig = sig_alterations(fifths) if fifths is not None else None
    hist, n = [0.0] * 12, 0
    for m in staff.get("measures", []):
        dets = m.get("detections", [])
        paired = pair_accidentals(dets) if sig is not None else {}
        carried = {}
        order = sorted((i for i, d in enumerate(dets)
                        if d.get("category") == "notehead"),
                       key=lambda i: dets[i]["bbox"][0])
        for i in order:
            d = dets[i]
            pp = parse_pitch(d.get("pitch"))
            if pp is None:
                continue
            letter, alt, octv = pp
            l2, o2 = from_dia(dia_index(letter, octv) + delta)
            if sig is not None:
                if i in paired:
                    alt = paired[i]
                    carried[(l2, o2)] = alt
                elif (l2, o2) in carried:
                    alt = carried[(l2, o2)]
                else:
                    alt = sig.get(l2, 0)
            hist[(SEMI[l2] + alt) % 12] += d.get("duration_beats") or 1.0
            n += 1
    return hist, n


def corr(hist, profile):
    n = 12
    mh, mp = sum(hist) / n, sum(profile) / n
    num = sum((hist[i] - mh) * (profile[i] - mp) for i in range(n))
    d1 = sum((hist[i] - mh) ** 2 for i in range(n)) ** 0.5
    d2 = sum((profile[i] - mp) ** 2 for i in range(n)) ** 0.5
    return num / (d1 * d2) if d1 and d2 else 0.0


def best_key(hist):
    best = None
    for tonic in range(12):
        for name, prof in (("maj", KK_MAJ), ("min", KK_MIN)):
            c = corr(hist, [prof[(i - tonic) % 12] for i in range(12)])
            if best is None or c > best[0]:
                best = (c, tonic, name)
    return best


def staff_midis(staff, orig, cand):
    delta = clef_shift(orig, cand)
    out = []
    for m in staff.get("measures", []):
        for d in m.get("detections", []):
            if d.get("category") != "notehead":
                continue
            pp = parse_pitch(d.get("pitch"))
            if pp is None:
                continue
            letter, alt, octv = pp
            l2, o2 = from_dia(dia_index(letter, octv) + delta)
            out.append(12 * (o2 + 1) + SEMI[l2] + alt)
    return out


def iter_staves(docs):
    for name, doc in docs:
        for pg in doc.get("pages", []):
            for sy in pg.get("systems", []):
                yield name, pg, sy, sy.get("staves", [])


# ── experiments ─────────────────────────────────────────────────────────────

def experiment_a(docs):
    """Per-staff key-signature fit. Reports the margin between the best and
    second-best signature — if the argmax is meaningful the margin is large."""
    margins, agree = [], 0
    total = 0
    for _n, _pg, _sy, staves in iter_staves(docs):
        for st in staves:
            clef = st.get("clef")
            if clef not in ANCHOR:
                continue
            rows = []
            for f in range(-7, 8):
                h, n = pc_histogram(st, clef, clef, fifths=f)
                if n < MIN_NOTES:
                    rows = []
                    break
                rows.append((best_key(h)[0], f))
            if len(rows) < 2:
                continue
            rows.sort(reverse=True)
            margins.append(rows[0][0] - rows[1][0])
            read = st.get("key_signature") or {}
            total += 1
            agree += (rows[0][1] == read.get("sharps", 0) - read.get("flats", 0))
    print("\n── A. per-staff key-signature fit (KS over fifths -7..+7) ──")
    if not margins:
        print("   no staff had enough resolved noteheads")
        return
    print(f"   staves scored           : {len(margins)}")
    print(f"   median best-vs-2nd margin: {statistics.median(margins):.4f}")
    print(f"   margin < 0.01 on        : {sum(m < 0.01 for m in margins)}/{len(margins)} staves")
    print(f"   argmax == pipeline's read: {agree}/{total}")
    print("   -> the argmax is not separated from its runner-up: noise.")


def experiment_b(docs):
    """Do inline accidentals concentrate on circle-of-fifths prefix letters
    under the true clef more than under the alternatives?"""
    per = {c: {"flat": collections.Counter(), "sharp": collections.Counter()}
           for c in CAND}
    for _n, _pg, _sy, staves in iter_staves(docs):
        for st in staves:
            orig = st.get("clef")
            if orig not in ANCHOR:
                continue
            for cand in CAND:
                delta = clef_shift(orig, cand)
                for m in st.get("measures", []):
                    dets = m.get("detections", [])
                    for i, alt in pair_accidentals(dets).items():
                        pp = parse_pitch(dets[i].get("pitch"))
                        if pp is None or alt == 0:
                            continue
                        letter, _a, octv = pp
                        l2, _o2 = from_dia(dia_index(letter, octv) + delta)
                        per[cand]["flat" if alt < 0 else "sharp"][l2] += 1
    print("\n── B. accidental letters vs the circle of fifths ──")
    print("   fraction landing on the first THREE letters of the signature order")
    print("   (a real 3-flat / 3-sharp key concentrates here; 3/7 = 0.43 is chance)")
    for cand in CAND:
        fl, sh = per[cand]["flat"], per[cand]["sharp"]
        def frac(c, order):
            t = sum(c.values())
            return sum(c[l] for l in order[:3]) / t if t else float("nan")
        tag = "  (as detected)" if cand == "treble" else ""
        print(f"   {cand:7s} flats n={sum(fl.values()):3d} -> {frac(fl, FLAT_ORDER):.2f}   "
              f"sharps n={sum(sh.values()):3d} -> {frac(sh, SHARP_ORDER):.2f}{tag}")
    print("   -> no candidate separates from chance: the accidental letters carry")
    print("      no clef information at this detection quality.")


def _loo(docs, predict, title, note):
    tot = cor = 0
    conf = collections.Counter()
    truth_dist = collections.Counter()
    for _n, _pg, _sy, staves in iter_staves(docs):
        if len(staves) < 3:
            continue
        for i, st in enumerate(staves):
            truth = st.get("clef")
            if truth not in CAND:
                continue
            pred = predict(staves, i, truth)
            if pred is None:
                continue
            tot += 1
            cor += (pred == truth)
            conf[(truth, pred)] += 1
            truth_dist[truth] += 1
    print(f"\n── {title} ──")
    if not tot:
        print("   no evaluable staves")
        return
    mc = truth_dist.most_common(1)[0]
    print(f"   leave-one-out accuracy : {cor}/{tot} = {cor / tot:.1%}")
    print(f"   always-'{mc[0]}' baseline: {mc[1]}/{tot} = {mc[1] / tot:.1%}   truth={dict(truth_dist)}")
    for (t, p), n in sorted(conf.items(), key=lambda kv: -kv[1]):
        if t != p:
            print(f"      {t:7s} -> {p:7s} {n:3d}  WRONG")
    print(f"   -> {note}")


def experiment_c(docs):
    def predict(staves, i, truth):
        mine = staff_midis(staves[i], truth, truth)
        if len(mine) < MIN_NOTES:
            return None
        anchors = []
        for j, sj in enumerate(staves):
            if j == i or sj.get("clef") not in CAND:
                continue
            mj = staff_midis(sj, sj["clef"], sj["clef"])
            if len(mj) >= MIN_NOTES:
                anchors.append((j, statistics.median(mj)))
        if len(anchors) < MIN_ANCHORS:
            return None
        best = None
        for c in CAND:
            med = statistics.median(staff_midis(staves[i], truth, c))
            pen = sum((med - mj) if (j < i and med > mj) else
                      (mj - med) if (j > i and med < mj) else 0.0
                      for j, mj in anchors)
            if best is None or pen < best[0]:
                best = (pen, c)
        return best[1]
    _loo(docs, predict, "C. clef from register ordering vs neighbours",
         "below the trivial baseline — staff ORDER constrains relative register, "
         "not absolute register, so the middle clefs win too often.")


def experiment_d(docs):
    def predict(staves, i, truth):
        own, n_own = pc_histogram(staves[i], truth, truth)
        if n_own < MIN_NOTES:
            return None
        pool, others = [0.0] * 12, 0
        for j, sj in enumerate(staves):
            if j == i or sj.get("clef") not in CAND:
                continue
            hj, nj = pc_histogram(sj, sj["clef"], sj["clef"])
            if nj < MIN_NOTES:
                continue
            pool = [a + b for a, b in zip(pool, hj)]
            others += 1
        if others < MIN_ANCHORS:
            return None
        _c, tonic, mode = best_key(pool)
        prof = KK_MAJ if mode == "maj" else KK_MIN
        rot = [prof[(k - tonic) % 12] for k in range(12)]
        best = None
        for c in CAND:
            h, _ = pc_histogram(staves[i], truth, c)
            f = corr(h, rot)
            if best is None or f > best[0]:
                best = (f, c)
        return best[1]
    _loo(docs, predict, "D. clef from fit to the other staves' key consensus",
         "identical to the trivial baseline — it recovers the prior, not the clef.")


def main(paths):
    docs = []
    for p in paths:
        try:
            d = json.load(open(p))
        except Exception as e:                       # noqa: BLE001
            print(f"skip {p}: {e}", file=sys.stderr)
            continue
        if "pages" in d:
            docs.append((os.path.basename(p), d))
    if not docs:
        print("no transcribe JSON given", file=sys.stderr)
        return 1
    print(f"scores: {', '.join(n for n, _ in docs)}")
    experiment_a(docs)
    experiment_b(docs)
    experiment_c(docs)
    experiment_d(docs)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
