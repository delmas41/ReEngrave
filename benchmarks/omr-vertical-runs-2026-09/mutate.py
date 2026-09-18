"""Mutation battery for `Q.VERTICAL_RUN` — the SHIPPED code and the INSTRUMENT.

⚠️⚠️ TWO SUBJECTS, TWO JUDGES, AND THE SPLIT IS THE POINT. This lane ships
code under `tools/` as well as a probe, and a battery that mutated only one of
them would measure only one of them:

  * arms under `tools/` are judged by the UNIT SUITE
    (`tools/omr/tests/test_vertical_runs.py`), which must go RED;
  * arms under this directory are judged by the ARM's own HEADLINE, which must
    MOVE.

An arm that leaves its judge unchanged is a SURVIVOR and a real test gap.

⚠️ ONE RED ARM IS NOT A BATTERY, and it needs a POSITIVE CONTROL IN THE SAME
CLASS: the baseline must be GREEN before any arm is read, because if it is not
then every arm is red for free and the battery measures nothing.

⚠️ A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT -- WHICH IS NOT THE
SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS NEITHER.
So: a BYTE snapshot on disk (not in memory, which dies with the process and
left a sibling lane's mutation on disk indistinguishable from a legitimate
edit), an in-flight SENTINEL written before the first arm and deleted on a
clean exit, a VERIFIED restore by md5, and a refusal to start on a dirty tree
without `--force`.

⚠️ `PYTHONDONTWRITEBYTECODE=1` IN EVERY ARM. A stale `.pyc` made two arms in a
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

LINEDET = ROOT / "tools" / "omr" / "line_detection.py"
GATHER = ROOT / "tools" / "omr" / "staged" / "gather.py"
ARM = HERE / "vertical_run_arm.py"

TARGETS = {"linedet": LINEDET, "gather": GATHER, "arm": ARM}

#: The unit suite, the judge for every `tools/` arm.
SUITE = ["tools/omr/tests/test_vertical_runs.py"]

#: One cheap page, the judge for every instrument arm. ⚠️ Litolff p1: the
#: record's own 190 strokes, so the faithfulness control is live.
ARM_ARGS = [
    "--pdf", "library/editions/beethoven/symphony-5-op67/"
             "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
             "imslp984073.pdf",
    "--pages", "1",
    "--record", "library/_shared-records/beethoven5-p1-p4.record.json",
    "--label", "MUTATE", "--json", str(OUT / ".mutate-arm.json"),
]

#: (target, name, find, replace, what it must break)
ARMS = [
    # ── the SHIPPED filter chain ─────────────────────────────────────────────
    ("linedet", "the SHORT and TALL reasons are swapped",
     'RUN_TOO_SHORT if h < min_h else RUN_TOO_TALL',
     'RUN_TOO_TALL if h < min_h else RUN_TOO_SHORT',
     "one test per filter must fail -- a single fixture asserting 'seven "
     "outcomes appear' would pass with these swapped, which is why there is "
     "one test each"),

    ("linedet", "the WIDE reason is reported as AT A CELL EDGE",
     '            _note(x, y, w, h, area, RUN_TOO_WIDE)',
     '            _note(x, y, w, h, area, RUN_AT_CELL_EDGE)',
     "test_too_wide must fail"),

    ("linedet", "a refused candidate is silently dropped (the OLD behaviour)",
     '''        if h < min_h or h > max_h:
            _note(x, y, w, h, area,
                  RUN_TOO_SHORT if h < min_h else RUN_TOO_TALL)
            continue''',
     '''        if h < min_h or h > max_h:
            continue''',
     "the whole point of the quantity: a candidate the pipeline found and "
     "discarded must not vanish"),

    ("linedet", "the pair rule's drops stay labelled `accepted`",
     '                candidates_out[i] = replace(cand, outcome=RUN_PAIRED)',
     '                pass',
     "the seventh outcome must be distinguishable from the six -- a pair "
     "rejection is the only one a candidate's own measurements cannot explain"),

    ("linedet", "the pair re-stamp fires on EVERY candidate, not the dropped",
     '                if (cand.x, cand.y, cand.w, cand.h) in kept_boxes:\n'
     '                    continue',
     '                pass',
     "a SURVIVING stroke must not be labelled PAIRED"),

    ("linedet", "the box is emitted as CORNERS instead of [x, y, w, h]",
     '                x=int(x), y=int(y), w=int(w), h=int(h), area=int(area),',
     '                x=int(x), y=int(y), w=int(x + w), h=int(y + h), '
     'area=int(area),',
     "the convention test must fail -- reading one box spelling as another is "
     "what produced a NEGATIVE width and a clean believable zero in a sibling "
     "lane"),

    ("linedet", "`accepted` is derived from the wrong word",
     '        return self.outcome == RUN_ACCEPTED',
     '        return self.outcome != RUN_ACCEPTED',
     "every accepted/refused assertion must fail"),

    ("linedet", "`detect_lines` drops the out-parameter on the floor",
     '    stems = detect_stems(cell, candidates_out=candidates_out)',
     '    stems = detect_stems(cell)',
     "the forwarding test must fail, and with it the whole gather rung -- "
     "`gather_cv_lines` reaches `detect_stems` only through here"),

    ("linedet", "the dimension group silently includes the pair rule",
     '''RUN_DIMENSION_REASONS = (
    RUN_TOO_SHORT, RUN_TOO_TALL, RUN_TOO_WIDE,
    RUN_AT_CELL_EDGE, RUN_TOO_LITTLE_AREA, RUN_ASPECT,
)''',
     '''RUN_DIMENSION_REASONS = (
    RUN_TOO_SHORT, RUN_TOO_TALL, RUN_TOO_WIDE,
    RUN_AT_CELL_EDGE, RUN_TOO_LITTLE_AREA, RUN_ASPECT, RUN_PAIRED,
)''',
     "§9's question -- how much is refused BY DIMENSION -- must stop being "
     "answerable, and the six-not-seven test must fail"),

    # ── the GATHER rung ──────────────────────────────────────────────────────
    ("gather", "the flag's ON test becomes a DENY-list (wrong for default-OFF)",
     '    return os.environ.get(VERTICAL_RUNS_ENV, "0").strip().lower() in (\n'
     '        "1", "true", "yes", "on")',
     '    return os.environ.get(VERTICAL_RUNS_ENV, "0").strip().lower() '
     'not in (\n        "0", "", "false", "no", "off")',
     "a typo must not switch a document ONTO an unpriced gather change -- the "
     "allow-list test must fail, and so must the derived flag-direction guard"),

    ("gather", "the flag defaults ON",
     'os.environ.get(VERTICAL_RUNS_ENV, "0")',
     'os.environ.get(VERTICAL_RUNS_ENV, "1")',
     "the default-OFF test must fail"),

    ("gather", "flag-off still allocates the list, so the rung writes rows",
     '        runs: Optional[list] = [] if vertical_runs_enabled() else None',
     '        runs: Optional[list] = []',
     "`off means ABSENT, not quiet` must fail -- a flag-off record would stop "
     "being byte-identical to a tree without the quantity"),

    ("gather", "the page box is DEFAULTED instead of DECLINED",
     '''        else:
            optional["frame_note"] = (
                "no page box: cell has no bbox_page_px/upscale_factor")''',
     '''        else:
            optional.update(run_bbox_page_px=[0.0, 0.0, 0.0, 0.0],
                            run_y_top_page=0.0, run_y_bottom_page=0.0,
                            run_x_center_page=0.0)''',
     "a fallback must never convert `cannot tell` into a definite answer -- "
     "and a zeroed page box is the frame error this quantity exists to avoid"),

    ("gather", "the staff-space unit is the nominal 100 px",
     '        if cand.line_spacing > 0:\n'
     '            optional.update(\n'
     '                run_width_spaces=round(cand.width_spaces, 3),\n'
     '                run_height_spaces=round(cand.height_spaces, 3),\n'
     '                run_staff_space_px=round(cand.line_spacing, 2))',
     '        if cand.line_spacing > 0:\n'
     '            optional.update(\n'
     '                run_width_spaces=round(cand.w / 100.0, 3),\n'
     '                run_height_spaces=round(cand.h / 100.0, 3),\n'
     '                run_staff_space_px=100.0)',
     "`_upscale_to_canonical` scales a too-wide cell by WIDTH, so the nominal "
     "is silently wrong on a minority of cells -- the cell's-own-unit test "
     "must fail"),

    ("gather", "the candidate glyph base collides with the ink base",
     '_VERTICAL_RUN_GLYPH_BASE = 300_000',
     '_VERTICAL_RUN_GLYPH_BASE = 200_000',
     "a collision would not raise; it would silently merge two readers' rows "
     "into one subject -- the disjoint-subject test must fail"),

    ("gather", "an empty cell writes nothing instead of abstaining NO_INK",
     '''                log.abstain(sub, Q.VERTICAL_RUN, reader=READERS.CV_LINES,
                            frame=frame, reason=ABSTAIN.NO_INK,
                            image="no_staff" if erased else "original",
                            staff_lines_erased=erased)''',
     '''                pass''',
     "ABSENT and DECLINED must stay distinguishable -- the honest `NO_INK` "
     "is the one case where that reason word is true for this family"),

    # ── the INSTRUMENT ───────────────────────────────────────────────────────
    ("arm", "the faithfulness control compares against the WRONG pages",
     '                if int(p[1]) in pages:',
     '                if True:',
     "the control must refuse -- this is exactly the failure its own first "
     "run had, and a control that cannot fail is not one"),

    ("arm", "the barline predicate tests only the TOP end",
     '''    return (abs(y_top - min(lines)) <= tol
            and abs(y_bot - max(lines)) <= tol)''',
     '''    return abs(y_top - min(lines)) <= tol''',
     "the fire rates must move -- `BOTH ends` is the whole of Sean's rule"),

    ("arm", "the end offsets are unsigned, so a systematic offset reads as "
            "scatter",
     '        r["d_top"] = (r["y_top"] - min(lines)) / sp',
     '        r["d_top"] = abs(r["y_top"] - min(lines)) / sp',
     "the diagnosis must change -- the `too TALL` bucket's median -4.00 is "
     "what NAMES the cell padding, and an absolute value hides the sign"),
]


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def run_suite() -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *SUITE],
                       cwd=str(ROOT), env=env, capture_output=True, text=True)
    tail = [ln for ln in (r.stdout + r.stderr).splitlines()
            if "passed" in ln or "failed" in ln or "error" in ln.lower()]
    return r.returncode, "\n".join(tail[-3:])


def run_arm() -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-u", str(ARM), *ARM_ARGS],
                       cwd=str(ROOT), env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    keep = [s.strip() for s in out.splitlines()
            if any(t in s for t in ("REACH:", "FAITHFULNESS", "ABORT", "DEAD",
                                    "%", "COST:", "d_top", "-4.00"))]
    return r.returncode, "\n".join(keep)


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
    lines = [f"{k}={TARGETS[k]} md5={md5b(v)}" for k, v in snap.items()]
    SENTINEL.write_text("\n".join(lines) + "\n")

    print("=" * 78)
    print("BASELINE (the positive control -- every arm below is free if this "
          "is not green)")
    print("=" * 78)
    s_rc, s_out = run_suite()
    print(f"  SUITE  exit {s_rc}: {s_out}")
    a_rc, a_out = run_arm()
    print(f"  ARM    exit {a_rc}")
    print("  " + a_out.replace("\n", "\n  ")[:1600])
    if s_rc != 0 or a_rc != 0:
        print("\n⚠️ BASELINE IS NOT GREEN. The battery measures nothing.")
        for k, v in snap.items():
            TARGETS[k].write_bytes(v)
        SENTINEL.unlink(missing_ok=True)
        return 4

    red, survived, bad = [], [], []
    for target, name, find, repl, why in ARMS:
        src = snap[target].decode("utf-8")
        if src.count(find) != 1:
            bad.append((name, f"BAD ANCHOR: {src.count(find)} occurrences in "
                              f"{target}"))
            print(f"\n{'-' * 78}\nARM: {name}\n  ⚠️ BAD ANCHOR "
                  f"({src.count(find)} occurrences in {target}) -- REPORTED "
                  f"AS AN ERROR, never as a pass")
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
        else:
            print(f"  {out.splitlines()[-1] if out else ''}")

    # ── restore, and VERIFY it ──────────────────────────────────────────────
    ok = True
    for k, v in snap.items():
        TARGETS[k].write_bytes(v)
        if md5b(TARGETS[k].read_bytes()) != md5b(v):
            print(f"\n⚠️⚠️ RESTORE FAILED for {k} -- the tree is NOT as the "
                  f"battery found it.")
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
