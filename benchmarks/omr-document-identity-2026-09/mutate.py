"""Mutation battery for the identity rung and the one-sided key-signature tier.

⚠️⚠️ TWO SUBJECTS, TWO JUDGES. Arms under `tools/` are judged by the UNIT
SUITE, which must go RED; arms under this directory are judged by the ARM's
own headline, which must MOVE. An arm that leaves its judge unchanged is a
SURVIVOR and a real test gap, never a pass.

⚠️ ONE RED ARM IS NOT A BATTERY, and it needs a POSITIVE CONTROL IN THE SAME
CLASS: the baseline must be green before any arm is read.

⚠️ A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT — WHICH IS NOT THE
SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS NEITHER.
A byte snapshot on disk, an in-flight SENTINEL, a restore VERIFIED by md5, and
a refusal to start on a dirty target without `--force`.

⚠️ `PYTHONDONTWRITEBYTECODE=1` IN EVERY ARM — a stale `.pyc` survives a
mutate/restore cycle (`shutil.copy2` preserves mtime) and made two arms in a
sibling lane import UNMUTATED code and report NOT RED.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
SENTINEL = OUT / ".mutate-in-flight"

TARGETS = {
    "gather": ROOT / "tools/omr/staged/gather.py",
    "header": ROOT / "tools/omr/staged/adjudicators/header.py",
    "store": ROOT / "tools/omr/positional_store.py",
    "arm": HERE / "keysig_domain_arm.py",
    "scanarm": HERE / "scan_is_untouched.py",
}

#: ⚠️ THE DERIVED CHECKS ARE PART OF THE SUITE. `capture`, `reach` and
#: `brakes` are what caught the duplicate `Q.INPUT_DOMAIN` declaration and the
#: reason word that could not be judged statically, so a battery that ran the
#: unit tests alone would call several of these arms survivors.
SUITE = [
    "tools/omr/tests/test_input_domain_gather.py",
    "tools/omr/tests/test_keysig_second_reader.py",
    "tools/omr/tests/test_positional_store.py",
    "tools/omr/tests/test_flag_default_direction.py",
    "tools/omr/tests/test_staged_capture.py",
]
CHECKS = [("reach", "--check"), ("capture", "--check"), ("brakes", "--check")]

REC = OUT / "engraved-p0p2-identity.record.json"
SCAN_REC = OUT / "litolff-p1-identity.record.json"
TRUTH = (ROOT / "benchmarks/omr-staged-engraved-2026-09/out/fixture/"
                "beethoven-sym5-mvt1-m1-24.musicxml")

#: ⚠️⚠️ **THE ARM IS JUDGED ON TWO RECORDS, AND THE SECOND IS WHY.** Judged on
#: the engraved record alone, THREE arms SURVIVED the first run — every one of
#: them a control sitting at its CEILING on a record where the thing works:
#: the reach is non-zero so the DEAD branch is never taken; 54 staves divide
#: 18 parts exactly so the join never refuses. **A control can only be
#: mutation-tested in a state where it FAILS**, which is the lesson
#: `omr-vertical-runs-page-2026-09` paid for and this battery repeated.
#:
#: The SCAN record supplies that state for both: it measures `scanned`, so the
#: arm must exit 2 DEAD; and its 12 staves do not divide 18 parts, so the
#: ordinal join must refuse. The third survivor — an unresolved verdict walk —
#: is answered inside the arm instead, by printing how many superseded pairs
#: it resolved (227 on the engraved record: 215 `duration`, 12 `pitch`).
ARM_RUNS = [
    ["--record", str(REC), "--truth-xml", str(TRUTH)],
    ["--record", str(SCAN_REC), "--truth-xml", str(TRUTH)],
]

#: (target, name, find, replace, what it must break)
ARMS = [
    # ── GATHER: the two rows, and why they are two ──────────────────────────
    ("gather", "the domain is a FIELD of the catalog row, not its own quantity",
     "    log.observe(R.DOCUMENT, Q.INPUT_DOMAIN, cls.verdict,",
     "    if not log.rows(Q.DOCUMENT_IDENTITY, R.DOCUMENT):\n"
     "        return\n"
     "    log.observe(R.DOCUMENT, Q.INPUT_DOMAIN, cls.verdict,",
     "THIS IS THE WHOLE STRUCTURAL CLAIM: a render is in no catalog, so "
     "gating the domain on the catalog row gives it ZERO reach on the one "
     "input the rule is proven on. `test_the_catalog_is_SILENT_where_the_"
     "container_ANSWERS` must fail"),

    ("gather", "an unclassifiable page DEFAULTS to `scanned`",
     "    if cls.verdict not in (SCANNED, ENGRAVED):",
     "    if False:",
     "a fallback must never convert `cannot tell` into a definite answer -- "
     "the blank-page abstention test must fail"),

    ("gather", "the idempotence guard asks only for OBSERVATIONS",
     "    if log.rows(Q.INPUT_DOMAIN, R.DOCUMENT) \\\n"
     "            or log.refusals(Q.INPUT_DOMAIN, R.DOCUMENT):",
     "    if log.rows(Q.INPUT_DOMAIN, R.DOCUMENT):",
     "`rows()` does not return abstentions, so a four-page run on an "
     "unheld PDF files FOUR of them -- the once-per-document test must fail"),

    ("gather", "flag-off ABSTAINS instead of writing nothing",
     "    if not _document_identity_enabled():\n        return\n"
     "    if log.rows(Q.INPUT_DOMAIN, R.DOCUMENT)",
     "    if not _document_identity_enabled():\n"
     "        log.abstain(R.DOCUMENT, Q.INPUT_DOMAIN,\n"
     "                    reader=READERS.CONTAINER, frame=FRAME_PAGE,\n"
     "                    reason=ABSTAIN.OUT_OF_SCOPE)\n        return\n"
     "    if log.rows(Q.INPUT_DOMAIN, R.DOCUMENT)",
     "flag-off must be byte-identical to a tree with no rung, or it perturbs "
     "every A/B in the repo by existing -- the writes-NOTHING test must fail"),

    ("gather", "the flag becomes an ALLOW-list under a default-ON flag",
     '    return os.environ.get(DOCUMENT_IDENTITY_ENV, "1").strip().lower() \\\n'
     '        not in ("0", "", "false", "no", "off")',
     '    return os.environ.get(DOCUMENT_IDENTITY_ENV, "1").strip().lower() \\\n'
     '        in ("1", "true", "yes", "on")',
     "a default-ON flag written as an allow-list is silently switched OFF by "
     "a typo -- both the flag test and the derived direction scan must fail"),

    ("gather", "unnameable pages become an EMPTY list, not None",
     "    return sorted(set(idx)) or None",
     "    return sorted(set(idx))",
     "an empty `page_indices` classifies NOTHING and returns `unknown` -- a "
     "clean believable abstention meaning the wrong thing"),

    # ── the catalog fields Sean asked for ───────────────────────────────────
    ("store", "the year and the plate are dropped again",
     '    return {k: entry.get(k) for k in _EDITION_FIELDS}',
     '    return {k: entry.get(k) for k in _EDITION_FIELDS\n'
     '            if k not in ("publisher_year", "plate")}',
     "Sean asked for the year BY NAME -- the catalog-row test must fail"),

    ("store", "the projection is RESTATED rather than shared",
     '_EDITION_FIELDS = ("path", "work_id", "publisher", "publisher_year", "plate",',
     '_EDITION_FIELDS = ("path", "work_id", "publisher",',
     "the two lookups must not drift apart -- the anti-drift test must fail"),

    # ── ADJUDICATE: the one-sided tier ──────────────────────────────────────
    ("header", "the precedence is flipped GLOBALLY, not one-sided",
     "    if _proved_engraved(ev):",
     "    if True:",
     "THE REFUSAL WAS PRICED ON SCANS and that side is not measured -- the "
     "scan, no-row and flag-off fall-through tests must all fail"),

    ("header", "a SCAN is treated as engraved too",
     '        if str(row.value) == "engraved":',
     '        if str(row.value) in ("engraved", "scanned"):',
     "one-sided means one side -- the scan test must fail"),

    ("header", "the DOCUMENT row is read at the default EXACT scope",
     "    for row in ev.rows(Q.INPUT_DOMAIN, scope=Scope.SELF_AND_ANCESTORS):",
     "    for row in ev.rows(Q.INPUT_DOMAIN):",
     "`Q.INPUT_DOMAIN` is filed on the DOCUMENT and this decision is "
     "Kind.STAFF, so a bare read returns nothing on every page FOREVER and "
     "fails silent -- the engraved test and the scope test must fail"),

    ("header", "the consumer flag is ignored",
     "    if not _engraved_keysig_enabled():\n        return False",
     "    if False:\n        return False",
     "a default-OFF mechanism must be off by default -- the flag-off test "
     "must fail"),

    ("header", "the engraved tier reuses the SHIPPED reason word",
     '            return Ruling(value=fifths, reason="fitted_by_template_engraved",',
     '            return Ruling(value=fifths, reason="fitted_by_template",',
     "a separate word is what makes the new tier's reach countable in the "
     "record; folding them hides every firing"),

    ("header", "the template's fit for ANOTHER clef is taken",
     "        if str(row.value) != str(clef.value):\n"
     "            continue\n"
     "        fifths = row.detail.get(\"fifths\")\n"
     "        if fifths is None:\n"
     "            continue\n"
     "        return row, int(fifths)",
     "        fifths = row.detail.get(\"fifths\")\n"
     "        if fifths is None:\n"
     "            continue\n"
     "        return row, int(fifths)",
     "a bass-clef fit must not name a treble staff's key -- the wrong-clef "
     "test must fail"),

    # ── THE INSTRUMENT ──────────────────────────────────────────────────────
    ("arm", "DEAD at zero reach becomes a clean exit",
     '        print("\\n⚠️ DEAD ARM: this record carries no Q.INPUT_DOMAIN row',
     '        return 0\n        print("\\n⚠️ DEAD ARM: this record carries no Q.INPUT_DOMAIN row',
     "a dead instrument must not read as a clean result"),

    ("arm", "the outcome is compared as `str(enum)` again",
     "            out[q][key] = (live.outcome.value, live.value, live.reason) \\",
     "            out[q][key] = (str(live.outcome), live.value, live.reason) \\",
     "THE BUG THIS ARM ALREADY HAD: `str(Outcome.DECIDED)` is "
     "'Outcome.DECIDED', so the accuracy table read 0 right / 0 wrong on "
     "BOTH arms -- the scorer's own positive control must fire"),

    ("arm", "the verdict walk takes SUPERSEDED rows",
     "            live = log.verdict(q, sub)",
     "            live = next((v for v in log.all_verdicts()\n"
     "                         if v.quantity == q\n"
     "                         and v.subject.to_key() == key), None)",
     "EVALUATE revises in place, so an unresolved walk reports quantities as "
     "having moved when only the write count moved -- the CONTROL must move"),

    ("scanarm", "the VACUITY control is dropped",
     "    return 0 if (same and moved) else 1",
     "    return 0 if same else 1",
     "a run where the scan is untouched AND the control is vacuous is a "
     "PASS-shaped nothing -- BOTH conditions are the instrument"),

    ("scanarm", "the forged control is not forged",
     '            o["value"] = "engraved"',
     '            o["value"] = o["value"]',
     "the control must actually change the domain, or `CONTROL DIFFERS` is "
     "reporting that a file equals itself"),

    ("arm", "the ordinal join is forced where it does not divide",
     "        if len(staves) % len(truth) != 0:",
     "        if False:",
     "pairing by position where the counts disagree reports the mismatch as "
     "accuracy"),
]


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()[:12]


def _env() -> dict:
    return dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def run_suite() -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *SUITE],
                       cwd=str(ROOT), env=_env(), capture_output=True,
                       text=True)
    tail = [s for s in r.stdout.splitlines()
            if "passed" in s or "failed" in s or "error" in s]
    rc = r.returncode
    detail = [tail[-1] if tail else ""]
    for mod, flag in CHECKS:
        c = subprocess.run([sys.executable, "-m",
                            f"tools.omr.staged.{mod}", flag],
                           cwd=str(ROOT), env=_env(), capture_output=True,
                           text=True)
        rc |= (c.returncode << 4)
        detail.append(f"{mod}={c.returncode}")
    return rc, "  ".join(detail)


def _one_arm(args: list[str]) -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-u", str(TARGETS["arm"]), *args],
                       cwd=str(ROOT), env=_env(), capture_output=True,
                       text=True)
    out = r.stdout + r.stderr
    keep = [s.strip() for s in out.splitlines()
            if any(t in s for t in ("Q.INPUT_DOMAIN", "MOVED", "DEAD",
                                    "right", "reasons", "CHANGED", "RESOLVED",
                                    "SCORED NOTHING", "REFUSED"))]
    return r.returncode, "\n".join(keep)


def _scan_arm() -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-u", str(TARGETS["scanarm"]),
                        "--record", str(SCAN_REC)],
                       cwd=str(ROOT), env=_env(), capture_output=True,
                       text=True)
    out = r.stdout + r.stderr
    keep = [s.strip() for s in out.splitlines()
            if any(t in s for t in ("REACH", "OFF == ON", "CONTROL",
                                    "control changed", "DEAD"))]
    return r.returncode, "\n".join(keep)


def run_arm() -> tuple[int, str]:
    """⚠️ THE HEADLINE IS THREE RUNS. See `ARM_RUNS`: the engraved record alone
    leaves three of this arm's own controls unable to fail, and the scan
    fall-through needs its own instrument with its own vacuity control."""
    rcs, outs = [], []
    for args in ARM_RUNS:
        rc, out = _one_arm(args)
        rcs.append(rc)
        outs.append(out)
    rc, out = _scan_arm()
    rcs.append(rc)
    outs.append(out)
    return (sum(rcs), "\n--\n".join(outs))


def main() -> int:
    force = "--force" in sys.argv
    if SENTINEL.exists():
        print("REFUSED: an in-flight sentinel exists -- a previous battery "
              "was interrupted and the tree may still carry a mutation.")
        print(SENTINEL.read_text())
        return 3
    for r in (REC, SCAN_REC):
        if not r.is_file():
            print(f"REFUSED: {r} is missing. The arm half of this battery "
                  f"measures nothing without it; see run_all.sh.")
            return 3
    rel = [str(p.relative_to(ROOT)) for p in TARGETS.values()]
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *rel],
                           cwd=str(ROOT), capture_output=True,
                           text=True).stdout.strip()
    if dirty and not force:
        print(f"REFUSED: a target is dirty:\n{dirty}\nCommit, or --force.")
        return 3

    OUT.mkdir(parents=True, exist_ok=True)
    snap = {k: v.read_bytes() for k, v in TARGETS.items()}
    SENTINEL.write_text("\n".join(
        f"{k}={TARGETS[k]} md5={md5b(v)}" for k, v in snap.items()) + "\n")

    print("=" * 78)
    print("BASELINE — the positive control. Every arm below is free if this "
          "is not green.")
    print("=" * 78)
    s_rc, s_out = run_suite()
    print(f"  SUITE+CHECKS exit {s_rc}: {s_out}")
    a_rc, a_out = run_arm()
    print(f"  ARM          exit {a_rc}")
    print("  " + a_out.replace("\n", "\n  "))
    # ⚠️ THE ARM'S BASELINE IS NOT "exit 0". It is the EXPECTED PROFILE over
    # the two runs — engraved 0, scan 2 (DEAD, because that document measures
    # `scanned` and the one-sided tier is a no-op there BY DESIGN) — summed to
    # 2. An arm whose scan run stops declaring itself dead moves this.
    if s_rc != 0 or a_rc != 2:
        print("\n⚠️ BASELINE IS NOT GREEN. The battery measures nothing.")
        for k, v in snap.items():
            TARGETS[k].write_bytes(v)
        SENTINEL.unlink(missing_ok=True)
        return 4

    red, survived, bad = [], [], []
    for target, name, find, repl, why in ARMS:
        src = snap[target].decode("utf-8")
        if src.count(find) != 1:
            bad.append((target, name, f"{src.count(find)} occurrences"))
            print(f"\n{'-' * 78}\nARM [{target}]: {name}\n"
                  f"  ⚠️ BAD ANCHOR ({src.count(find)} occurrences) — "
                  f"REPORTED AS AN ERROR, never as a pass")
            continue
        TARGETS[target].write_text(src.replace(find, repl), encoding="utf-8")
        if target == "arm":
            rc, out = run_arm()
            moved = (rc != a_rc) or (out != a_out)
            judge = "ARM headline"
        else:
            rc, out = run_suite()
            moved = (rc != s_rc)
            judge = "suite+checks"
        TARGETS[target].write_bytes(snap[target])
        (red if moved else survived).append((target, name, why))
        print(f"\n{'-' * 78}\nARM [{target}]: {name}")
        print(f"  judge: {judge}   expected: {why}")
        print(f"  exit {rc}  -> {'RED' if moved else 'SURVIVED'}")
        if not moved:
            print("  ⚠️ SURVIVOR — a real test gap, not a pass.")

    ok = True
    for k, v in snap.items():
        TARGETS[k].write_bytes(v)
        if md5b(TARGETS[k].read_bytes()) != md5b(v):
            print(f"\n⚠️⚠️ RESTORE FAILED for {k}")
            ok = False
    if ok:
        SENTINEL.unlink(missing_ok=True)

    print("\n" + "=" * 78)
    print(f"RED {len(red)}   SURVIVED {len(survived)}   BAD ANCHORS {len(bad)}")
    print(f"restore VERIFIED by md5: {ok}")
    for t, n, w in survived:
        print(f"  SURVIVOR [{t}] {n}\n     expected: {w}")
    for t, n, w in bad:
        print(f"  BAD ANCHOR [{t}] {n} ({w})")
    return 0 if (ok and not survived and not bad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
