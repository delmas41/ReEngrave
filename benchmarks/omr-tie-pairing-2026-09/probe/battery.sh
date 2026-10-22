#!/bin/zsh
# A mutation battery for the TIE PAIRING repair. Shape copied from
# `benchmarks/omr-chord-tie-2026-09/probe/battery.sh`.
#
# ⚠️ RESTORES FROM git and MUTATES COMMITTED CONTENT (`git show HEAD:<path>`),
# so commit before running.
#
# ⚠️⚠️ DO NOT RUN THIS CONCURRENTLY WITH AN A/B READING THE SAME WORKTREE. It
# `git checkout`s the files it mutates; the chord-tie session lost a three-arm
# run to exactly that race and had to discard it.
#
# ⚠️ ONE RED ARM IS NOT A BATTERY, and a battery of arms that break a REFUSAL
# can pass by refusing everything. ARM 0 is the positive control on the
# unmutated tree; ARM P is the positive control IN THE SAME CLASS — it makes
# the rule refuse every arc, and the suite must still go red.
#
# ⚠️ EVERY MUTATION IS ANCHORED ON A WHOLE EXPRESSION and is refused unless it
# applies exactly once. "NOT APPLIED" is a harness failure, never a survivor.
T="tools/omr/tests/test_tie_pairing.py tools/omr/tests/test_export.py"
EXPECT=$(python3 -m pytest ${=T} -q 2>&1 | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')

check() {  # -> RED | SURVIVED | BROKEN
  local out; out=$(python3 -m pytest ${=T} -q 2>&1 | tail -3)
  if   echo "$out" | grep -q "no tests ran";  then echo "BROKEN(no tests)"
  elif echo "$out" | grep -q "error";          then echo "BROKEN(collect error)"
  elif echo "$out" | grep -q "failed";         then echo "RED"
  elif echo "$out" | grep -q "$EXPECT passed"; then echo "SURVIVED"
  else echo "BROKEN(unrecognised: $out)"; fi
}

arm() {  # file, 'old||new', name
  python3 - "$1" "$2" <<'PY'
import subprocess, sys
path, expr = sys.argv[1], sys.argv[2]
src = subprocess.run(["git", "show", f"HEAD:{path}"],
                     capture_output=True, text=True).stdout
old, new = expr.split("||")
if not src:
    sys.stderr.write(f"HARNESS: empty HEAD blob for {path}\n"); sys.exit(3)
if src.count(old) != 1:
    sys.stderr.write(f"MUTATION IS NOT UNIQUE ({src.count(old)}x): {old!r}\n")
    sys.exit(3)
open(path, "w").write(src.replace(old, new, 1))
PY
  if [ $? -ne 0 ]; then echo "NOT APPLIED (harness failure): $3"; git checkout -- "$1"; return; fi
  echo "$(check): $3"
  git checkout -- "$1"
}

R=tools/omr/transcribe.py
E=tools/omr/export.py
echo "ARM 0 positive control on the unmutated tree: $(check)  (expected SURVIVED, $EXPECT passed)"

# ── the repair itself, in `transcribe` ───────────────────────────────────────
arm $R 'TIE_SAME_POSITION_MAX_SPACES = 0.25||TIE_SAME_POSITION_MAX_SPACES = 0.0' \
       "TRANSCRIBE: shrink the window to zero — the old rule, restored"
arm $R 'TIE_SAME_POSITION_MAX_SPACES = 0.25||TIE_SAME_POSITION_MAX_SPACES = 3.0' \
       "TRANSCRIBE: widen the window past a step, so any pair qualifies"
arm $R '            if at_one_position:
                _, best_left, best_right = min(at_one_position,
                                               key=lambda t: t[0])||            if False:
                _, best_left, best_right = min(at_one_position,
                                               key=lambda t: t[0])' \
       "TRANSCRIBE: delete the same-position branch outright"
arm $R '                and abs(yl - yr) / avg_nh_h <= TIE_SAME_POSITION_MAX_SPACES
            ]||                and abs(yl - yr) / avg_nh_h > TIE_SAME_POSITION_MAX_SPACES
            ]' \
       "TRANSCRIBE: invert the window — prefer heads at DIFFERENT positions"
arm $R '                _, best_left, best_right = min(at_one_position,
                                               key=lambda t: t[0])||                _, best_left, best_right = max(at_one_position,
                                               key=lambda t: t[0])' \
       "TRANSCRIBE: take the FURTHEST same-position pair, not the nearest"
# ⚠️ An arm swapping start and stop in the tie-break was written and REMOVED:
# the line it anchored on does not exist (the branch unpacks a 3-tuple), so the
# harness correctly reported NOT APPLIED. A harness failure is not a survivor,
# and an arm that can never apply is not a test — it is noise in the report.
#
# ⚠️ An arm swapping the two dx terms of the tie-break is an EQUIVALENT MUTANT
# and is also removed: `dxl + dxr` is symmetric, so relabelling the loop
# variables cannot change the answer. It SURVIVED on the first run, and that is
# a property of the arithmetic rather than a gap in the tests. Recorded here so
# nobody writes it again.

# ── the export MIRROR, which the veto's bookkeeping depends on ───────────────
arm $E '    if at_one_position:
        _, best_left, best_right = min(at_one_position, key=lambda t: t[0])||    if False:
        _, best_left, best_right = min(at_one_position, key=lambda t: t[0])' \
       "EXPORT: let the mirror drift — delete its same-position branch"
arm $E '        and abs(yl - yr) / avg_h <= TIE_SAME_POSITION_MAX_SPACES||        and abs(yl - yr) / avg_h >= TIE_SAME_POSITION_MAX_SPACES' \
       "EXPORT: invert the mirror's window"
arm $E '    from .transcribe import TIE_SAME_POSITION_MAX_SPACES||    TIE_SAME_POSITION_MAX_SPACES = 0.9  # restated, not imported' \
       "EXPORT: restate the constant instead of importing it (drift by hand)"

# ── ARM P: the positive control IN THE SAME CLASS ────────────────────────────
arm $R '        if (
            best_left is not None
            and best_right is not None
            and best_left is not best_right
        ):
            at_one_position = [||        if (
            False
            and best_right is not None
            and best_left is not best_right
        ):
            at_one_position = [' \
       "ARM P: never enter the branch at all (refuse-everything control)"
