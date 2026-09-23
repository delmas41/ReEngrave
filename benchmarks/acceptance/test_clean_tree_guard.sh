#!/bin/bash
# Roadmap 1.2 (coordinator addendum): `gather_movement.sh`'s clean-tree guard
# counted ANY untracked file, so a first document's own
# `benchmarks/acceptance/out/<doc>/*.record.json` etc. made a SECOND
# document's run refuse to start, quoting the first run's output as the
# reason the tree was "dirty".
#
# This exercises the guard's actual `git status --porcelain | grep -v ...`
# pipeline against a REAL git repo (not a restatement of the pattern), so a
# future edit to the two `grep -v` lines in gather_movement.sh is checked
# against the same fixture rather than against itself.
#
#   bash benchmarks/acceptance/test_clean_tree_guard.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="${REPO_ROOT}/benchmarks/acceptance/gather_movement.sh"

fail=0
pass=0

check_guard_lines_present() {
  if ! grep -q "grep -v '\^?? benchmarks/acceptance/out/'" "$SCRIPT"; then
    echo "FAIL: gather_movement.sh no longer exempts benchmarks/acceptance/out/ untracked files" >&2
    fail=$((fail + 1))
    return
  fi
  if ! grep -q "grep -v '\^?? library/'" "$SCRIPT"; then
    echo "FAIL: gather_movement.sh no longer exempts library/ untracked files" >&2
    fail=$((fail + 1))
    return
  fi
  echo "PASS: gather_movement.sh's guard still exempts both paths"
  pass=$((pass + 1))
}

with_temp_repo() {
  local tmp rc
  tmp="$(mktemp -d)"
  (
    cd "$tmp"
    git init -q
    git config user.email test@example.com
    git config user.name test
    mkdir -p src benchmarks/acceptance/out/docA library
    echo "one" > src/tracked.py
    # ⚠️ MIRRORS THE REAL REPO SHAPE, DELIBERATELY: `benchmarks/acceptance/out/`
    # is not itself gitignored and already holds tracked files for the three
    # acceptance documents (`git ls-files` names 13 of them), so a NEW
    # untracked file inside one of its subdirectories is reported per-file
    # by `git status --porcelain` (`?? benchmarks/acceptance/out/docA/x`).
    # A fixture with NOTHING tracked anywhere near `benchmarks/` instead
    # collapses to a single `?? benchmarks/` line -- caught by this test's
    # own first run, which failed for exactly that reason before this
    # placeholder was added.
    echo "placeholder" > benchmarks/acceptance/out/docA/.keep
    echo "placeholder" > library/.keep
    git add src/tracked.py benchmarks/acceptance/out/docA/.keep library/.keep
    git commit -q -m init
    "$@" "$tmp"
  )
  # ⚠️ CAPTURED BEFORE `rm -rf`, which always exits 0 and would otherwise
  # mask every failure the subshell reported -- caught by running this test
  # once with a deliberately-inverted assertion before writing it this way.
  rc=$?
  rm -rf "$tmp"
  return "$rc"
}

# 1. A clean tree with only the two exempt directories dirty -> guard PASSES
if with_temp_repo bash -c '
  cd "$1"
  echo "record" > benchmarks/acceptance/out/docA/beethoven5-p1-p4.record.json
  echo "log line" > benchmarks/acceptance/out/docA/beethoven5-p1-p4.log
  echo "pdf bytes" > library/some-edition.pdf
  out="$(git status --porcelain | grep -v "^?? benchmarks/acceptance/out/" | grep -v "^?? library/" || true)"
  if [ -n "$out" ]; then
    echo "FAIL: exempt-only tree reported as dirty: $out" >&2
    exit 1
  fi
  echo "PASS: a second document sees a tree dirtied only by the first document (and library/) as clean"
' _; then
  pass=$((pass + 1))
else
  fail=$((fail + 1))
fi

# 2. A MODIFIED tracked file -> guard still REFUSES
if with_temp_repo bash -c '
  cd "$1"
  echo "two" >> src/tracked.py
  echo "record" > benchmarks/acceptance/out/docA/x.record.json
  out="$(git status --porcelain | grep -v "^?? benchmarks/acceptance/out/" | grep -v "^?? library/" || true)"
  if [ -z "$out" ]; then
    echo "FAIL: a MODIFIED tracked file was exempted -- the guard has gone silent" >&2
    exit 1
  fi
  echo "PASS: a modified tracked file still trips the guard"
' _; then
  pass=$((pass + 1))
else
  fail=$((fail + 1))
fi

# 3. An untracked file OUTSIDE both exempt directories -> guard still REFUSES
if with_temp_repo bash -c '
  cd "$1"
  echo "oops" > src/stray_untracked.py
  echo "record" > benchmarks/acceptance/out/docA/x.record.json
  out="$(git status --porcelain | grep -v "^?? benchmarks/acceptance/out/" | grep -v "^?? library/" || true)"
  if [ -z "$out" ]; then
    echo "FAIL: an untracked file outside the exempt directories was silently exempted" >&2
    exit 1
  fi
  echo "PASS: an untracked file outside the exempt directories still trips the guard"
' _; then
  pass=$((pass + 1))
else
  fail=$((fail + 1))
fi

check_guard_lines_present

echo
echo "clean-tree guard test: ${pass} passed, ${fail} failed"
[ "$fail" -eq 0 ]
