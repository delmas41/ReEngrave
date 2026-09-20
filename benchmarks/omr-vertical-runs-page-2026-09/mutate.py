"""Mutation battery for the page-frame reader and its arm.

⚠️⚠️ TWO SUBJECTS, TWO JUDGES — the predecessor lane's split, inherited:
arms under `tools/` are judged by the UNIT SUITE, which must go RED; arms
under this directory are judged by the ARM's own headline, which must MOVE. An
arm that leaves its judge unchanged is a SURVIVOR and a real test gap.

⚠️ ONE RED ARM IS NOT A BATTERY, and it needs a POSITIVE CONTROL IN THE SAME
CLASS: the baseline must be GREEN before any arm is read.

⚠️ A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT — WHICH IS NOT THE
SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS NEITHER. A
BYTE snapshot on disk, an in-flight SENTINEL, a VERIFIED restore by md5, and a
refusal to start on a dirty tree without `--force`.

⚠️ `PYTHONDONTWRITEBYTECODE=1` IN EVERY ARM — a stale `.pyc` made two arms in a
sibling lane import UNMUTATED code and report NOT RED.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
SENTINEL = OUT / ".mutate-in-flight"

READER = ROOT / "tools" / "omr" / "vertical_runs_page.py"
ARM = HERE / "page_run_arm.py"
TARGETS = {"reader": READER, "arm": ARM}

SUITE = ["tools/omr/tests/test_vertical_runs_page.py"]

#: ⚠️ ONE PAGE AND THE PRINT JOIN, so the arm's headline includes the tables
#: the finding rests on. Litolff p1 carries 41 crop rows, enough for the join
#: to be live rather than empty.
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library"
ARM_ARGS = [
    "--pdf", f"{LIB}/editions/beethoven/symphony-5-op67/"
             "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
             "imslp984073.pdf",
    "--pages", "1",
    "--crop-rows", "benchmarks/omr-stem-crop-pass-2026-09/out/litolff-rows.json",
    "--crop-manifest",
    "benchmarks/omr-stem-crop-pass-2026-09/out/crop-manifest-litolff.json",
    "--crop-adjudication",
    "benchmarks/omr-stem-crop-pass-2026-09/ADJUDICATION-litolff.json",
    "--label", "MUTATE", "--json", str(OUT / ".mutate-arm.json"),
]

#: (target, name, find, replace, what it must break)
ARMS = [
    # ── THE READER: the window, which is the whole claim ────────────────────
    ("reader", "the page is windowed to one staff's band (the fault, restored)",
     "    ink = _binary_ink(img)",
     "    ink = _binary_ink(img)\n"
     "    _b = _staff_bounds(staves)\n"
     "    if _b:\n"
     "        _t = int(max(0, _b[0][0] - 4 * sp))\n"
     "        _s = int(_b[0][1] + 4 * sp)\n"
     "        ink[:_t] = 0\n"
     "        ink[_s:] = 0",
     "the no-clip tests must fail -- this IS the predecessor's cell, and if "
     "the suite survives it then nothing here is testing the window"),

    ("reader", "the kernel is one staff space (the pre-2026 stem bug)",
     "    kernel_h = max(3, int(round(sp * KERNEL_REFERENCE_SPACES\n"
     "                                * STEM_KERNEL_MARGIN)))",
     "    kernel_h = max(3, int(round(sp)))",
     "a notehead survives a one-space opening and stays joined to its stem, "
     "so the width and attribution tests must move"),

    ("reader", "the recipe is RESTATED rather than imported",
     "from .line_detection import STEM_KERNEL_MARGIN, _binary_ink",
     "from .line_detection import _binary_ink\nSTEM_KERNEL_MARGIN = 0.8",
     "the anti-drift test must fail -- two copies of a measured constant is "
     "how this repo's numbers drift from the chain that produced them"),

    ("reader", "the staff-space unit is the MEAN, not the median",
     "    return float(np.median(gaps))",
     "    return float(np.mean(gaps))",
     "one odd staff must not move the page's unit -- the median test must "
     "fail, the same statistic and the same reason as system_left_consensus"),

    ("reader", "a page with no staves DEFAULTS its unit instead of raising",
     '''    if sp <= 1.0:
        raise ValueError(''',
     '''    if sp <= 1.0:
        sp = 100.0
    if False:
        raise ValueError(''',
     "a fallback must never convert `cannot tell` into a definite answer, and "
     "reporting page px as staff spaces is this thread's own frame error"),

    ("reader", "an unattributable run is given the NEAREST staff anyway",
     "                if sx1 > sx0 and not (sx0 <= xc <= sx1):\n"
     "                    continue",
     "                pass",
     "`cannot tell` must not be written down as an answer -- the "
     "attributed-to-NONE test must fail"),

    ("reader", "`staves_spanned` counts only the OWNING staff",
     "                spanned += 1",
     "                spanned = 1",
     "a systemic barline crossing twelve staves must not read as one -- the "
     "span assertion must fail"),

    ("reader", "the box is emitted as CORNERS instead of [x, y, w, h]",
     "            x=float(x), y=float(y), w=float(w), h=float(h), area=area,",
     "            x=float(x), y=float(y), w=float(x + w), h=float(y + h), "
     "area=area,",
     "reading one box spelling as another gives a negative width and a clean "
     "believable zero -- the width and no-filter tests must fail"),

    ("reader", "a stem-style HEIGHT cap is reintroduced",
     "        out.append(PageVerticalRun(",
     "        if h > 8.0 * sp:\n            continue\n"
     "        out.append(PageVerticalRun(",
     "THIS IS THE BOUND THAT REFUSES BARLINES. If the suite survives it, the "
     "no-filter tests are decorative"),

    ("reader", "a stem-style WIDTH cap is reintroduced",
     "        out.append(PageVerticalRun(",
     "        if w > 0.6 * sp:\n            continue\n"
     "        out.append(PageVerticalRun(",
     "the width-cap test must fail"),

    ("reader", "runs at the page edge are dropped (the cell-edge filter)",
     "        out.append(PageVerticalRun(",
     "        if x < 3:\n            continue\n"
     "        out.append(PageVerticalRun(",
     "the page-edge test must fail -- the cell-edge filter drops exactly the "
     "population this reader is for"),

    # ── THE INSTRUMENT ──────────────────────────────────────────────────────
    ("arm", "the barline predicate tests only the TOP end",
     """    return (abs(y_top - min(lines)) <= tol
            and abs(y_bot - max(lines)) <= tol)""",
     """    return abs(y_top - min(lines)) <= tol""",
     "the test is about BOTH ends; half of it would fire on every stem whose "
     "head sits near a staff line"),

    ("arm", "the WIDE form collapses into the narrow one",
     """    return (any(abs(y_top - min(v)) <= tol for v in page_lines)
            and any(abs(y_bot - max(v)) <= tol for v in page_lines))""",
     """    return (abs(y_top - min(page_lines[0])) <= tol
            and abs(y_bot - max(page_lines[0])) <= tol)""",
     "*or they extend to other systems* is half of Sean's rule and is the "
     "half that fires here; the two forms must not read alike"),

    ("arm", "the DECISIVE control cannot see the cell signature",
     "                                     if abs(r[\"d_top\"] + 4.0) < 0.05\n"
     "                                     and abs(r[\"d_bot\"] - 4.0) < 0.05)}",
     "                                     if False)}",
     "the control that decides whether the window actually changed must be "
     "able to fire -- otherwise the whole result is unreadable"),

    ("arm", "the cross-reader control passes vacuously",
     "    covered = sum(1 for s in cell_stems\n"
     "                  if any(overlaps(s[\"page_box\"], r[\"page_box\"])\n"
     "                         for r in by_page[s[\"page\"]]))",
     "    covered = len(cell_stems)",
     "a reader that found nothing would report 100% coverage -- a control "
     "that cannot fail is not a control"),

    ("arm", "DEAD at zero reach becomes a clean exit",
     "        return 2",
     "        return 0",
     "a dead instrument must not read as a clean result"),

    ("arm", "the print join takes the SHORTEST run over a tile",
     "                    tallest = max(hit, key=lambda x: x[\"h_spaces\"] or 0.0)",
     "                    tallest = min(hit, key=lambda x: x[\"h_spaces\"] or 0.0)",
     "a crop tile is small and several runs cross it; the mark the eye "
     "settled is the long one, and the headline must move"),
]


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()[:12]


def run_suite() -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *SUITE],
                       cwd=str(ROOT), env=env, capture_output=True, text=True)
    tail = [s for s in r.stdout.splitlines() if "passed" in s or "failed" in s]
    return r.returncode, (tail[-1] if tail else "")


def _one_arm(extra: list[str]) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-u", str(ARM), *ARM_ARGS, *extra],
                       cwd=str(ROOT), env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    keep = [s.strip() for s in out.splitlines()
            if any(t in s for t in ("REACH:", "DEAD", "cross-reader",
                                    "signature", "barlines", "stems",
                                    "height (spaces)"))]
    return r.returncode, "\n".join(keep)


def run_arm() -> tuple[int, str]:
    """⚠️⚠️ THE HEADLINE IS THREE RUNS, AND THE BATTERY IS WHY. Judged on the
    ordinary run alone, three arms SURVIVED — every one of them a control
    sitting at its CEILING on a page where the repair works: the cross-reader
    rate is 190 of 190, so `covered = len(cell_stems)` is identical; the cell
    signature is 0, so disabling its test is identical; and the DEAD exit is
    never taken, so returning 0 instead of 2 is identical. A control can only
    be mutation-tested in a state where it FAILS, so the arm's own two
    positive controls are part of the judge."""
    rcs, outs = [], []
    for extra in ([], ["--blind-the-reader"], ["--clip-like-a-cell"]):
        rc, out = _one_arm(extra)
        rcs.append(rc)
        outs.append(out)
    return (sum(rcs), "\n--\n".join(outs))


def main() -> int:
    force = "--force" in sys.argv
    if SENTINEL.exists():
        print("REFUSED: an in-flight sentinel exists -- a previous battery was "
              "interrupted and the tree may still carry a mutation.")
        print(SENTINEL.read_text())
        return 3
    rel = [str(p.relative_to(ROOT)) for p in TARGETS.values()]
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *rel],
                           cwd=str(ROOT), capture_output=True,
                           text=True).stdout.strip()
    if dirty and not force:
        print(f"REFUSED: a target is dirty:\n{dirty}\nCommit, or --force.")
        return 3

    OUT.mkdir(parents=True, exist_ok=True)
    snap = {k: v.read_bytes() for k, v in TARGETS.items()}
    SENTINEL.write_text("\n".join(
        f"{k}={TARGETS[k]} md5={md5b(v)}" for k, v in snap.items()) + "\n")

    print("=" * 78)
    print("BASELINE (the positive control -- every arm below is free if this "
          "is not green)")
    print("=" * 78)
    s_rc, s_out = run_suite()
    print(f"  SUITE  exit {s_rc}: {s_out}")
    a_rc, a_out = run_arm()
    print(f"  ARM    exit {a_rc}")
    print("  " + a_out.replace("\n", "\n  "))
    # ⚠️ THE ARM'S BASELINE IS NOT "exit 0". It is the EXPECTED PROFILE over
    # the three runs — ordinary 0, blinded 2 (DEAD), clipped 0 — summed to 2.
    # An arm whose blinded run stops declaring itself dead moves this.
    if s_rc != 0 or a_rc != 2:
        print("\n⚠️ BASELINE IS NOT GREEN. The battery measures nothing.")
        for k, v in snap.items():
            TARGETS[k].write_bytes(v)
        SENTINEL.unlink(missing_ok=True)
        return 4

    red, survived, bad = [], [], []
    for target, name, find, repl, why in ARMS:
        src = snap[target].decode("utf-8")
        if src.count(find) != 1:
            bad.append((name, f"{src.count(find)} occurrences in {target}"))
            print(f"\n{'-' * 78}\nARM [{target}]: {name}\n  ⚠️ BAD ANCHOR "
                  f"({src.count(find)} occurrences) -- REPORTED AS AN ERROR, "
                  f"never as a pass")
            continue
        TARGETS[target].write_text(src.replace(find, repl), encoding="utf-8")
        if target == "arm":
            rc, out = run_arm()
            moved = (rc != a_rc) or (out != a_out)
            judge = "ARM headline"
        else:
            rc, out = run_suite()
            moved = (rc != s_rc)
            judge = "unit suite"
        TARGETS[target].write_bytes(snap[target])
        (red if moved else survived).append((target, name, why))
        print(f"\n{'-' * 78}\nARM [{target}]: {name}")
        print(f"  judge: {judge}   expected: {why}")
        print(f"  exit {rc}  -> {'RED' if moved else 'SURVIVED'}")
        if not moved:
            print("  ⚠️ SURVIVOR -- a real test gap, not a pass.")

    ok = True
    for k, v in snap.items():
        TARGETS[k].write_bytes(v)
        if md5b(TARGETS[k].read_bytes()) != md5b(v):
            print(f"\n⚠️⚠️ RESTORE FAILED for {k}")
            ok = False
    if ok:
        SENTINEL.unlink(missing_ok=True)

    print("\n" + "=" * 78)
    print(f"RED {len(red)}   SURVIVED {len(survived)}   BAD ANCHORS {len(bad)}")
    print(f"restore VERIFIED by md5: {ok}")
    for t, n, _ in survived:
        print(f"  SURVIVOR [{t}] {n}")
    for n, m in bad:
        print(f"  BAD ANCHOR {n}: {m}")
    return 0 if (ok and not survived and not bad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
