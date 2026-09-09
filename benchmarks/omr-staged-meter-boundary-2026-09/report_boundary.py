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
    # ⚠️ THE TRUTH STRING IS THE ENGRAVING, NOT THE FRACTION. LilyPond sets
    # 4/4 as a common-time `C` and this page prints one, so the truth is `C`;
    # writing "4/4" here scored a CORRECT reading as FORM-WRONG once the
    # length/form split arrived.
    ("boundary-m150-180", 0): "C",     # m150-154, printed as a common-time C
    ("boundary-m150-180", 1): "C",     # m154 alone, the fermata bar
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
    # Brahms 1 mvt 1 — 6/8, with ONE bar of 9/8 at m8 and 6/8 again from m9.
    # The engraved render and the Breitkopf scan print the SAME structure,
    # including the cautionary 9/8 after page 0's final barline.
    ("brahms1-m1-22", 0): "6/8",     # mm 1-7
    ("brahms1-m1-22", 1): "9/8",     # opens ON the 9/8 bar, m8
    ("brahms1-m1-22", 2): "6/8",
    # ⚠️ THE SCAN'S PAGE 1 HOLDS TWO SYSTEMS WITH DIFFERENT TRUTHS, so these
    # keys carry the SYSTEM as well. `works.json` (hand-verified by Sean
    # against the print) has system 1 = mm 8-14 and system 2 = mm 15-22.
    ("brahms1-317803", 0): "6/8",    # the SAME music, scanned
    ("brahms1-317803", 1, 0): "9/8",   # opens on m8, the 9/8 bar
    ("brahms1-317803", 1, 1): "6/8",   # mm 15-22, no meter printed
    # Brahms 1 mvt 4 — 4/4 printed `C` to m391, 2/2 printed `¢` from m392.
    # ⚠️ BOTH ARE 4.0 QUARTER NOTES. The bars are blind here by construction.
    ("brahms4-m386-412", 0): "C",
    ("brahms4-m386-412", 1): "C|",
    ("brahms4-m386-412", 2): "C|",
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
    # ⚠️ p0's 9/8 is a CAUTIONARY printed AFTER the final barline; it announces
    # the NEXT system's meter and governs no bar on this page. A change
    # proposed at that page's last cell is WRONG — it would re-size m7.
    ("brahms1-m1-22", 0): None,
    ("brahms1-m1-22", 1): (1, "6/8"),
    ("brahms1-m1-22", 2): None,
    ("brahms1-317803", 0): None,
    ("brahms1-317803", 1, 0): (1, "6/8"),
    ("brahms1-317803", 1, 1): None,
    # m392 is the 7th bar of an excerpt opening at 386, so cell 6.
    ("brahms4-m386-412", 0): (6, "C|"),
    ("brahms4-m386-412", 1): None,
    ("brahms4-m386-412", 2): None,
}


#: A meter's LENGTH in quarter notes, so a `C` and a `4/4` are one row.
def length_of(raw):
    if not raw:
        return None
    if raw in ("C", "common"):
        return 4.0
    if raw in ("C|", "cut"):
        # ⚠️ 4.0, NOT 2.0 — and this line was WRONG until the Brahms 4 fixture
        # made it matter. Cut common is 2/2: two HALF notes, which is four
        # quarter notes, exactly as many as `C`. That identity is the whole
        # point of the length-blind fixture — the bars cannot tell `C` from
        # `¢`, so only ink can.
        return 4.0
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


def _same_form(got, want):
    """Is the ENGRAVING the same, not merely the bar length?

    ⚠️ `4/4` and `C` are one length and two printings and this repository
    already pays for the difference — `export._mxl_attributes_block` emits
    `symbol="common"` / `"cut"` from `raw`, and musicdiff charges a wrong
    `symbol=` at THREE EDITS PER STAFF.
    """
    if got is None or want is None:
        return False
    norm = {"common": "C", "cut": "C|"}
    return norm.get(str(got), str(got)) == norm.get(str(want), str(want))


