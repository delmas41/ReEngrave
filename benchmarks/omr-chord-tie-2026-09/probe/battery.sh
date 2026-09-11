#!/bin/zsh
# A mutation battery for the CHORD TIE repair. Shape copied from
# `benchmarks/omr-staged-fermata-2026-09/probe/battery.sh`.
#
# ⚠️ RESTORES FROM git, never from a hand-named backup, and MUTATES COMMITTED
# CONTENT (`git show HEAD:<path>`) — so commit before running.
#
# ⚠️ ONE RED ARM IS NOT A BATTERY, and a battery can pass by REFUSING
# everything as easily as by accepting everything. ARM 0 is the positive
# control on the unmutated tree; an arm reporting BROKEN is a harness failure
# and is NOT a survivor.
#
# ⚠️ EVERY MUTATION IS ANCHORED ON A WHOLE EXPRESSION. The tie-chain session
# lost an arm to a fragment that occurred three times in one file and silently
# mutated a different function; `arm` refuses a mutation that does not apply,
# and the "NOT APPLIED" line is a harness failure, not a survivor.
T="tools/omr/tests/test_staged_tie_chain.py tools/omr/tests/test_export.py tools/omr/tests/test_staged_export.py tools/omr/tests/test_voicing.py"
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
src = subprocess.run(["git","show",f"HEAD:{path}"],capture_output=True,text=True).stdout
old, new = expr.split("||")
if not src:
    sys.stderr.write(f"HARNESS: empty HEAD blob for {path}\n"); sys.exit(3)
if src.count(old) != 1:
    sys.stderr.write(f"MUTATION IS NOT UNIQUE ({src.count(old)}x): {old!r}\n")
    sys.exit(3)
open(path,"w").write(src.replace(old,new,1))
PY
  if [ $? -ne 0 ]; then echo "NOT APPLIED (harness failure): $3"; git checkout -- "$1"; return; fi
  echo "$(check): $3"
  git checkout -- "$1"
}

E=tools/omr/export.py
X=tools/omr/staged/export.py
V=tools/omr/voicing.py
echo "ARM 0 positive control on the unmutated tree: $(check)  (expected SURVIVED, $EXPECT passed)"

# ── the LEGACY renderer: the defect itself, and its neighbours ────────────
arm $E 'tied_to_next=bool(nh.get("tied_to_next")),||tied_to_next=(bool(event.get("tied_to_next")) and ni == 0),' \
       "LEGACY: restore the hoist for tie STARTS (the original defect)"
arm $E 'tied_from_prev=bool(nh.get("tied_from_prev")),||tied_from_prev=(bool(event.get("tied_from_prev")) and ni == 0),' \
       "LEGACY: restore the hoist for tie STOPS"
arm $E 'tied_to_next=bool(nh.get("tied_to_next")),||tied_to_next=bool(nh.get("tied_from_prev")),' \
       "LEGACY: read the WRONG end's flag"
arm $E 'tied_to_next=bool(nh.get("tied_to_next")),||tied_to_next=any(h.get("tied_to_next") for h in event["noteheads"]),' \
       "LEGACY: tie EVERY member of a chord holding one tie"

# ── the STAGED renderer ───────────────────────────────────────────────────
arm $X 'tied_to_next=bool(head.get("tied_to_next")),||tied_to_next=bool(ev.get("tied_to_next")) if n == 0 else False,' \
       "STAGED: restore the hoist for tie STARTS"
arm $X 'tied_from_prev=bool(head.get("tied_from_prev")),||tied_from_prev=bool(ev.get("tied_from_prev")) if n == 0 else False,' \
       "STAGED: restore the hoist for tie STOPS"
arm $X 'if head.get("tied_to_next"):
                counters["ties"] += 1||if ev.get("tied_to_next") and n == 0:
                counters["ties"] += 1' \
       "STAGED: count ties per EVENT again, not per written element"
arm $X 'if head.get(key):
                        counters[name + "_on_an_upper_chord_note"] += 1||if True:
                        counters[name + "_on_an_upper_chord_note"] += 1' \
       "STAGED: the upper-note counter fires on every upper member"

# ── voicing, which must keep the event-level flag for LILYPOND ────────────
arm $V 'tied_to_next = any(n.get("tied_to_next") for n in group)||tied_to_next = bool(group[0].get("tied_to_next"))' \
       "VOICING: the LilyPond chord flag reads only the lowest head"

# ── the POSITIVE CONTROL IN THE SAME CLASS ────────────────────────────────
# ⚠️ Every arm above BREAKS the tie position. A suite that went red on all of
# them could still be one that rejects any tie at all. This arm breaks a case
# that must NOT be flagged -- a single-note tie, which the repair does not
# touch -- and the suite must still go red.
arm $E 'tied_to_next=bool(nh.get("tied_to_next")),||tied_to_next=False,' \
       "CONTROL: no note is ever tied (a single-note tie must fail too)"
