"""HOW WE GET IT: what changed in the code between two overnight commits (Sean 2026-10-29: "what we get and how we get it").

Everything is DERIVED from the trees, nothing hand-listed (CLAUDE.md rule 10 / measuring.md flags):
  * commit count, merge count, and the ROADMAP item numbers named in the commit subjects (the ledger -- the tree outranks it,
    so the item list is "named in a subject", not "verified landed");
  * every OMR_* flag whose DEFAULT differs between the two commits, by the same AST scan the fast tier uses
    (tools/omr/tests/test_flag_default_direction.py::default_on_flags), run on BOTH trees with ONE scanner (the one at HEAD of
    the checkout this runs in) so that a scanner change cannot show up as a flag change. Blind spot, printed: the scan only
    sees flags compared against a literal on/off word set; value flags (OMR_X=0.3) and flags read some other way are caught only
    by the second table, which lists every OMR_* NAME that appears in / vanished from the non-test source;
  * whether each changed flag is read in a GATHER-stage module (lane_report.GATHER_MODULES): a flag that changes GATHER makes
    the two records differ in what was SEEN, not only in what was DECIDED.

python3 process_diff.py BASE_COMMIT TAG_COMMIT
"""
import importlib.util
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def extract(commit: str, dest: pathlib.Path) -> pathlib.Path:
    d = dest / commit[:9]
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run("git archive %s tools | tar -x -C %s" % (commit, d), shell=True, cwd=ROOT, check=True)
    return d


def scanner():
    spec = importlib.util.spec_from_file_location("fdir", ROOT / "tools/omr/tests/test_flag_default_direction.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def defaults(m, tree: pathlib.Path):
    m.ROOT = tree
    out = {}
    for path, line, flag, default, op, members, on in m.default_on_flags():
        out.setdefault(flag, (on, str(path), default))
    return out


FLAG_RE = re.compile(r"\bOMR_[A-Z0-9_]+\b")


def names(tree: pathlib.Path):
    found = {}
    for p in sorted((tree / "tools").rglob("*.py")):
        if "tests" in p.parts:
            continue
        try:
            for n in set(FLAG_RE.findall(p.read_text(errors="ignore"))):
                found.setdefault(n, str(p.relative_to(tree)))
        except OSError:
            pass
    return found


def gather_homes(flag: str, tree: pathlib.Path):
    from tools.omr.staged import lane_report as L
    homes = L.flag_homes(flag, root=tree / "tools" / "omr")
    return homes, L.acts_in_gather(homes)


def main():
    base, tag = sys.argv[1], sys.argv[2]
    rb, rt = git("rev-parse", base).strip(), git("rev-parse", tag).strip()
    log = git("log", "--format=%h%x09%p%x09%s", "%s..%s" % (rb, rt)).splitlines()
    n = len(log)
    merges = sum(1 for l in log if len(l.split("\t")[1].split()) > 1)
    print("== commits")
    print("BASE %s  TAG %s" % (rb, rt))
    print("git log --oneline %s..%s: %d commits (%d merges, %d non-merge)" % (rb[:9], rt[:9], n, merges, n - merges))
    print("changed under tools/omr: " + git("diff", "--shortstat", rb, rt, "--", "tools/omr").strip())
    stat = {}
    for l in git("diff", "--name-only", rb, rt, "--", "tools/omr").splitlines():
        parts = l.split("/")
        k = "tests" if "tests" in parts else ("staged" if "staged" in parts else "/".join(parts[:3]))
        stat[k] = stat.get(k, 0) + 1
    print("files changed by area: " + ", ".join("%s %d" % kv for kv in sorted(stat.items(), key=lambda kv: -kv[1])))
    print()
    print("== ROADMAP items named in commit subjects (oldest first; a subject names it, the tree decides whether it is ON)")
    seen = {}
    pat = re.compile(r"\b(?:ROADMAP\s+)?(\d\.\d{1,3}[a-z]?\d?)\b")
    for l in reversed(log):
        sha, _p, subj = l.split("\t", 2)
        if subj.startswith("Merge"):
            continue
        for item in pat.findall(subj):
            if re.match(r"\d\.\d{2,3}", item):
                seen.setdefault(item, (sha, subj))
    for item, (sha, subj) in sorted(seen.items(), key=lambda kv: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", kv[0])]):
        print("  %-7s %s %s" % (item, sha, subj[:150]))
    print("  (%d items)" % len(seen))
    print()
    print("== 'Land' commits (the ones that flip a default)")
    for l in reversed(log):
        sha, _p, subj = l.split("\t", 2)
        if re.match(r"(Land|land)\b", subj):
            print("  %s %s" % (sha, subj[:170]))
    print()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="flagdiff-"))
    tb, tt = extract(rb, tmp), extract(rt, tmp)
    m = scanner()
    db, dt = defaults(m, tb), defaults(m, tt)
    print("== flag DEFAULTS that differ (same AST scanner on both trees; ON = the default state)")
    print("%-34s %-8s %-8s %-7s %s" % ("flag", "BASE", "TAG", "GATHER?", "read in (TAG tree)"))
    rows = 0
    for f in sorted(set(db) | set(dt)):
        a = db.get(f, (None,))[0]
        b = dt.get(f, (None,))[0]
        if a == b:
            continue
        sa = {None: "absent", True: "ON", False: "OFF"}[a]
        sb = {None: "removed", True: "ON", False: "OFF"}[b]
        homes, g = gather_homes(f, tt if b is not None else tb)
        print("%-34s %-8s %-8s %-7s %s" % (f, sa, sb, "YES" if g else "no", ", ".join(h.replace("staged/", "") for h in homes[:3])))
        rows += 1
    print("(%d flags changed default; %d flags seen by the scan at BASE, %d at TAG)" % (rows, len(db), len(dt)))
    nb, nt = names(tb), names(tt)
    flags_doc = git("show", "%s:docs/flags-2026-09.md" % rt)
    added, gone = sorted(set(nt) - set(nb)), sorted(set(nb) - set(nt))
    print()
    print("== every OMR_* NAME in non-test source: added since BASE (%d) / gone (%d)  [catches value flags the scan misses]" % (len(added), len(gone)))
    for f in added:
        if f not in dt:
            homes, g = gather_homes(f, tt)
            src = [ln.strip() for ln in (tt / nt[f]).read_text(errors="ignore").splitlines() if f in ln and "environ" in ln]
            print("  + %-34s %s%s" % (f, "GATHER " if g else "", nt[f].replace("tools/omr/", "")))
            row = [ln for ln in flags_doc.splitlines() if ln.startswith("| `%s`" % f)]
            cell = row[0].split("|")[2].strip()[:150] if row and len(row[0].split("|")) > 2 else "no row in docs/flags-2026-09.md"
            print("      not seen by the default scan; read as: %s" % (src[0][:110] if src else "(no environ line; named only)"))
            print("      docs/flags-2026-09.md default column: %s" % cell)
    for f in gone:
        print("  - %s (was %s)" % (f, nb[f]))
    print()
    print("blind spot: a flag read through a path the scan cannot parse and already present at BASE is NOT listed even if its default moved.")


if __name__ == "__main__":
    main()