def partitions(path):
    """Each system's bar COUNT, as `measure_partition` decided it.

    ⚠️ THIS IS WHAT MAKES A CROSS-ARM CONTROL A CONTROL. `--control bars`
    compares runs by SUBJECT KEY, and subject keys are positional
    (`system/2/0`) — so two runs of entirely different music happily "match"
    and the tool reports a difference as if it meant something. It did exactly
    that once here, comparing a Brahms first movement against a Brahms finale.
    Two runs of the same pages agree on every shared system's bar count; two
    runs of different music essentially never do.
    """
    out = {}
    rec = json.loads(Path(path).read_text())["record"]
    for v in rec["verdicts"]:
        if v["quantity"] != "measure_partition":
            continue
        sub = str(v["subject"]).split("/")
        val = v.get("value")
        n = val if isinstance(val, int) else (val or {}).get("n_cells")
        out.setdefault(f"system/{sub[1]}/{sub[2]}", set()).add(n)
    return {k: sorted(x for x in v if x is not None) for k, v in out.items()}


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
        system = int(str(sub).split("/")[2])
        # ⚠️ A PAGE CAN HOLD TWO SYSTEMS WITH DIFFERENT METERS, so a
        # (tag, page, system) key wins over a (tag, page) one. Keying only on
        # the page marked the scan's second system against the first's truth.
        def _truth(table, default=None):
            if (tag, page, system) in table:
                return table[(tag, page, system)]
            return table.get((tag, page), default)
        truth = _truth(TRUTH, "?")
        val = v.get("value") or {}
        raw = val.get("raw")
        d = v.get("detail") or {}
        got_len = length_of(raw)
        want_len = length_of(truth)
        mark = "·"
        if v["outcome"] == "decided":
            if v.get("reason") == "change_only":
                known = (tag, page) in TRUTH_CHANGES
                known = ((tag, page, system) in TRUTH_CHANGES
                         or (tag, page) in TRUTH_CHANGES)
                want = _truth(TRUTH_CHANGES)
                segs = (val.get("segments") or [])
                got = ((segs[0].get("from_cell"), segs[0].get("raw"))
                       if segs else None)
                mark = ("?(no change truth)" if not known
                        else ("OK " if got == want else "WRONG"))
                truth = (f"chg@{want[0]}={want[1]}" if want
                         else ("prints no change" if known else "?"))
            else:
                # ⚠️⚠️ LENGTH AND FORM ARE SCORED APART, and reporting only the
                # length would call a KNOWN-WRONG answer "OK". `C` and `¢` are
                # both 4.0 quarter notes, so a mechanism that reasons from bar
                # sums gets the length right and the engraving wrong — and
                # musicdiff charges `symbol=` at 3 edits per staff. A row that
                # is LENGTH-OK and FORM-WRONG is the designed limit of the bar
                # mechanisms observed, not a pass.
                same_form = _same_form(raw, truth)
                mark = ("OK " if got_len == want_len and same_form
                        else ("LEN-OK/FORM-WRONG" if got_len == want_len
                              else "WRONG"))
                # ⚠️ A `voted` VERDICT CAN STILL CARRY A WRONG SEGMENT, and
                # scoring only the opening hides it. Brahms 1 page 0 votes the
                # right 6/8 and then proposes a change at its LAST cell out of
                # the CAUTIONARY 9/8 printed after the final barline — a
                # standard engraving convention, and the segment would re-size
                # a bar the cautionary does not govern.
                known = ((tag, page, system) in TRUTH_CHANGES
                         or (tag, page) in TRUTH_CHANGES)
                want_c = _truth(TRUTH_CHANGES)
                segs = (val.get("segments") or [])[1:]
                got_c = ((segs[0].get("from_cell"), segs[0].get("raw"))
                         if segs else None)
                if known and got_c != want_c:
                    mark = "WRONG(segment)" if mark == "OK " else mark
                    truth = (truth + " " + (f"chg@{want_c[0]}={want_c[1]}"
                                            if want_c else "no change"))
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


