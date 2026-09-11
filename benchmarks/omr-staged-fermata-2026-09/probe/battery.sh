#!/bin/zsh
# A mutation battery for the fermata and voices wiring.
#
# ⚠️ RESTORES FROM git, never from a hand-named backup — the articulation
# battery's first run copied to one name and restored from another, so `sed`
# wrote empty files over both sources and all ten arms reported SURVIVED
# because pytest said "no tests ran" and the classifier grepped for "failed".
#
# ⚠️ A BATTERY CAN PASS BY REFUSING EVERYTHING **AND** BY ACCEPTING
# EVERYTHING. Both print a clean summary. ARM 0 is the positive control on the
# unmutated tree; an arm that reports BROKEN is a harness failure and is NOT a
# survivor.
#
# ⚠️ DO NOT RUN THIS WHILE A STAGED GATHER IS IN FLIGHT. `staged/__main__.py`
# imports the exporter AFTER the gather, so a run that started eight minutes
# ago will pick up whatever `export.py` says when it reaches EXPORT — measured
# the hard way: a gather finished and then died on a NameError from an edit
# made four minutes into it.
# ⚠️ `test_staged_glyph_families.py` IS IN THIS LIST BECAUSE IT WAS NOT, AND
# TWO GATHER ARMS REPORTED SURVIVED FOR IT. A battery whose test list does
# not reach the file it mutates measures its own scope, not the code.
T="tools/omr/tests/test_staged_fermata_owner.py tools/omr/tests/test_staged_voices.py tools/omr/tests/test_staged_event.py tools/omr/tests/test_staged_export.py tools/omr/tests/test_staged_glyph_families.py"
EXPECT=179

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
if old not in src:
    sys.stderr.write(f"MUTATION DID NOT APPLY: {old!r}\n"); sys.exit(3)
open(path,"w").write(src.replace(old,new,1))
PY
  if [ $? -ne 0 ]; then echo "NOT APPLIED: $3"; git checkout -- "$1"; return; fi
  echo "$(check): $3"
  git checkout -- "$1"
}

O=tools/omr/staged/adjudicators/ownership.py
R=tools/omr/staged/adjudicators/rhythm.py
G=tools/omr/staged/gather.py
E=tools/omr/staged/export.py
echo "ARM 0 positive control: $(check)  (expected SURVIVED)"

# ── the fermata ───────────────────────────────────────────────────────────
arm $G 'elif name.lower().startswith(_FERMATA_PREFIX):||elif name.lower().startswith(_ARTIC_PREFIX + "XX"):' \
       "GATHER: fermatas never typed"
arm $G '_FERMATA_PREFIX = "fermata"||_FERMATA_PREFIX = "artic"' \
       "GATHER: routed to the articulation prefix"
arm $O '_FERMATA_CARRIERS = ("notehead", "rest")||_FERMATA_CARRIERS = ("notehead",)' \
       "a fermata may no longer hang over a REST"
arm $O 'if _span(r)[0] <= mx <= _span(r)[1]), None)||if False), None)' \
       "containment branch deleted — everything falls to nearest"
arm $O 'reason = "contains_the_mark"||reason = "nearest_in_bar"' \
       "the two branches report the SAME reason"
arm $O 'return Ruling.abstain("no_carrier", detector_class=str(mark.value))||pass' \
       "no_carrier refusal deleted"
arm $E 'fermatas_dropped = _place_fermatas(rec, runs)||fermatas_dropped = {}' \
       "EXPORT: placement pass NOT CALLED"
arm $E 'fermata=(ev_fermata if n == 0 else False),||fermata=False,' \
       "EXPORT: kwarg never reaches the renderer"
arm $E 'ev_fermata = any(h.get("fermata") for h in heads)||ev_fermata = bool(heads and heads[0].get("fermata"))' \
       "hoist reads only the chord's FIRST head"
arm $E 'fermata = bool(det.get("fermata"))||fermata = False' \
       "EXPORT: a REST can no longer carry one"
arm $E '    f_written = int(counters.get("fermatas", 0))||    f_written = fermata_marks' \
       "the balance is told what it wants to hear"

# ── stem direction and voices ─────────────────────────────────────────────
arm $R 'answers.add(_legacy_stems._stem_direction(_Shim(sx, sy, sw, sh), group))||answers.add("up")' \
       "every stem points UP"
# ⚠️ ANCHORED ON THE WHOLE EXPRESSION, not on `for h in heads` -- that string
# occurs THREE times in this file and the first is in `adjudicate_tuplet`, so
# the arm mutated a different function and reported SURVIVED.
arm $R 'group = [_Shim(*_xywh_head(h.value)) for h in heads||group = [_Shim(*head_box)] or [_Shim(*_xywh_head(h.value)) for h in heads' "direction from ONE head, not the stems whole group (the double stop)"
arm $R 'if len(answers) != 1:||if False:' \
       "opposing stems no longer abstain — the last one read wins"
arm $R 'return bool(theirs) and mine not in theirs||return False' \
       "the divisi guard never conflicts"
arm $R 'blocked = True||blocked = False' \
       "a blocked head is no longer reported as separated"
arm $R '"rests_in_every_voice": rests if n > 1 else []||"rests_in_every_voice": []' \
       "the duplicated rests are not named"
arm $E 'streams = _voice_split(rec, run, cell_index, events, why)||streams = None' \
       "EXPORT: the voices verdict is never read"
arm $E 'breaks, voice_of)||breaks, {})' \
       "EXPORT: the arc pairing is handed an EMPTY voice map again"
arm $E '               + int(counters["measure_rests_read"]) - duplicated)||               + int(counters["measure_rests_read"]))' \
       "the balance forgets the duplicated rests"

# ⚠️ THE HARNESS CONTROL, DELIBERATELY UNAPPLIABLE. A battery that silently
# skipped every arm would print nothing but the positive control's SURVIVED;
# this proves the "MUTATION DID NOT APPLY" path is reached and reported.
arm $R 'a string that is not in this file||x' "HARNESS CONTROL (must say NOT APPLIED)"

git status --short | grep -E 'ownership|rhythm|gather.py|export.py' && echo "⚠️ TREE DIRTY" || echo "tree clean"
