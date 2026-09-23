"""Does the lexicon repair do what it claims? — a mutation battery.

⚠️ The judge is `(returncode, failing test ids)` from pytest and contains NO
elapsed time: two batteries in this repo were voided on 2026-09-20 by comparing
a summary line ending `" in 0.57s"`, so every arm scored RED for free.

⚠️ Byte snapshot, in-flight sentinel, `PYTHONDONTWRITEBYTECODE=1`, and the
restore verified by hash.
"""
import hashlib, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "tools/omr/instruments.py"
SENTINEL = HERE / ".mutate-in-flight"
TESTS = ["tools/omr/tests/test_instruments.py"]

ARMS = [
    ("the inner-digit rule is removed",
     '    t = _INNER_NOISE_DIGIT.sub("", t)', "    pass"),
    ("the exempt digits are HAND-WRITTEN instead of derived",
     '_FOLDED_DIGITS = frozenset(c for c in "0123456789" if ord(c) in _OCR_FOLD)',
     '_FOLDED_DIGITS = frozenset("017")'),
    ("the rule eats `0` and `1` too, the ordering hazard",
     '"".join(c for c in "0123456789" if c not in _FOLDED_DIGITS) +',
     '"0123456789" +'),
    ("the rule reaches a digit that is NOT between two letters",
     r'    r"(?<=[^\W\d_])[" +', '    r"[" +'),
    ("the ß variant is not derived",
     '''    for alias in tuple(out):
        if "ß" in alias:
            out.append(alias.replace("ß", "b"))''',
     "    pass"),
    ("the ß variant folds the WRONG way, turning every b into ß",
     '            out.append(alias.replace("ß", "b"))',
     '            out.append(alias.replace("b", "ß"))'),
]


def judge():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-q",
                        "--no-header", "-p", "no:cacheprovider"],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    return {"rc": r.returncode,
            "failed": sorted(set(re.findall(r"^FAILED (\S+)", r.stdout, re.M)))}


def main() -> int:
    if SENTINEL.is_file():
        print("REFUSING: a previous battery did not finish.\n" + SENTINEL.read_text())
        return 2
    snap = SRC.read_bytes()
    SENTINEL.write_text(json.dumps({str(SRC): hashlib.md5(snap).hexdigest()}))
    try:
        base = judge()
        print("POSITIVE CONTROL — unmutated:", base)
        if base["rc"] != 0:
            print("FAILED: the tree is not green; nothing below means anything.")
            return 2
        red = survived = bad = 0
        for name, find, repl in ARMS:
            src = snap.decode()
            if src.count(find) != 1:
                print("\nBAD ANCHOR  %s  (%d matches)" % (name, src.count(find)))
                bad += 1
                continue
            SRC.write_text(src.replace(find, repl), encoding="utf8")
            got = judge()
            SRC.write_bytes(snap)
            if got["rc"] != 0:
                red += 1
                print("\nRED       %s\n          -> %s"
                      % (name, ", ".join(got["failed"])[:140]))
            else:
                survived += 1
                print("\nSURVIVED  %s  <== the suite is blind to it" % name)
        SRC.write_bytes(snap)
        ok = hashlib.md5(SRC.read_bytes()).hexdigest() == hashlib.md5(snap).hexdigest()
        print("\n" + "=" * 70)
        print("%d RED, %d survived, %d bad anchors.  restore verified: %s"
              % (red, survived, bad, ok))
        return 0 if (survived == 0 and bad == 0 and ok) else 1
    finally:
        SRC.write_bytes(snap)
        SENTINEL.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
