"""Part 2 bit-identity control: on every `Evidence.correlated_groups` call of a real Brahms ADJUDICATE, compute the answer with
the OLD algorithm (full intersection set, no component skip; copied from the 10-07 tree) and assert it equals the new one;
also check `quantities_in_closure` against the un-memoised formula and the compiled alias pattern against `re.search`.
A control that can fail: `--break` flips one pair in the new answer and the script must exit non-zero.

  python3 brahms_1007_corr_identity.py <cache.json> <pages csv> [--break]
"""
from __future__ import annotations
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import mark_identity_rebuild as MR
from tools.omr.staged import adjudicate as A
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged.record import Observation


def old_one_signal(log, a, b):
    if isinstance(a, Observation) and isinstance(b, Observation):
        return (a.reader, a.frame, a.quantity) == (b.reader, b.frame, b.quantity)
    shared = log.closure(a.id) & log.closure(b.id)
    shared = {s for s in shared if s not in (a.id, b.id)}
    return bool(shared)


def old_groups(self):
    rows = [self.log.row(i) for i in self._seen]
    rows = list({r.id: r for r in rows if r is not None}.values())
    parent = {r.id: r.id for r in rows}

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx
    buckets, others = {}, []
    for r in rows:
        if isinstance(r, Observation):
            buckets.setdefault((r.reader, r.frame, r.quantity), []).append(r)
        else:
            others.append(r)
    for b in buckets.values():
        for r in b[1:]:
            union(b[0].id, r.id)
    derived = [r for b in buckets.values() for r in b if r.basis]
    for i, a in enumerate(others):
        for b in others[i + 1:]:
            if old_one_signal(self.log, a, b):
                union(a.id, b.id)
        for o in derived:
            if old_one_signal(self.log, a, o):
                union(a.id, o.id)
    comp = {}
    for r in rows:
        comp.setdefault(find(r.id), []).append(r.id)
    return tuple(frozenset(v) for v in comp.values() if len(v) > 1)


def main(cache, pages, brk):
    res = json.loads(Path(cache).read_text())
    pg = set(int(p) for p in pages.split(","))
    log = MR.rebuild(res["record"], pg)
    new = A.Evidence.correlated_groups
    st = dict(calls=0, differ=0, qic=0, qic_bad=0)

    def checked(self):
        got = new(self)
        want = old_groups(self)
        if brk and st["calls"] == 100 and got:
            got = got[1:]
        st["calls"] += 1
        if got != want:                      # same tuple, same ORDER, same frozensets
            st["differ"] += 1
        for i in list(self._seen)[:5]:
            r = self.log.row(i)
            if r is not None:
                st["qic"] += 1
                if self.log.quantities_in_closure(i) != frozenset(
                        x.quantity for x in (self.log.row(j) for j in self.log.closure(i)) if x is not None):
                    st["qic_bad"] += 1
        return got
    A.Evidence.correlated_groups = checked
    A.run(log)
    print(st)
    from tools.omr import instruments as I
    import re
    bad = 0
    for cand in ("vc.", "violoncello e basso", "cor. in f", "fl. 1.2.", "tp. in c", "timpani in g.d", "contrabassi"):
        for folded in (False, True):
            old = None
            for alias, inst in I._ALIAS_INDEX:
                probe = I._fold_ocr(alias) if folded else alias
                if re.search(rf"(?<![a-z]){re.escape(probe)}(?![a-z])", cand):
                    old = (alias, inst); break
            bad += old != I._search(cand, folded)
    print("alias search mismatches:", bad)
    return 1 if st["differ"] or st["qic_bad"] or bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], "--break" in sys.argv))
