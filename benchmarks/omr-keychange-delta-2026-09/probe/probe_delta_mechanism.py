"""STEP 1b — WHY the shared-delta property fails where it fails.

`probe_shared_delta.py` measures the rate. A rate is not usable on its own:
"holds 95% of the time with a KNOWN, detectable 5%" is a shippable rule and
"holds 95% for unknown reasons" is not. This classifies every disagreeing bar
by mechanism, and it does so in CONCERT space as well as written space —
which is the only way to tell an enharmonic respelling from an encoding that
never transposed its key at all.

The arithmetic, derived rather than tabulated
---------------------------------------------
MusicXML `<transpose>` says *sounding = written + (diatonic steps, chromatic
semitones)*. Put C (fifths 0) through that interval and read off where it
lands on the line of fifths; call that `f_int`. Then

    concert_fifths = written_fifths + f_int        and       offset = -f_int

which reproduces `instruments.fifths_offset` exactly: an instrument in B-flat
sounds (-1, -2), which lands on B-flat, `f_int = -2`, `offset = +2` — the
number `instruments.py` stores.

The buckets, in the order they are tested
-----------------------------------------
ENHARMONIC        the outlier's delta differs from the bar's modal delta by
                  exactly ±12 — the SAME key, spelled the other way round
                  (7 flats vs 5 sharps). The property holds mod 12.
CROOK             `<transpose>` is restated at this very bar. The instrument
                  itself changed; the offsets no longer cancel, by definition.
UNSIGNATURED      the outlier's key on ONE side is 0 while its own transpose
                  says it should not be — horns, trumpets and timpani are
                  historically notated with NO key signature and accidentals.
                  A page fact, not an encoding fault.
CONCERT_PITCH_KEY the outlier's key disagrees with `concert + offset` on BOTH
                  sides — the part carries a `<transpose>` its `<key>` was
                  never adjusted for.
GENUINE           concert keys really do differ across the staves at this bar
                  (bitonality), with every part's key consistent with its own
                  transpose.
UNEXPLAINED       none of the above. This is the bucket that decides whether
                  the rule is usable.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _refs import root                    # noqa: E402  fail-loud
from keys import load_keys                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

#: fifths of each natural step, and its semitone above C.
_STEP_FIFTHS = [0, 2, 4, -1, 1, 3, 5]      # C D E F G A B
_STEP_SEMIS = [0, 2, 4, 5, 7, 9, 11]


def interval_fifths(diatonic: int, chromatic: int) -> int:
    """Where C lands on the line of fifths after `(diatonic, chromatic)`.

    ⚠️ Both components are needed. `chromatic` alone cannot separate a
    diminished fourth from a major third, and those sit five fifths apart.
    """
    step = diatonic % 7
    natural = _STEP_SEMIS[step]
    # Semitones within the octave the diatonic step lands in.
    semis = chromatic - 12 * ((diatonic - step) // 7)
    alter = semis - natural
    # Fold an octave-sized residue away (a +12/-12 leftover is not an alteration)
    while alter > 6:
        alter -= 12
    while alter < -6:
        alter += 12
    return _STEP_FIFTHS[step] + 7 * alter


def classify(sk, event) -> dict:
    staves = sk.staves
    changers = event["changers"]
    delta_counts = Counter(c["delta"] for c in changers)
    modal, modal_n = delta_counts.most_common(1)[0]

    def offset_of(st, ordinal):
        t = st.transpose_at(ordinal)
        if t is None:
            return 0, False
        return -interval_fifths(t[0], t[1]), True

    rows = []
    for c in changers:
        st = staves[c["i"]]
        off_b, has_b = offset_of(st, max(event["ordinal"] - 1, 0))
        off_a, has_a = offset_of(st, event["ordinal"])
        rows.append({
            "part": c["part"], "staff": c["staff"],
            "written_before": c["before"], "written_after": c["after"],
            "delta": c["delta"],
            "offset_before": off_b, "offset_after": off_a,
            "declares_transpose": has_b or has_a,
            "concert_before": c["before"] - off_b,
            "concert_after": c["after"] - off_a,
            "crook": event["ordinal"] in st.transpose and has_b,
        })

    concert_deltas = Counter(r["concert_after"] - r["concert_before"]
                             for r in rows)
    cmodal, cmodal_n = concert_deltas.most_common(1)[0]

    buckets: Counter[str] = Counter()
    outliers = []
    for r in rows:
        if r["delta"] == modal:
            continue
        why = None
        if (r["delta"] - modal) % 12 == 0:
            why = "ENHARMONIC"
        elif r["crook"]:
            why = "CROOK"
        elif (r["concert_after"] - r["concert_before"]) == cmodal:
            # concert space agrees — the written departure is the offsets not
            # cancelling, i.e. one side carried no signature.
            why = "OFFSET_NOT_APPLIED"
        else:
            ok_b = r["written_before"] == r["concert_before"] + r["offset_before"]
            ok_a = r["written_after"] == r["concert_after"] + r["offset_after"]
            # `ok_*` are tautological as written; the real test is against the
            # bar's MODAL concert key, which is what the rest of the score says.
            modal_concert_b = Counter(x["concert_before"] for x in rows
                                      ).most_common(1)[0][0]
            modal_concert_a = Counter(x["concert_after"] for x in rows
                                      ).most_common(1)[0][0]
            unsig_b = (r["written_before"] == 0
                       and modal_concert_b + r["offset_before"] != 0)
            unsig_a = (r["written_after"] == 0
                       and modal_concert_a + r["offset_after"] != 0)
            wrong_b = r["concert_before"] != modal_concert_b
            wrong_a = r["concert_after"] != modal_concert_a
            if unsig_b or unsig_a:
                why = "UNSIGNATURED"
            elif (wrong_b and wrong_a and not r["declares_transpose"]
                  and (r["concert_before"] - modal_concert_b)
                  == (r["concert_after"] - modal_concert_a)):
                why = "GENUINE_DIFFERENT_KEY"
            elif wrong_b and not wrong_a:
                why = "BEFORE_DISAGREES_WITH_SCORE"
            elif wrong_a and not wrong_b:
                why = "AFTER_DISAGREES_WITH_SCORE"
            elif ((r["concert_before"] - modal_concert_b)
                  == (r["concert_after"] - modal_concert_a)):
                why = "GENUINE_DIFFERENT_KEY"
            else:
                why = "UNEXPLAINED"
        buckets[why] += 1
        outliers.append({**r, "why": why, "modal_delta": modal})
    return {
        "modal_delta": modal, "modal_n": modal_n, "n_changing": len(rows),
        "concert_modal_delta": cmodal, "concert_modal_n": cmodal_n,
        "buckets": dict(buckets), "outliers": outliers,
    }


def main() -> int:
    src = os.path.join(OUT, "shared-delta.json")
    if not os.path.isfile(src):
        sys.stderr.write(f"FATAL: {src} missing — run probe_shared_delta.py "
                         f"first.\n")
        return 2
    data = json.load(open(src))
    paths = sorted({w["path"] for w in data["works"]})
    if not paths:
        sys.stderr.write("FATAL: no works with key changes to classify.\n")
        return 2
    sys.stderr.write(f"classifying {len(paths)} works with key changes "
                     f"under {root()}\n")

    disagree_by_path = defaultdict(list)
    for e in data["disagreeing"]:
        disagree_by_path[e["path"]].append(e)

    all_buckets: Counter[str] = Counter()
    bar_buckets: Counter[str] = Counter()
    detail = []
    # Rate in CONCERT space, and the modal-delta share, over every multi-staff
    # bar — not only the disagreeing ones.
    modal_share_num = modal_share_den = 0
    mod12_agree_bars = 0
    concert_agree_bars = 0
    total_multi = 0

    for path in paths:
        sk = load_keys(path)
        from probe_shared_delta import analyse           # noqa: PLC0415
        w = analyse(sk)
        for e in w["events"]:
            if e["n_changing"] < 2:
                continue
            total_multi += 1
            info = classify(sk, e)
            modal_share_num += info["modal_n"]
            modal_share_den += info["n_changing"]
            if len({d % 12 for d in e["deltas"]}) == 1:
                mod12_agree_bars += 1
            if info["concert_modal_n"] == info["n_changing"]:
                concert_agree_bars += 1
            if e["agree"]:
                continue
            for k, v in info["buckets"].items():
                all_buckets[k] += v
            worst = sorted(info["buckets"], key=lambda k: _SEVERITY.index(k)
                           if k in _SEVERITY else 99)[-1] if info["buckets"] else ""
            bar_buckets[worst] += 1
            detail.append({
                "path": os.path.basename(path),
                "measure_number": e["measure_number"],
                "ordinal": e["ordinal"],
                "n_changing": e["n_changing"], "n_staves": e["n_staves"],
                "deltas": e["deltas"], **info,
            })

    print("=" * 72)
    print(f"multi-staff key-change bars classified: {total_multi}")
    print(f"  written deltas identical            : "
          f"{total_multi - len(detail)} / {total_multi} = "
          f"{(total_multi - len(detail))/total_multi:.4f}")
    print(f"  written deltas identical MOD 12     : {mod12_agree_bars} / "
          f"{total_multi} = {mod12_agree_bars/total_multi:.4f}")
    print(f"  CONCERT deltas identical            : {concert_agree_bars} / "
          f"{total_multi} = {concert_agree_bars/total_multi:.4f}")
    print(f"  staves agreeing with their bar's MODAL delta: "
          f"{modal_share_num} / {modal_share_den} = "
          f"{modal_share_num/modal_share_den:.4f}")
    print()
    print("--- outlier STAVES by mechanism")
    for k, v in all_buckets.most_common():
        print(f"  {k:30s} {v}")
    print()
    print("--- disagreeing BARS by worst mechanism present")
    for k, v in bar_buckets.most_common():
        print(f"  {k:30s} {v}")
    print()
    print("--- every UNEXPLAINED outlier, in full")
    n_unexp = 0
    for d in detail:
        for o in d["outliers"]:
            if o["why"] != "UNEXPLAINED":
                continue
            n_unexp += 1
            print(f"  {d['path']} bar#{d['measure_number']} "
                  f"{o['part']}/{o['staff']} "
                  f"written {o['written_before']}->{o['written_after']} "
                  f"(Δ{o['delta']:+d}, modal Δ{o['modal_delta']:+d}) "
                  f"offset {o['offset_before']}/{o['offset_after']} "
                  f"concert {o['concert_before']}->{o['concert_after']}")
    print(f"  ({n_unexp} unexplained outlier staves)")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "delta-mechanism.json"), "w") as fh:
        json.dump({"total_multi_bars": total_multi,
                   "n_disagreeing_bars": len(detail),
                   "mod12_agree_bars": mod12_agree_bars,
                   "concert_agree_bars": concert_agree_bars,
                   "modal_share": [modal_share_num, modal_share_den],
                   "outlier_buckets": dict(all_buckets),
                   "bar_buckets": dict(bar_buckets),
                   "detail": detail}, fh, indent=1)
    print(f"\nwrote {OUT}/delta-mechanism.json")
    return 0


#: worst-last, for naming a bar by the most serious thing in it
_SEVERITY = ["ENHARMONIC", "CROOK", "OFFSET_NOT_APPLIED", "UNSIGNATURED",
             "BEFORE_DISAGREES_WITH_SCORE", "AFTER_DISAGREES_WITH_SCORE",
             "CONCERT_PITCH_KEY", "GENUINE_DIFFERENT_KEY", "UNEXPLAINED"]


if __name__ == "__main__":
    raise SystemExit(main())
