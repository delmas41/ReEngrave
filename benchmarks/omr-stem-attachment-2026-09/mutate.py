"""THE MUTATION BATTERY -- over the INSTRUMENTS, because nothing ships here.

This directory's product is a measurement and a refusal, so the thing that has
to be shown trustworthy is the measurement. Each arm breaks one instrument in
a way a reader could plausibly write by accident, and requires the CONTROL that
instrument carries to go RED. An arm that stays green is a control that cannot
fail.

⚠️ ONE RED ARM IS NOT A BATTERY, and a battery of failure tests can pass by
failing at everything -- so arm 0 is a POSITIVE CONTROL in the same class: the
unmutated tree must pass every control. It runs FIRST.

⚠️⚠️ IT MUST LEAVE THE TREE AS IT FOUND IT -- WHICH IS NOT THE SAME AS LEAVING
IT AS GIT HAS IT. This repo has twice had a battery destroy the change it had
just certified by restoring from HEAD, and once had an INTERRUPTED battery
leave a mutation on disk indistinguishable from a legitimate edit. So: a BYTE
snapshot is taken before the first arm and the restore is VERIFIED by hash; an
in-flight SENTINEL is written before the first arm and deleted only on a clean
exit, and a run that finds one refuses to start and names every file at risk
with the hash it should have; and a dirty tree is refused without `--force`.

    python3 mutate.py            # the battery
    python3 mutate.py --force    # ... on a deliberately dirty tree
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SENTINEL = HERE / ".mutation-in-flight.json"
SNAP = HERE / ".mutation-snapshot"

REC = ("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/"
       "beethoven5-p1-p4-ink-identity.record.json")
PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
       "symphony-5-op67/beethoven--symphony-5-op67--"
       "henry-litolff-s-verlag-1870--imslp984073.pdf")
EXPECT = HERE.parents[0] / "omr-stem-ink-2026-09/out/litolff-convention.json"

CONV, BEAM, MARG = (HERE / "convention_rows.py", HERE / "beam_mate_set.py",
                    HERE / "marginal_reach.py")

#: (name, file, find, replace, which control must go red)
#:
#: ⚠️ EVERY ANCHOR IS CHECKED FOR UNIQUENESS BEFORE THE ARM RUNS. A battery
#: that silently mutates the SECOND occurrence of a line measures its own
#: aim -- which has happened here twice, once mutating a different function
#: entirely.
ARMS = [
    ("convention: swap the two legal cells", CONV,
     'r_up = round(best[("R", "up")], 2)\n        l_dn = round(best[("L", "down")], 2)',
     'r_up = round(best[("L", "up")], 2)\n        l_dn = round(best[("R", "down")], 2)',
     "conv"),
    # ⚠️ RETARGETED AFTER THE FIRST RUN REPORTED `BAD ANCHOR (0 matches)`.
    # The intended hazard was `Q.GLYPH_BOX` read as `[x,y,w,h]` when the NAME
    # comes first -- but `convention_rows.py` never calls `_xywh_head`; it
    # reads `detail["bbox_page_px"]`, which is a CORNER box. So the analogous
    # real hazard for THIS file is the other recorded box confusion: *a
    # measure bbox is CORNERS and a detection bbox is WIDTH*. Reading the
    # corner box as a width box puts the head's right edge at x0+x1.
    ("convention: the corner box read as a width box", CONV,
     '        x0, y0, x1, y1 = pbox[s]',
     '        x0, y0, w_, h_ = pbox[s]\n        x1, y1 = x0 + w_, y0 + h_',
     "conv"),
    ("convention: the staff key built with the KIND first", CONV,
     'L = lines_of.get(f"staff/{p[1]}/{p[2]}/{p[3]}")',
     'L = lines_of.get(f"staff/{p[0]}/{p[1]}/{p[2]}")',
     "conv"),
    # ⚠️⚠️ ONE ARM WAS REMOVED AFTER THE FIRST RUN AND IS NAMED RATHER THAN
    # DELETED SILENTLY: *heads selected by NAME instead of
    # `detail["category"]`* came back GREEN, and
    # `head_filter_equivalence.py` shows why -- on this record the two
    # selectors pick the IDENTICAL 2,347 rows (0 only-category, 0 only-name).
    # It is an EQUIVALENT MUTANT, not a hole, and an arm that can never go red
    # trains the next reader to ignore the list. ⚠️ It is equivalent on THIS
    # record; a record whose detector emitted a notehead category under some
    # other name would separate them.
    ("beam-mate: a MAJORITY of mates, not unanimity", BEAM,
     'if mates == 0 or len(votes) != 1:',
     'if mates == 0 or not votes:',
     "beam"),
    ("beam-mate: the cell key by rsplit, losing the KIND", BEAM,
     'return "cell/" + "/".join(p[1:5]) if len(p) >= 5 else subject',
     'return subject.rsplit("/", 1)[0]',
     "beam"),
    ("beam-mate: a head's x-centre test replaced by a box overlap", BEAM,
     '    hx = head_box[0] + head_box[2] / 2.0\n    return beam[0] <= hx <= beam[0] + beam[2]',
     '    return (head_box[0] <= beam[0] + beam[2]\n            and head_box[0] + head_box[2] >= beam[0])',
     "beam"),
    ("marginal: the overlap counted as marginal too", MARG,
     'marginal = tab[("stays no_stem", "speaks")]',
     'marginal = gross',
     "marg"),
]

#: `_on_beam` lives in the SHIPPED module, which is out of this lane, so that
#: arm cannot mutate it in place. It is imported by name, so the honest
#: mutation site is the local rebind -- drop it from the import and define a
#: box-overlap version beside it.
#:
#: ⚠️ ADDRESSED BY NAME, NOT BY INDEX. The first version wrote `ARMS[6]`, and
#: when one arm was removed as an equivalent mutant every index below it
#: shifted, so the rebind silently retargeted a different arm. That is the
#: BAD-ANCHOR lesson one level up: *a battery that addresses an arm by its
#: position measures its own bookkeeping.*
_XC = "beam-mate: a head's x-centre test replaced by a box overlap"
_i = [n for n, arm in enumerate(ARMS) if arm[0] == _XC]
if len(_i) != 1:
    raise SystemExit(f"mutate.py: expected exactly one arm named {_XC!r}, "
                     f"found {len(_i)}")
ARMS[_i[0]] = (
    _XC, BEAM,
    'from tools.omr.staged.adjudicators.rhythm import (               # noqa: E402\n    _on_beam, _project, _stems_on, _xywh, _xywh_head)',
    'from tools.omr.staged.adjudicators.rhythm import (               # noqa: E402\n    _project, _stems_on, _xywh, _xywh_head)\n\n\ndef _on_beam(head_box, beam):\n    return (head_box[0] <= beam[0] + beam[2]\n            and head_box[0] + head_box[2] >= beam[0])',
    "beam")


def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def run_conv():
    return sh([sys.executable, str(CONV), "--record", REC, "--pdf", PDF,
               "--label", "arm", "--out", str(HERE / "out/_arm-rows.json"),
               "--expect", str(EXPECT)])


def run_beam():
    return sh([sys.executable, str(BEAM), "--record", REC, "--label", "arm",
               "--out", str(HERE / "out/_arm-beammate.json"), "--expect", "152"])


def run_marg():
    r = sh([sys.executable, str(MARG), "--rows", str(HERE / "out/litolff-rows.json"),
            "--beammate", str(HERE / "out/litolff-beammate.json"),
            "--label", "arm", "--out", str(HERE / "out/_arm-marginal.json")])
    # `marginal_reach.py` carries no --expect, so the battery asserts on its
    # OUTPUT: the marginal must not equal the gross.
    if r.returncode == 0:
        d = json.loads((HERE / "out/_arm-marginal.json").read_text())
        if d["marginal"] == d["gross"]:
            r.returncode = 1
    return r


RUN = {"conv": run_conv, "beam": run_beam, "marg": run_marg}


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    files = sorted({arm[1] for arm in ARMS})

    if SENTINEL.is_file():
        print("REFUSING: a previous battery was interrupted and its "
              "mutations may still be on disk.\n", file=sys.stderr)
        for k, v in json.loads(SENTINEL.read_text())["hashes"].items():
            now = digest(Path(k)) if Path(k).is_file() else "MISSING"
            flag = "" if now == v else "   <- DIFFERS"
            print(f"   {k}\n      should be {v[:16]}  is {now[:16]}{flag}",
                  file=sys.stderr)
        print(f"\nRestore from {SNAP}, then delete {SENTINEL}.",
              file=sys.stderr)
        return 2

    dirty = sh(["git", "status", "--porcelain"]).stdout.strip()
    if dirty and not a.force:
        print("REFUSING: the tree is dirty. A battery restores from its own "
              "snapshot, but an interrupted one leaves a mutation that looks "
              "exactly like your edit. Commit first, or pass --force.",
              file=sys.stderr)
        return 2

    SNAP.mkdir(exist_ok=True)
    hashes = {}
    for f in files:
        shutil.copy2(f, SNAP / f.name)
        hashes[str(f)] = digest(f)
    SENTINEL.write_text(json.dumps({"hashes": hashes}, indent=1))

    results = []
    try:
        print("== ARM 0: POSITIVE CONTROL -- the clean tree must PASS ==")
        ok = True
        for k in ("conv", "beam", "marg"):
            r = RUN[k]()
            good = r.returncode == 0
            ok &= good
            print(f"   {k:<6} exit {r.returncode}  "
                  f"{'PASS' if good else 'FAIL <- the battery cannot trust itself'}")
            if not good:
                sys.stderr.write(r.stdout[-1500:] + r.stderr[-1500:])
        results.append(("POSITIVE CONTROL (clean tree passes)", ok))

        for name, f, find, repl, which in ARMS:
            src = f.read_text()
            n = src.count(find)
            if n != 1:
                print(f"   BAD ANCHOR ({n} matches): {name}")
                results.append((name, False))
                continue
            f.write_text(src.replace(find, repl))
            try:
                r = RUN[which]()
            finally:
                shutil.copy2(SNAP / f.name, f)
            red = r.returncode != 0
            print(f"   {'RED ' if red else 'GREEN'} exit {r.returncode:>2}  {name}")
            results.append((name, red))
    finally:
        bad = []
        for f in files:
            shutil.copy2(SNAP / f.name, f)
            if digest(f) != hashes[str(f)]:
                bad.append(f)
        if bad:
            print(f"\nRESTORE FAILED for {bad} -- snapshot kept at {SNAP}",
                  file=sys.stderr)
            return 2
        SENTINEL.unlink(missing_ok=True)
        shutil.rmtree(SNAP, ignore_errors=True)
        for tmp in HERE.glob("out/_arm-*.json"):
            tmp.unlink(missing_ok=True)

    print(f"\n== RESTORE VERIFIED: all {len(files)} files byte-identical to "
          f"the pre-battery snapshot ==")
    n_ok = sum(1 for _, v in results if v)
    print(f"== {n_ok} of {len(results)} arms behaved as required ==")
    for name, v in results:
        if not v:
            print(f"   SURVIVED / FAILED: {name}")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
