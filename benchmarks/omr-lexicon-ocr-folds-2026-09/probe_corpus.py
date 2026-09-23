"""EVERY LABEL, BEFORE AND AFTER — the validation this lexicon's own history demands.

Two repairs, both admitted on the RARITY argument `_OCR_FOLD` states:

  1. a DIGIT between two letters is noise (`Flo6ten` -> `Floten`), in
     `normalize_label`, with `0` and `1` exempt because `_OCR_FOLD` already
     claims them as letter confusions;
  2. an alias carrying `ß` also gets its `b`-spelled form (`kontrabaß` ->
     `kontrabab`), derived in `aliases_of`.

⚠️⚠️ THE FALSE-POSITIVE TEST IS THE POINT, NOT THE RECOVERY. This file's
history is that a widening looked free and was not: `Vier Flöten` resolved to
**Piano** (`vier` is a tail of `klavier`) and `Soprano Saxophone` to **Alto**
(`soprano` is a tail of `mezzosoprano`), and both were found by crossing the
lexicon against a corpus it was never meant to match. So every string in BOTH
committed corpora is resolved on the OLD lexicon and the NEW one and every
difference is printed — a recovery and a regression look identical until you
name which is which.

  labels.json      1,422 real margin labels, what the readers actually emitted
  part-names.json  the reference-encoding part names, which the margin lexicon
                   is NOT meant to match and which therefore price the
                   widening's false-positive surface
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPORA = {
    "labels": ROOT / "benchmarks/omr-lexicon-2026-09/labels.json",
    "part-names": ROOT / "benchmarks/omr-lexicon-2026-09/part-names.json",
}

WORKER = r'''
import json, sys
sys.path.insert(0, %r)
from tools.omr.instruments import lookup
out = {}
for t in json.load(open(%r)):
    if isinstance(t, dict):
        t = t.get("text") or t.get("name") or ""
    t = str(t)
    if not t or t in out:
        continue
    h = lookup(t)
    out[t] = None if h is None else [h.instrument.name, h.instrument.family,
                                     h.alias, round(h.coverage, 3)]
json.dump(out, open(%r, "w"))
'''


def resolve(corpus: Path, tag: str, ref: str | None) -> dict:
    """Resolve every string in `corpus` — at `ref` (a git rev) or in the tree."""
    tmp = HERE / "out" / f".{tag}.json"
    worker = HERE / "out" / f".worker-{tag}.py"
    if ref is None:
        root = str(ROOT)
    else:
        root = str(HERE / "out" / f".tree-{tag}")
        Path(root).mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "worktree", "add", "-f", "--detach", root, ref],
                       cwd=ROOT, check=True, capture_output=True)
    worker.write_text(WORKER % (root, str(corpus), str(tmp)))
    subprocess.run([sys.executable, str(worker)], check=True)
    got = json.loads(tmp.read_text())
    tmp.unlink()
    worker.unlink()
    if ref is not None:
        subprocess.run(["git", "worktree", "remove", "--force", root],
                       cwd=ROOT, check=True, capture_output=True)
    return got


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    report = {"base": base, "corpora": {}}
    total_new, total_lost, total_changed = 0, 0, 0
    for name, path in CORPORA.items():
        if not path.is_file():
            print("MISSING corpus %s" % path, file=sys.stderr)
            return 2
        old = resolve(path, "old-" + name, base)
        new = resolve(path, "new-" + name, None)
        assert set(old) == set(new), "the two runs saw different strings"
        gained = {t: new[t] for t in old if old[t] is None and new[t] is not None}
        lost = {t: old[t] for t in old if old[t] is not None and new[t] is None}
        changed = {t: [old[t], new[t]] for t in old
                   if old[t] is not None and new[t] is not None
                   and old[t][:2] != new[t][:2]}
        total_new += len(gained)
        total_lost += len(lost)
        total_changed += len(changed)
        print("=" * 74)
        print("%s — %d distinct strings" % (name, len(old)))
        print("=" * 74)
        print("  resolved before %d   after %d" %
              (sum(1 for v in old.values() if v), sum(1 for v in new.values() if v)))
        print("  GAINED (nothing -> an instrument)   %d" % len(gained))
        for t, v in sorted(gained.items()):
            print("     %-34r -> %s (%s)" % (t, v[0], v[1]))
        print("  LOST (an instrument -> nothing)     %d" % len(lost))
        for t, v in sorted(lost.items()):
            print("     %-34r was %s (%s)" % (t, v[0], v[1]))
        print("  CHANGED (one instrument -> another) %d" % len(changed))
        for t, (o, n) in sorted(changed.items()):
            flag = "  <== CROSS-FAMILY" if o[1] != n[1] else ""
            print("     %-34r %s (%s) -> %s (%s)%s"
                  % (t, o[0], o[1], n[0], n[1], flag))
        report["corpora"][name] = {"strings": len(old),
                                   "resolved_before": sum(1 for v in old.values() if v),
                                   "resolved_after": sum(1 for v in new.values() if v),
                                   "gained": gained, "lost": lost,
                                   "changed": changed}
        print()
    print("TOTAL over both corpora: gained %d, LOST %d, CHANGED %d"
          % (total_new, total_lost, total_changed))
    (HERE / "out" / "corpus-diff.json").write_text(json.dumps(report, indent=1))
    print("wrote", HERE / "out" / "corpus-diff.json")
    return 0 if (total_lost == 0 and total_changed == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
