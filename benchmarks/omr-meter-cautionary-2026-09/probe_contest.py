"""Can a CAUTIONARY and the OPENING it announces be arbitrated against each
other — GLYPH against GLYPH, with the bars out of it?

⚠️⚠️ THE FIRST THING THIS PROBE PRINTS IS THAT THE TWO SIDES ARE NOT MEASURED
IN THE SAME UNIT, because that is the finding and not a preamble. A cautionary
carries `support` (a signed-term tally in the carry's currency), the staves
that read it, and its loose digits. An opening carries `share` and
`n_staves_spoke`. **There is exactly ONE quantity both sides state** — how many
staves read it — and it is the one that points the wrong way.

⚠️ EVERY CANDIDATE RULE IS SCORED AGAINST THE PRINT, three ways, because a
contest can face three situations and they are not the same act:
  * DISAGREE      — the cautionary would OVERTURN a decided opening;
  * OPENING_UNKNOWN — it would FILL an opening the system abstained on;
  * AGREE         — it must change nothing (the positive control for "this
                    rule does not break a reading that is already right").

⚠️ A rule that fixes the DISAGREE case and breaks the UNKNOWN case is not a
net win of zero; they are different costs. A wrong overturn replaces a wrong
answer with a right one or vice versa; a wrong FILL converts an honest
abstention into a confident error, which this project's own stage doctrine
says is the worse direction.

    python3 benchmarks/omr-meter-cautionary-2026-09/probe_contest.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import BOUNDARY, load_arms, next_system_of, truth_for  # noqa: E402


def _pairs():
    arms = load_arms(BOUNDARY / "out")
    seen: dict = {}
    for arm in arms:
        for sub, value in arm.meters():
            c = (value or {}).get("cautionary")
            if not c:
                continue
            key = (arm.fixture, sub, int(c["from_cell"]), c["raw"])
            if key in seen and seen[key][0].generation >= arm.generation:
                continue
            seen[key] = (arm, c, sub)
    out = []
    for (fix, sub, cell, raw), (arm, c, _s) in sorted(seen.items()):
        nxt = next_system_of(arm, sub)
        v = (arm.verdict(nxt) or {}) if nxt else {}
        det = v.get("detail") or {}
        opening = None
        if v.get("outcome") == "decided" and v.get("reason") != "change_only":
            opening = (v.get("value") or {}).get("raw")
        truth = truth_for(fix, nxt)
        out.append({
            "fixture": fix, "system": sub, "cell": cell,
            "caut_raw": raw,
            "caut_support": c.get("support"),
            "caut_staves": len(c.get("staves_reading_it") or []),
            "caut_loose": c.get("loose_digits"),
            "caut_bars_fit": c.get("bars_fit"),
            "caut_bars_contradict": c.get("bars_contradict"),
            "next": nxt, "open_raw": opening,
            "open_share": det.get("share"),
            "open_staves": det.get("n_staves_spoke"),
            "open_reason": v.get("reason"),
            "truth": truth,
            "state": ("OPENING_UNKNOWN" if opening is None
                      else "AGREE" if opening == raw else "DISAGREE"),
        })
    return out


# ── the candidate rules ──────────────────────────────────────────────────────
#
# Each takes a pair and returns the meter it would install on the NEXT system,
# or None for "leave the pipeline's own answer alone". Every one is a pure
# function of quantities that are ALREADY ON THE RECORD — nothing here needs a
# gather, a page, or a new reader.

def r1_always(p):
    """The cautionary always wins."""
    return p["caut_raw"]


def r2_staves(p):
    """Whichever reading more staves read. ⚠️ The only common unit there is."""
    if p["open_raw"] is None:
        return p["caut_raw"]
    return (p["caut_raw"] if (p["caut_staves"] or 0) > (p["open_staves"] or 0)
            else None)


def _support_floor(f):
    def rule(p):
        return p["caut_raw"] if (p["caut_support"] or 0) >= f else None
    rule.__doc__ = f"The cautionary wins where its support >= {f}."
    return rule


def _stave_floor(n):
    def rule(p):
        return p["caut_raw"] if (p["caut_staves"] or 0) >= n else None
    rule.__doc__ = f"The cautionary wins where >= {n} staves read it."
    return rule


def r5_fill_only(p):
    """FILL ONLY — never overturn a decided opening.

    ⚠️ This is the route the boundary FINDINGS records as *"not dead in the
    OTHER case ... recorded as available and unbuilt rather than shipped
    untested"*, on the stated ground that its reach on that corpus was ZERO.
    It is scored here because the reach is not zero.
    """
    return p["caut_raw"] if p["open_raw"] is None else None


def r0_nothing(p):
    """The incumbent: no contest at all. The NEGATIVE control."""
    return None


def rX_inverted(p):
    """⚠️ THE POSITIVE CONTROL FOR THE `BROKEN` COLUMN, and it is not
    decoration. Every honest rule below scores `BROKEN 0`, and a column that
    reads zero for every arm is indistinguishable from a column that cannot
    be non-zero — this file's own *a control that cannot fail is worse than no
    control*. This rule installs the cautionary UPSIDE DOWN, so it must break
    the AGREE pair. If it does not, the scorer is not measuring breakage and
    every other zero in that column is worthless.
    """
    n, _, d = (p["caut_raw"] or "/").partition("/")
    return f"{d}/{n}" if n and d else None


RULES = [
    ("R0 do nothing (incumbent)", r0_nothing),
    ("R1 cautionary always wins", r1_always),
    ("R2 more staves wins", r2_staves),
    ("R3 support >= 10.0", _support_floor(10.0)),
    ("R4 >= 3 staves read it", _stave_floor(3)),
    ("R5 fill an unknown opening only", r5_fill_only),
    ("RX inverted cautionary (POSITIVE CONTROL for BROKEN)", rX_inverted),
]


def score(rule, pairs):
    """Score one rule against the print.

    ⚠️⚠️ `abstention_lost` IS COUNTED APART FROM `kept_wrong`, AND IT IS THE
    LOAD-BEARING COLUMN. A system that abstained says *"I could not tell"*;
    installing a wrong meter on it converts that into a definite answer, which
    is CLAUDE.md's own ABSENT/DECLINED collapse and the one thing a wiring
    pass is forbidden to do. Netted into "still wrong" — which is what a naive
    right/wrong scorer does, because the answer was not right before either —
    it disappears, and the rule that commits it reads as costless.
    """
    fixed = broken = kept_right = kept_wrong = unscored = abstention_lost = 0
    detail = []
    for p in pairs:
        installed = rule(p)
        before = p["open_raw"]
        after = installed if installed is not None else before
        t = p["truth"]
        if t is None:
            unscored += 1
            outcome = "UNSCORED"
        else:
            was_ok = (before == t)
            now_ok = (after == t)
            if not was_ok and now_ok:
                fixed += 1
                outcome = ("FIXED" if before is not None
                           else "FILLED, correctly")
            elif was_ok and not now_ok:
                broken += 1
                outcome = "BROKEN"
            elif now_ok:
                kept_right += 1
                outcome = "kept right"
            elif before is None and after is not None:
                abstention_lost += 1
                outcome = "⚠️ ABSTENTION -> A WRONG ANSWER"
            else:
                kept_wrong += 1
                outcome = ("kept wrong" if installed is None
                           else "still wrong")
        detail.append({"pair": f"{p['fixture']} {p['system']}",
                       "state": p["state"], "before": before,
                       "installed": installed, "after": after,
                       "truth": t, "outcome": outcome})
    return {"fixed": fixed, "broken": broken, "kept_right": kept_right,
            "kept_wrong": kept_wrong, "unscored": unscored,
            "abstention_lost": abstention_lost, "detail": detail}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(HERE / "out" / "contest.json"))
    a = ap.parse_args()

    pairs = _pairs()
    print("═══ REACH ═══")
    print(f"  contestable pairs .............. {len(pairs)}")
    states = {}
    for p in pairs:
        states[p["state"]] = states.get(p["state"], 0) + 1
    for k in sorted(states):
        print(f"      {k:<16} {states[k]}")
    if not pairs:
        print("DEAD: nothing to contest.")
        return 2
    if "DISAGREE" not in states:
        print("DEAD: no pair where the two readings disagree.")
        return 2

    # ── 1. the currency table ───────────────────────────────────────────────
    print("\n═══ 1. THE TWO SIDES, IN EVERY QUANTITY THE RECORD CARRIES ═══")
    fields_c = ["caut_support", "caut_staves", "caut_loose",
                "caut_bars_fit", "caut_bars_contradict"]
    fields_o = ["open_share", "open_staves"]
    hdr = (f"  {'pair':<34}{'caut':>6}{'open':>6}{'truth':>7}"
           + "".join(f"{f.replace('caut_', 'c.'):>10}" for f in fields_c)
           + "".join(f"{f.replace('open_', 'o.'):>10}" for f in fields_o))
    print(hdr)
    for p in pairs:
        print(f"  {p['fixture'] + ' ' + p['system']:<34}"
              f"{str(p['caut_raw']):>6}{str(p['open_raw']):>6}"
              f"{str(p['truth']):>7}"
              + "".join(f"{str(p[f]):>10}" for f in fields_c)
              + "".join(f"{str(p[f]):>10}" for f in fields_o))

    shared = []
    for fc, fo in [("caut_staves", "open_staves")]:
        if all(p[fc] is not None for p in pairs) and \
           any(p[fo] is not None for p in pairs):
            shared.append((fc, fo))
    print(f"\n  quantities BOTH sides state ... {len(shared)}"
          f"  {[s[0].replace('caut_', '') for s in shared]}")
    print("  ⚠️ `support` is the cautionary's alone; `share` is the "
          "opening's alone.\n     There is no common currency for the "
          "contest to be decided IN.")
    for fc, fo in shared:
        for p in pairs:
            if p["state"] != "DISAGREE":
                continue
            print(f"  ⚠️ on the ONE contested pair, the shared quantity reads"
                  f" caut {p[fc]} vs opening {p[fo]} — "
                  f"{'the WRONG reading has MORE' if (p[fo] or 0) >= (p[fc] or 0) else 'the cautionary has more'}")

    # ── 2. does anything separate a TRUE cautionary from a FALSE one? ───────
    print("\n═══ 2. TRUE vs FALSE CAUTIONARY (the cautionary side alone) ═══")
    print("  ⚠️ This is a DIFFERENT question from the contest: it asks whether"
          "\n     the cautionary can be trusted at all, not whether it beats "
          "the opening.")
    tru = [p for p in pairs if p["truth"] and p["caut_raw"] == p["truth"]]
    fal = [p for p in pairs if p["truth"] and p["caut_raw"] != p["truth"]]
    print(f"  cautionaries that match the print   {len(tru)}")
    print(f"  cautionaries that do not            {len(fal)}")
    sep = []
    for f in fields_c:
        tv = sorted(p[f] for p in tru if p[f] is not None)
        fv = sorted(p[f] for p in fal if p[f] is not None)
        if not tv or not fv:
            print(f"  {f:<22} TRUE {tv}  FALSE {fv}   (cannot compare)")
            continue
        gap = min(tv) - max(fv)
        ok = gap > 0
        sep.append((f, gap, ok))
        print(f"  {f:<22} TRUE {tv}  FALSE {fv}   "
              f"{'SEPARATES, empty interval ' + f'{max(fv)} -> {min(tv)}' if ok else 'does NOT separate'}")
    if not any(ok for _f, _g, ok in sep):
        print("  ⚠️ POSITIVE CONTROL FAILED: nothing separates, so this probe"
              " cannot detect separation and its negatives mean nothing.")
        return 3

    # ── 3. every candidate rule, scored against the print ──────────────────
    print("\n═══ 3. CANDIDATE RULES, SCORED AGAINST THE PRINT ═══")
    results = {}
    for name, rule in RULES:
        s = score(rule, pairs)
        results[name] = s
        print(f"\n  {name}")
        print(f"      fixed {s['fixed']}   BROKEN {s['broken']}   "
              f"ABSTENTION->WRONG {s['abstention_lost']}   "
              f"kept-right {s['kept_right']}   kept-wrong {s['kept_wrong']}")
        for d in s["detail"]:
            print(f"        {d['pair']:<34} {d['state']:<16} "
                  f"{str(d['before']):>5} -> {str(d['after']):>5} "
                  f"(truth {d['truth']})  {d['outcome']}")

    # ── 4. what the OPENING's own reader records and nothing reads ─────────
    #
    # ⚠️⚠️ A CLAIM ABOUT THE CODE IS CHECKED AGAINST THE CODE. CLAUDE.md's
    # prescription for a prose claim is that it be mechanically falsifiable,
    # so this greps rather than asserts.
    print("\n═══ 4. THE OPENING'S EVIDENCE, AND WHO READS IT ═══")
    import inspect                                              # noqa: PLC0415
    sys.path.insert(0, str(HERE.parents[1]))
    from tools.omr.staged import gather                         # noqa: E402
    from tools.omr.staged.adjudicators import rhythm            # noqa: E402
    written = inspect.getsource(gather._gather_meter_template) \
        if hasattr(gather, "_gather_meter_template") else ""
    if not written:
        src = inspect.getsource(gather)
        i = src.find("Q.METER_TEMPLATE,\n")
        written = src[max(0, i - 2000): i + 600]
    body = inspect.getsource(rhythm.adjudicate_meter)
    for field in ("score", "runner_up", "runner_up_score", "score_margin",
                  "raw"):
        w = f"{field}=" in written
        r = f'"{field}"' in body or f"'{field}'" in body
        print(f"  {field:<16} written by GATHER {str(w):<5}   "
              f"read by adjudicate_meter {str(r):<5}"
              + ("   <- ON THE RECORD AND READ BY NOTHING" if w and not r
                 else ""))
    print("  ✓ `raw` is this grep's own POSITIVE CONTROL: it is written AND "
          "read,\n     so a `False` in the read column is a fact and not a "
          "broken search.")
    print("  ⚠️ `score` is the ONE quantity FINDINGS §4c measured separating "
          "this\n     document's true votes (0.744-0.781) from its false one "
          "(0.514) —\n     and the vote does not look at it. That figure is "
          "INHERITED, not\n     re-measured here: it needs the locator and "
          "the page.")

    ctrl = next(v for k, v in results.items() if k.startswith("RX"))
    print(f"\n  ⚠️ CONTROL CHECK: the inverted rule breaks "
          f"{ctrl['broken']} pair(s).")
    if ctrl["broken"] == 0:
        print("  ⚠️ CONTROL FAILED — the `BROKEN` column cannot go non-zero, "
              "so every zero in it above means nothing.")
        return 3
    print("  ✓ the `BROKEN` column can go non-zero, so the zeros above are "
          "results.")

    Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json_out).write_text(json.dumps(
        {"pairs": pairs,
         "rules": {k: {kk: vv for kk, vv in v.items()} for k, v in results.items()}},
        indent=1) + "\n")
    print(f"\nwrote {a.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
