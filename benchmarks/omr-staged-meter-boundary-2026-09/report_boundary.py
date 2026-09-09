"""What each arm DECIDED about the meter, and whether the bars discriminated.

⚠️ THE DECIDING NUMBERS COME OUT OF THE RECORD'S OWN `detail`, NOT OUT OF THIS
FILE. `support`, `bars_agree`, `bars_disagree` and `bar_lengths_seen` are
written by `adjudicate_meter` itself; this only lays them side by side and
labels each row against a hand-entered truth. Recomputing them here would
measure this script.

⚠️⚠️ THE CONTROL A CROSS-WINDOW COMPARISON NEEDS IS `bar_lengths_seen`, NOT
THE DURATIONS -- and reaching for the durations first is a trap this file
exists partly to mark. Two arms that differ only in WHICH EARLIER PAGE was in
the window must read the shared page identically, because the gather is per
page. But a DECIDED meter is CONSUMED: `size_measure_rest` and
`reconcile_duration` rewrite durations from it, so the durations are
downstream of the very thing under test. Measured on this fixture, page 3:
**159 of 314 duration verdicts differ between the carry-off and carry-on arms**
-- 157 whole rests re-sized 4.0 -> 3.0 as `whole_rest_means_the_bar`, plus 2
notes re-read by `meter_reconciliation`. That is the FIX working, not jitter.

So `--control durations` is valid only between arms whose meter outcome for
that page is the SAME (two abstentions, or two identical decisions), and
`--control bars` is the one that always applies: `bar_lengths_seen` is written
by `adjudicate_meter` out of the durations as they stood BEFORE any
consequence ran, so equal bar readings under two different candidates make the
difference attributable to the candidate.

    python3 report_boundary.py out/full-CARRY.json out/p0p3-CARRY.json
    python3 report_boundary.py --control bars out/full-CARRY.json out/p0p3-CARRY.json
    python3 report_boundary.py --control durations --page 3 A.json B.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

#: Hand-entered from the reference encoding and confirmed against the rendered
#: page images: `beethoven-sym5-mvt4` is 4/4 to bar 154, 3/4 from 155 to 208,
#: 4/4 from 209. Keyed by (fixture tag, page index) -> the truth for the
#: system on that page.
TRUTH = {
    ("boundary-m150-180", 0): "4/4",   # m150-154, printed as a common-time C
    ("boundary-m150-180", 1): "4/4",   # m154 alone, the fermata bar
    ("boundary-m150-180", 2): "3/4",   # m155+, the change, printed at the head
    ("boundary-m150-180", 3): "3/4",   # m172+, NO meter printed
    ("boundary-m204-232", 0): "3/4",   # m204+, printed at the head
    ("boundary-m204-232", 1): "3/4",   # m206+, the change to 4/4 mid-system
    ("boundary-m204-232", 2): "4/4",   # m215+, NO meter printed
    ("boundary-m204-232", 3): "4/4",
    ("boundary-m204-232", 4): "4/4",
    ("boundary-m204-232", 5): "4/4",
    # The regression control: the SCAN the whole meter thread was built on.
    # Movement 1 is 2/4; the finale is 4/4 to bar 154 and 3/4 from 155, and the
    # Litolff print reaches bar 147 on page 62.
    ("litolff-984073", 1): "2/4",
    ("litolff-984073", 2): "2/4",
    ("litolff-984073", 61): "4/4",
    ("litolff-984073", 62): "4/4",
}

#: Where a page prints a meter CHANGE mid-system: page -> (cell it stands at,
#: the meter it names). Hand-read off the rendered page against the reference:
#: `boundary-m204-232` page 1 opens at m206 and the reference changes at m209,
#: so the change is that system's cell 3.
#:
#: ⚠️ A `change_only` VERDICT'S TOP-LEVEL `raw` IS THE CHANGE, NOT THE OPENING
#: -- the opening is what that reason says is unknown. Scoring it against the
#: page's opening meter marks a correct reading WRONG, which is what the first
#: run of this script did.
#: An explicit `None` means *this page prints NO change* — so a `change_only`
#: verdict on it is WRONG, not unscored. Without the sentinel a page with no
#: entry is merely unknown, and a false change reads as "?" instead of as a
#: false positive.
TRUTH_CHANGES = {
    ("boundary-m204-232", 1): (3, "C"),
    ("litolff-984073", 62): (8, "3/4"),
    ("litolff-984073", 61): None,      # bar 140; the page prints no meter
    ("litolff-984073", 1): None,
    ("litolff-984073", 2): None,
}


#: A meter's LENGTH in quarter notes, so a `C` and a `4/4` are one row.
def length_of(raw):
    if not raw:
        return None
    if raw in ("C", "common"):
        return 4.0
    if raw in ("C|", "cut"):
        return 2.0
    try:
        n, d = raw.split("/")
        return float(n) * 4.0 / float(d)
    except Exception:
        return None


def meters(path):
    rec = json.loads(Path(path).read_text())["record"]
    return [v for v in rec["verdicts"] if v["quantity"] == "meter"]


def durations(path, page):
    rec = json.loads(Path(path).read_text())["record"]
    out = {}
    for v in rec["verdicts"]:
        if v["quantity"] != "duration":
            continue
        if not str(v["subject"]).startswith(f"glyph/{page}/"):
            continue
        out[v["subject"]] = (v["outcome"], json.dumps(v.get("value"), sort_keys=True))
    return out


def bars_seen(path):
    """Each system's `bar_lengths_seen`, as the METER DECISION recorded it.

    ⚠️ Written by `adjudicate_meter` from the durations as they stood before
    any consequence ran, which is what makes it a valid cross-arm control.
    """
    out = {}
    for v in meters(path):
        d = v.get("detail") or {}
        if "bar_lengths_seen" in d:
            out[v["subject"]] = d["bar_lengths_seen"]
    return out


def show(path, tag):
    print(f"\n── {Path(path).name} ─────────────────────────────")
    for v in meters(path):
        sub = v["subject"]
        page = int(str(sub).split("/")[1])
        truth = TRUTH.get((tag, page), "?")
        val = v.get("value") or {}
        raw = val.get("raw")
        d = v.get("detail") or {}
        got_len = length_of(raw)
        want_len = length_of(truth)
        mark = "·"
        if v["outcome"] == "decided":
            if v.get("reason") == "change_only":
                known = (tag, page) in TRUTH_CHANGES
                want = TRUTH_CHANGES.get((tag, page))
                segs = (val.get("segments") or [])
                got = ((segs[0].get("from_cell"), segs[0].get("raw"))
                       if segs else None)
                mark = ("?(no change truth)" if not known
                        else ("OK " if got == want else "WRONG"))
                truth = (f"chg@{want[0]}={want[1]}" if want
                         else ("prints no change" if known else "?"))
            else:
                mark = "OK " if got_len == want_len else "WRONG"
        bits: list = []
        for seg in (val.get("segments") or [])[1:] if v.get("reason") != "change_only" else []:
            bits.append(f"segment@{seg.get('from_cell')}={seg.get('raw')}"
                        f"(support={seg.get('support')},"
                        f"{seg.get('bars_fit')}+/{seg.get('bars_contradict')}-)")
        if v.get("reason") == "change_only":
            for seg in (val.get("segments") or []):
                bits.append(f"change@{seg.get('from_cell')}={seg.get('raw')}"
                            f"(support={seg.get('support')},"
                            f"staves={len(seg.get('staves_reading_it') or [])},"
                            f"{seg.get('bars_fit')}+/{seg.get('bars_contradict')}-)")
        for k in ("support", "bars_agree", "bars_disagree", "length",
                  "carried_from", "form_borrowed_from", "candidate_forms",
                  "bar_lengths_seen", "instead_of"):
            if k in d:
                bits.append(f"{k}={d[k]}")
        print(f"  {sub:14s} truth={truth:4s} {v['outcome']:9s} "
              f"{str(v.get('reason')):36s} {str(raw):6s} {mark}")
        if bits:
            print(f"       {'  '.join(bits)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--tag", default="boundary-m150-180")
    ap.add_argument("--control", choices=("bars", "durations"), default=None,
                    help="bars: the meter decisions' own `bar_lengths_seen` "
                         "must agree (always valid). durations: the raw "
                         "duration verdicts must agree -- valid ONLY where the "
                         "meter outcome is the same in both arms, because a "
                         "decided meter rewrites them.")
    ap.add_argument("--page", type=int, default=3)
    a = ap.parse_args()
    if a.control:
        assert len(a.files) == 2, "--control takes exactly two runs"
        if a.control == "bars":
            x, y = (bars_seen(f) for f in a.files)
            shared = sorted(set(x) & set(y))
            bad = [s for s in shared if x[s] != y[s]]
            for s in shared:
                print(f"CONTROL bars {s}: {x[s]} vs {y[s]} "
                      f"{'OK' if x[s] == y[s] else '*** DIFFER ***'}")
            if not shared:
                print("CONTROL bars: no system carries `bar_lengths_seen` in "
                      "BOTH runs -- nothing is controlled. Run an arm that "
                      "reaches the bars in each.")
                raise SystemExit(1)
            raise SystemExit(1 if bad else 0)
        x, y = (durations(f, a.page) for f in a.files)
        same = x == y
        print(f"CONTROL durations page {a.page}: {len(x)} vs {len(y)} verdicts, "
              f"{'IDENTICAL' if same else '*** DIFFER ***'}")
        if not same:
            diff = [k for k in set(x) | set(y) if x.get(k) != y.get(k)]
            print(f"  {len(diff)} differing subjects, first 5: {diff[:5]}")
            print("  ⚠️ if the two arms decided the meter DIFFERENTLY for this "
                  "page this is expected -- see the module docstring.")
        raise SystemExit(0 if same else 1)
    for f in a.files:
        show(f, a.tag)