#: Which fixture each run tag belongs to, so `--tally` can score a whole set.
#: ⚠️ The ENGRAVED and SCANNED rows of the same music are the isolating pair —
#: same work, same measures, same code, one difference.
TALLY_SET = (
    ("m5brahms1eng-OFF", "brahms1-m1-22", "Brahms 1 i   ENGRAVED"),
    ("m5brahms1scan-OFF", "brahms1-317803", "Brahms 1 i   BREITKOPF SCAN"),
    ("m5brahms4eng-OFF", "brahms4-m386-412", "Brahms 1 iv  ENGRAVED (C -> cut)"),
    ("m5full-CARRY", "boundary-m150-180", "Beethoven 5 iv ENGRAVED (fwd)"),
    ("m5rev-OFF", "boundary-m204-232", "Beethoven 5 iv ENGRAVED (rev)"),
    ("m5lit6162-OFF", "litolff-984073", "Beethoven 5  LITOLFF SCAN"),
)


def tally(out_dir):
    """Printed meter changes against proposed ones, per fixture.

    ⚠️ COUNTS SEGMENTS, NOT VERDICTS. A `voted` system can carry a wrong
    segment while its opening is right, and a system-level pass/fail hides
    exactly that — which is what page 0 of both Brahms printings does with the
    CAUTIONARY signature after its final barline.
    """
    print(f"{'':34s} {'printed':>8} {'proposed':>9} {'found':>6} {'FALSE':>6}")
    for name, tag, label in TALLY_SET:
        f = Path(out_dir) / f"{name}.json"
        if not f.is_file():
            print(f"{label:34s} {'(not run)':>31}")
            continue
        proposed = correct = 0
        for v in meters(f):
            sub = str(v["subject"])
            page, system = int(sub.split("/")[1]), int(sub.split("/")[2])
            want = TRUTH_CHANGES.get((tag, page, system),
                                     TRUTH_CHANGES.get((tag, page), "?"))
            val = v.get("value") or {}
            segs = val.get("segments") or []
            segs = segs if v.get("reason") == "change_only" else segs[1:]
            proposed += len(segs)
            if want not in (None, "?") and segs and \
                    (segs[0].get("from_cell"), segs[0].get("raw")) == want:
                correct += 1
        truths = sum(1 for k, x in TRUTH_CHANGES.items()
                     if k[0] == tag and x is not None)
        print(f"{label:34s} {truths:>8} {proposed:>9} {correct:>6} "
              f"{proposed - correct:>6}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--tag", default="boundary-m150-180")
    ap.add_argument("--control", choices=("bars", "durations"), default=None,
                    help="bars: the meter decisions' own `bar_lengths_seen` "
                         "must agree (always valid). durations: the raw "
                         "duration verdicts must agree -- valid ONLY where the "
                         "meter outcome is the same in both arms, because a "
                         "decided meter rewrites them.")
    ap.add_argument("--page", type=int, default=3)
    ap.add_argument("--tally", default=None, metavar="OUT_DIR",
                    help="printed vs proposed meter changes across the "
                         "fixture set, engraved rows against scanned ones")
    a = ap.parse_args()
    if a.tally:
        tally(a.tally)
        raise SystemExit(0)
    if a.control:
        assert len(a.files) == 2, "--control takes exactly two runs"
        if a.control == "bars":
            px, py = (partitions(f) for f in a.files)
            shared_sys = sorted(set(px) & set(py))
            mismatch = [k for k in shared_sys if px[k] != py[k]]
            if not shared_sys or mismatch:
                print("CONTROL bars REFUSED: these runs are not of the same "
                      "pages.")
                for k in (mismatch or shared_sys):
                    print(f"  {k}: bar counts {px.get(k)} vs {py.get(k)}")
                if not shared_sys:
                    print("  (no system subject appears in both runs)")
                raise SystemExit(2)
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
