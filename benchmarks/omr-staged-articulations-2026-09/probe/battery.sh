#!/bin/zsh
# ⚠️ RESTORES FROM git, never from a hand-named backup. The first run of this
# battery copied to /tmp/own.orig.py and restored from
# /tmp/$(basename).orig.py -- a DIFFERENT name -- so sed wrote empty files over
# both sources and every arm reported SURVIVED because pytest said "no tests
# ran" and the grep was for the word "failed".
T="tools/omr/tests/test_staged_articulation_owner.py tools/omr/tests/test_staged_export.py"
EXPECT=109

check() {  # -> RED | SURVIVED | BROKEN
  local out; out=$(python3 -m pytest ${=T} -q 2>&1 | tail -3)
  if   echo "$out" | grep -q "no tests ran";  then echo "BROKEN(no tests)"
  elif echo "$out" | grep -q "error";          then echo "BROKEN(collect error)"
  elif echo "$out" | grep -q "failed";         then echo "RED"
  elif echo "$out" | grep -q "$EXPECT passed"; then echo "SURVIVED"
  else echo "BROKEN(unrecognised: $out)"; fi
}

arm() {  # file, sed-expr, name
  python3 - "$1" "$2" <<'PY'
import subprocess, sys, re
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
E=tools/omr/staged/export.py
echo "ARM 0 positive control: $(check)  (expected SURVIVED)"
arm $O 'if above and my >= hyc:||if above and my <= hyc:'                      "side test INVERTED"
arm $O 'if dx > limit:||if dx > limit and False:'                              "the 0.75 limit removed"
arm $O 'nh_width = widths[len(widths) // 2] or 1.0||nh_width = widths[-1] or 1.0' "MAX width, not median"
arm $O 'if best is None or dx < best[0]:||if best is None:'                     "first head, not the NEAREST"
arm $O 'value=head.subject.to_key()||value=mark.id'                            "returns the MARK, not the head"
arm $O 'detail={"articulation": name,||detail={"articulation": None,'           "kind dropped from the verdict"
arm $O 'return Ruling.abstain("no_side_declared"||return Ruling.abstain("no_notehead"' "no_side_declared collapsed into no_notehead"
arm $E 'artics_dropped = _place_articulations(rec, runs)||artics_dropped = {}'  "placement pass NOT CALLED"
arm $E 'articulations=(head.get("articulations") or None),||articulations=None,' "kwarg never reaches the renderer"
arm $E 'counters["articulations"] += len(head.get("articulations") or ())||pass' "the counter is deleted"
git status --short | grep -E 'ownership|export.py' && echo "⚠️ TREE DIRTY" || echo "tree clean"
