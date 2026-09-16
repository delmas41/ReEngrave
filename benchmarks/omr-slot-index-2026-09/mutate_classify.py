"""Mutation battery for `slot_arm.classify`.

Each arm must make `--self-check` FAIL. ⚠️ Arm 0 is the POSITIVE CONTROL: the
unmutated tree must PASS, or every "red" below is red for the wrong reason.
⚠️ Every anchor is asserted UNIQUE before it is applied -- an anchor occurring
twice has already cost this repo two batteries that mutated a different
function and reported green.
"""
import pathlib
import subprocess
import sys

F = pathlib.Path(__file__).resolve().parent / "slot_arm.py"
ORIG = F.read_text()

MEMBERSHIP = 'if slot_name in printed.split(" e "):'
EQUALITY = 'if printed == slot_name:\n        return "ok"'

ARMS = [
    ("1  restore the startswith prefix clause", MEMBERSHIP,
     'if printed.startswith(slot_name) or slot_name.startswith(printed):'),
    ('2  restore the bare " e " clause        ', MEMBERSHIP,
     'if " e " in printed:'),
    ("3  everything is a graft                ", MEMBERSHIP, "if False:"),
    ("4  everything is condensation           ", MEMBERSHIP, "if True:"),
    ("5  split on a bare \"e\" not \" e \"      ", MEMBERSHIP,
     'if slot_name in printed.split("e"):'),
    ("6  equality no longer short-circuits    ", EQUALITY,
     'if False:\n        return "ok"'),
]


def check():
    return subprocess.run([sys.executable, str(F), "--self-check"],
                          capture_output=True).returncode


def main():
    fails = []
    rc = check()
    print("arm 0  POSITIVE CONTROL (no mutation)    exit=%d   want 0" % rc)
    if rc != 0:
        fails.append("the positive control is not green")
    for name, old, new in ARMS:
        n = ORIG.count(old)
        if n != 1:
            print("arm  %s  BAD ANCHOR (occurs %d times)" % (name, n))
            fails.append(name + ": bad anchor")
            continue
        F.write_text(ORIG.replace(old, new))
        try:
            rc = check()
        finally:
            F.write_text(ORIG)
        print("arm  %s  exit=%d   want non-zero%s"
              % (name, rc, "" if rc else "   <-- SURVIVED"))
        if rc == 0:
            fails.append(name + ": survived")
    assert F.read_text() == ORIG, "the battery did not restore the file"
    print("\nrestored: identical to pre-battery")
    print("BATTERY %s" % ("all arms red" if not fails else "PROBLEMS: %s" % fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
