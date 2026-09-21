"""Mutation battery over the SHIPPED gate and this lane's arms.

⚠️ THE JUDGE IS THE UNIT SUITE PLUS THIS LANE'S OWN ARM SHAPE, and the
baseline must be GREEN before any arm is read or every arm is red for free.
The suite is `test_stem_notehead_gate.py` (the gate's three cases, the
flag-off identity and its positive control, the gather wiring) plus
`test_flag_default_direction.py` (the flag's direction is DERIVED, not
restated) plus the stem/beam suites the gate sits inside.

⚠️ ONE RED ARM IS NOT A BATTERY. A SURVIVOR is a real gap, not a pass.

⚠️ A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT — WHICH IS NOT THE
SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS NEITHER.
A BYTE snapshot on disk, an in-flight SENTINEL written before the first arm,
a restore VERIFIED by md5, and a refusal to start on a dirty target without
`--force`.

⚠️ THE ARMS DO NOT RUN THE PLATE ARMS. `gate_arm.py` takes ~110 s per
document and every arm here is a claim about the RULE, not about a plate; the
plate arms' own controls (faithfulness to 1,920 / 2,305, one-sidedness,
positive control) are what guard those.
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

LINE = ROOT / "tools/omr/line_detection.py"
GATHER = ROOT / "tools/omr/staged/gather.py"
ARM = HERE / "gate_arm.py"
PERBAR = HERE / "probe_per_bar.py"
TARGETS = {"line": LINE, "gather": GATHER, "arm": ARM, "perbar": PERBAR}

SUITES = [
    "tools/omr/tests/test_stem_notehead_gate.py",
    "tools/omr/tests/test_flag_default_direction.py",
    "tools/omr/tests/test_line_detection_stems.py",
    "tools/omr/tests/test_line_detection_beams.py",
    "tools/omr/tests/test_line_detection_stroke_reader.py",
    "tools/omr/tests/test_vertical_runs.py",
]

#: (target, name, find, replace, what it must break)
ARMS = [
    # ── THE GATE ITSELF ───────────────────────────────────────────────────
    ("line", "the gate is applied to the PARTNER as well as the subject",
     "        if heads is not None and on_head[i]:\n"
     "            kept.append(stem)\n"
     "            continue\n"
     "        for j in range(len(stems)):\n"
     "            if i == j or abs(centres[i] - centres[j]) > max_dx:\n"
     "                continue",
     "        if heads is not None and on_head[i]:\n"
     "            kept.append(stem)\n"
     "            continue\n"
     "        for j in range(len(stems)):\n"
     "            if i == j or abs(centres[i] - centres[j]) > max_dx:\n"
     "                continue\n"
     "            if heads is not None and on_head[j]:\n"
     "                continue",
     "an accidental's stroke beside a real stem loses its only partner and "
     "SURVIVES as a false stem -- the form this lane rejected"),

    ("line", "`None` and `[]` become the same argument",
     "    on_head = ([False] * len(stems) if heads is None\n"
     "               else [_meets_a_notehead(s, heads) for s in stems])",
     "    on_head = [_meets_a_notehead(s, heads or []) for s in stems]",
     "*no gate* and *the gate with nothing to protect* must stay different; "
     "collapsing them is this repo's own way of converting cannot-tell into "
     "a definite answer"),

    ("line", "the gate fires with the flag OFF",
     "        gate_heads = (list(noteheads) if enable_notehead_gate\n"
     "                      and noteheads is not None else None)",
     "        gate_heads = (list(noteheads) if noteheads is not None\n"
     "                      else None)",
     "flag-off must be byte-identical; a DATA-only gate makes the default "
     "path move and breaks every stem arm in this repo"),

    ("line", "the flag alone fires with no noteheads supplied",
     "        gate_heads = (list(noteheads) if enable_notehead_gate\n"
     "                      and noteheads is not None else None)",
     "        gate_heads = (list(noteheads or []) if enable_notehead_gate\n"
     "                      else None)",
     "the legacy `transcribe` path passes no detections and must stay "
     "unchanged BY CONSTRUCTION"),

    ("line", "the flag defaults ON",
     '    return os.environ.get(STEM_NOTEHEAD_GATE_ENV, "0").strip().lower() in (\n'
     '        "1", "true", "yes", "on")',
     '    return os.environ.get(STEM_NOTEHEAD_GATE_ENV, "1").strip().lower() in (\n'
     '        "1", "true", "yes", "on")',
     "a default-OFF flag with an allow-list test -- the derived guard reads "
     "the predicate on its own default and must see the flip"),

    ("line", "the flag's OFF test becomes a DENY-list",
     '    return os.environ.get(STEM_NOTEHEAD_GATE_ENV, "0").strip().lower() in (\n'
     '        "1", "true", "yes", "on")',
     '    return os.environ.get(STEM_NOTEHEAD_GATE_ENV, "0").strip().lower() '
     'not in (\n        "0", "", "false", "no", "off")',
     "CLAUDE.md: a flag's OFF test must follow its DEFAULT -- a default-OFF "
     "deny-list is switched ON by a typo"),

    ("line", "notehead overlap becomes touching-counts",
     "        if min(sx1, hx + hw) - max(sx0, hx) > 0 \\\n"
     "                and min(sy1, hy + hh) - max(sy0, hy) > 0:",
     "        if min(sx1, hx + hw) - max(sx0, hx) >= 0 \\\n"
     "                and min(sy1, hy + hh) - max(sy0, hy) >= 0:",
     "a stroke merely TOUCHING a head's bounding box is not standing on it; "
     "the loose test protects the neighbour's strokes too"),

    ("line", "the gate ignores y and matches on x alone",
     "        if min(sx1, hx + hw) - max(sx0, hx) > 0 \\\n"
     "                and min(sy1, hy + hh) - max(sy0, hy) > 0:",
     "        if min(sx1, hx + hw) - max(sx0, hx) > 0:",
     "every stroke in a head's COLUMN would claim it, including an "
     "accidental's strokes standing directly above or below the note"),

    ("line", "`noteheads` is not forwarded from `detect_lines`",
     "    stems = detect_stems(cell, candidates_out=candidates_out,\n"
     "                         noteheads=noteheads)",
     "    stems = detect_stems(cell, candidates_out=candidates_out)",
     "the staged path reaches `detect_stems` only through `detect_lines`, so "
     "dropping the forward makes the gate silently inert in production while "
     "every direct-call test still passes"),

    # ── THE WIRING ────────────────────────────────────────────────────────
    ("gather", "`gather()` stops handing the detections to the CV rung",
     "        gather_cv_lines(log, cells, local, detections)",
     "        gather_cv_lines(log, cells, local)",
     "the gate has no data on the staged path and is silently the shipped "
     "rule -- the exact fault this lane exists to repair"),

    ("gather", "a missing detector becomes an EMPTY head list",
     "    if detections is None:\n        return None",
     "    if detections is None:\n        return []",
     "`gather_detections(detector=None)` is a supported mode; turning it "
     "into *the gate with nothing to protect* is a different claim"),

    ("gather", "the head boxes are read as CORNERS, not x/y/w/h",
     "        heads.append((float(d.x_canonical), float(d.y_canonical),\n"
     "                      float(d.width_canonical), float(d.height_canonical)))",
     "        heads.append((float(d.x_canonical), float(d.y_canonical),\n"
     "                      float(d.x_canonical) + float(d.width_canonical),\n"
     "                      float(d.y_canonical) + float(d.height_canonical)))",
     "the three-box-conventions trap: a corner box read as a width box gives "
     "a head far larger than the print and protects everything near it"),

    ("gather", "every detection counts as a notehead",
     '        if "notehead" not in str(getattr(d, "smufl_name", "")).lower():\n'
     "            continue",
     "        if False:\n            continue",
     "an accidental, a rest and a clef would all protect a stroke; the gate's "
     "whole claim is that a NOTEHEAD is there"),

    # ── THE ARMS' OWN CONTROLS ────────────────────────────────────────────
    ("arm", "the faithfulness check cannot fail",
     "    elif n_off != expect:",
     "    elif False:",
     "the OFF arm reproducing the shared record's 1,920 / 2,305 strokes is "
     "what makes any delta comparable to anything committed"),

    ("arm", "the one-sidedness check cannot fail",
     "    if lost:",
     "    if False:",
     "the gate can only ever UN-condemn; a lost stroke means the relation "
     "was changed in a way this arm's author did not intend"),

    ("arm", "the arm accepts an inherited flag from the shell",
     "    if STEM_NOTEHEAD_GATE_ENV in os.environ:",
     "    if False:",
     "an inherited value makes both arms the same one -- the hazard this "
     "repo has paid for twice"),

    ("arm", "the positive control cannot fail",
     "    if len(rescued) == 0 and len(lost) == 0:",
     "    if False:",
     "two identical arms is what a flag that does not reach the code "
     "produces, and it would read as *the gate is harmless*"),

    ("arm", "DEAD at zero noteheads becomes a clean exit",
     '    if n_heads == 0:\n        print("DEAD: the detector found NO noteheads',
     '    if False:\n        print("DEAD: the detector found NO noteheads',
     "with no noteheads the ON arm IS the OFF arm and a clean zero would "
     "read as *the gate changes nothing here*"),

    # ── THE PER-BAR PROBE ─────────────────────────────────────────────────
    ("perbar", "the per-bar probe scores a thickness whose cells != bars",
     "            if set(got) != set(n_bars) or any(\n"
     "                    len(got[s]) != n_bars[s] for s in n_bars):",
     "            if False:",
     "`ground-truth.json`'s own caveat: where the page re-segments, a cell "
     "index is not a bar number and the comparison is nonsense"),

    ("perbar", "the composition check is silenced",
     "            emptied = [r for r in rows if r[\"truth\"] > 0 and r[\"on\"] == 0]",
     "            emptied = []",
     "the gated COUNT equals the truth on the chord bar by coincidence -- "
     "four strokes on two printed objects -- and reporting the count alone "
     "would credit the gate with getting that bar right"),

    ("perbar", "x-clustering uses a window wide enough to merge every stroke",
     "CLUSTER_SPACES = 0.9",
     "CLUSTER_SPACES = 99.0",
     "the composition statement is *four strokes are two objects*; a window "
     "that merges everything makes every bar read as one object"),
]


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()[:12]


def headline() -> tuple[int, str]:
    """The unit suites, plus the two probes' importability and shape.

    ⚠️ The probes are IMPORTED and their module-level constants read rather
    than run: running them costs weights, LilyPond and minutes, and every arm
    here is a claim about a rule. What is checked is that each still parses
    and still carries the control the arm targets -- which is what makes a
    `--find/--replace` arm on them visible at all.
    """
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("OMR_STEM_NOTEHEAD_GATE", None)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *SUITES],
                       cwd=str(ROOT), env=env, capture_output=True, text=True)
    tail = [ln for ln in (r.stdout + r.stderr).splitlines()
            if "passed" in ln or "failed" in ln or "error" in ln.lower()]
    # The arms' own source-level controls, as a second signal, so an arm that
    # deletes a guard from a probe is visible without running the probe.
    marks = []
    for name, path in (("arm", ARM), ("perbar", PERBAR)):
        src = path.read_text(encoding="utf-8")
        # ⚠️ SYNTAX FIRST: a mutation that breaks the file must not read as a
        # missing guard.
        try:
            compile(src, str(path), "exec")
        except SyntaxError as exc:
            marks.append(f"{name}:SYNTAX:{exc.lineno}")
            continue
        for needle in ("elif n_off != expect:", "if lost:",
                       "if STEM_NOTEHEAD_GATE_ENV in os.environ:",
                       "if len(rescued) == 0 and len(lost) == 0:",
                       "if n_heads == 0:",
                       "len(got[s]) != n_bars[s] for s in n_bars",
                       'r["truth"] > 0 and r["on"] == 0',
                       "CLUSTER_SPACES = 0.9"):
            if needle in src:
                marks.append(f"{name}:{needle[:28]}")
    return r.returncode, "\n".join(tail + sorted(marks))


def main() -> int:
    force = "--force" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    if SENTINEL.exists():
        print("REFUSED: an in-flight sentinel exists -- a previous battery "
              "was interrupted and the tree may still carry a mutation.")
        print(SENTINEL.read_text())
        return 3
    rel = [str(p.relative_to(ROOT)) for p in TARGETS.values()]
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *rel],
                           cwd=str(ROOT), capture_output=True,
                           text=True).stdout.strip()
    if dirty and not force:
        print(f"REFUSED: a target is dirty:\n{dirty}\nCommit, or --force.")
        return 3

    snap = {k: v.read_bytes() for k, v in TARGETS.items()}
    SENTINEL.write_text("\n".join(
        f"{k}={TARGETS[k]} md5={md5b(v)}" for k, v in snap.items()) + "\n")

    print("=" * 78)
    print("BASELINE (the positive control -- every arm is free if this is "
          "not green)")
    print("=" * 78)
    b_rc, b_out = headline()
    print(f"  exit {b_rc}\n  " + b_out.replace("\n", "\n  "))
    if b_rc != 0:
        print("\n⚠️ BASELINE IS NOT GREEN. The battery measures nothing.")
        for k, v in snap.items():
            TARGETS[k].write_bytes(v)
        SENTINEL.unlink(missing_ok=True)
        return 4

    red, survived, bad = [], [], []
    for target, name, find, repl, why in ARMS:
        src = snap[target].decode("utf-8")
        if src.count(find) != 1:
            bad.append((target, name, f"{src.count(find)} occurrences"))
            print(f"\n{'-' * 78}\nARM [{target}]: {name}\n"
                  f"  ⚠️ BAD ANCHOR ({src.count(find)} occurrences) -- "
                  f"REPORTED AS AN ERROR, not a pass")
            continue
        TARGETS[target].write_text(src.replace(find, repl), encoding="utf-8")
        rc, out = headline()
        TARGETS[target].write_bytes(snap[target])
        moved = (rc != b_rc) or (out != b_out)
        (red if moved else survived).append((target, name, why))
        print(f"\n{'-' * 78}\nARM [{target}]: {name}")
        print(f"  expected: {why}")
        print(f"  exit {rc}  -> {'RED' if moved else 'SURVIVED'}")
        if not moved:
            print("  ⚠️ SURVIVOR -- a real gap, not a pass.")

    ok = True
    for k, v in snap.items():
        TARGETS[k].write_bytes(v)
        if md5b(TARGETS[k].read_bytes()) != md5b(v):
            print(f"\n⚠️⚠️ RESTORE FAILED for {k}")
            ok = False
    if ok:
        SENTINEL.unlink(missing_ok=True)

    print("\n" + "=" * 78)
    print(f"RED {len(red)}   SURVIVED {len(survived)}   "
          f"BAD ANCHORS {len(bad)}")
    print(f"restore VERIFIED by md5: {ok}")
    for t, n, _ in survived:
        print(f"  SURVIVOR [{t}] {n}")
    for t, n, m in bad:
        print(f"  BAD ANCHOR [{t}] {n}: {m}")
    return 0 if (ok and not survived and not bad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
