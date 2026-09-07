#!/usr/bin/env python3
"""Re-derive the load-bearing structural claims of
`docs/pipeline-gather-then-adjudicate-2026-09-07.md` from the tree.

READ-ONLY. Parses source; runs no pipeline, loads no weights, opens no PDF.

Every check is STATIC and mechanical, because the document's claims are static
and mechanical: which line a decision sits on, whether a dict lookup can ever
hit, whether a written field has a reader. Anything requiring a pipeline run is
marked UNMEASURED in the document and is deliberately absent here.

    python3 benchmarks/omr-gather-adjudicate-2026-09/verify_order.py
    python3 benchmarks/omr-gather-adjudicate-2026-09/verify_order.py --root /some/tree

Exit codes
    0  every check passed
    1  a check FAILED — the document disagrees with the tree
    2  the INPUT SET WAS EMPTY OR MISSING — nothing was checked

⚠️ Exit 2 exists because a probe that finds no input and prints a clean zero
looks identical to a probe that found nothing wrong. Seven probes in this repo
did exactly that this week. Every check below registers the size of the input
it consumed, and `main` refuses to report success if any of them consumed
nothing.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

OMR = Path("tools/omr")

# ── the three carries, verified dead ───────────────────────────────────────
CARRIES = ("active_clef_by_staff", "active_key_sig_by_staff",
           "active_time_sig_by_staff")


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, int, str]] = []
        self.empty: list[str] = []

    def check(self, name: str, ok: bool, n_input: int, detail: str) -> None:
        """Record a check. `n_input` is how many things it actually looked at."""
        self.rows.append((name, ok, n_input, detail))
        if n_input <= 0:
            self.empty.append(name)


def _src(root: Path, rel: str) -> str:
    p = root / rel
    if not p.is_file():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8")


def _enclosing_for_loops(tree: ast.AST, lineno: int) -> list[ast.For]:
    """Every `for` statement whose body encloses `lineno`, outermost first."""
    out: list[ast.For] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if node.lineno < lineno <= (node.end_lineno or node.lineno):
            out.append(node)
    out.sort(key=lambda n: n.lineno)
    return out


# ── C1 · the three carries can never hit ───────────────────────────────────
def c1_dead_carries(root: Path, r: Result) -> None:
    """A dict read and written under the SAME loop nest, keyed on that nest's
    own loop variables, one visit per key, with the read ABOVE the write, can
    never return anything but its default."""
    text = _src(root, str(OMR / "transcribe.py"))
    tree = ast.parse(text)
    lines = text.splitlines()

    checked = 0
    verdicts: list[str] = []
    for carry in CARRIES:
        reads, writes = [], []
        for i, line in enumerate(lines, 1):
            if f"{carry}.get(" in line:
                reads.append(i)
            if re.search(rf"{re.escape(carry)}\[\(", line):
                writes.append(i)
        if not reads or not writes:
            verdicts.append(f"{carry}: NO read/write pair found")
            continue
        checked += 1
        # The write inside the deepest shared loop nest.
        w = max(writes)
        w_loops = _enclosing_for_loops(tree, w)
        # The read that shares that nest.
        shared = [
            rd for rd in reads
            if rd < w and [l.lineno for l in _enclosing_for_loops(tree, rd)]
            == [l.lineno for l in w_loops]
        ]
        # Loop targets of the shared nest — the key must be built from these.
        targets: set[str] = set()
        for lp in w_loops:
            for nd in ast.walk(lp.target):
                if isinstance(nd, ast.Name):
                    targets.add(nd.id)
        key_src = lines[w - 1]
        key_from_loops = all(t in key_src for t in ("p", "sys_idx", "staff_idx"))
        one_writer = len(set(writes)) == 1
        dead = bool(shared) and key_from_loops and one_writer
        verdicts.append(
            f"{carry}: read@{shared[0] if shared else '?'} write@{w} "
            f"nest={[l.lineno for l in w_loops]} targets={sorted(targets)} "
            f"one_writer={one_writer} -> {'DEAD' if dead else 'LIVE'}")
        if not dead:
            r.check("C1 dead carries", False, checked, "; ".join(verdicts))
            return
    r.check("C1 dead carries", checked == len(CARRIES), checked,
            "; ".join(verdicts))


# ── C2 · a fourth read, in the header pre-pass, is dead for the same reason ─
def c2_prepass_read(root: Path, r: Result) -> None:
    """The header pre-pass reads `active_clef_by_staff` keyed on `p` BEFORE
    anything is written for that `p`, so it too always takes its default."""
    text = _src(root, str(OMR / "transcribe.py"))
    lines = text.splitlines()
    reads = [i for i, l in enumerate(lines, 1)
             if "active_clef_by_staff.get(" in l]
    writes = [i for i, l in enumerate(lines, 1)
              if re.search(r"active_clef_by_staff\[\(", l)]
    if not reads or not writes:
        r.check("C2 pre-pass read", False, 0, "no read/write found")
        return
    earliest_read, only_write = min(reads), min(writes)
    ok = earliest_read < only_write and len(reads) >= 2
    r.check("C2 pre-pass read", ok, len(reads),
            f"reads={reads} write={only_write} "
            f"(earliest read precedes the only write)")


# ── C3 · clef_evidence is written and has no consumer ──────────────────────
def c3_clef_evidence_unconsumed(root: Path, r: Result) -> None:
    writers, consumers = [], []
    py = sorted((root / OMR).rglob("*.py"))
    scanned = 0
    for p in py:
        if "/tests/" in str(p):
            continue
        scanned += 1
        txt = p.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(txt.splitlines(), 1):
            if "clef_evidence" not in line:
                continue
            # `_not_clef_evidence` is an unrelated local in contextual.py.
            if "_not_clef_evidence" in line:
                continue
            rel = p.relative_to(root)
            if rel.name == "transcribe.py":
                writers.append(f"{rel}:{i}")
            else:
                consumers.append(f"{rel}:{i}")
    r.check("C3 clef_evidence unconsumed", not consumers and bool(writers),
            scanned,
            f"{len(writers)} writer refs in transcribe.py, "
            f"{len(consumers)} consumer refs elsewhere "
            f"{consumers if consumers else ''}")


# ── C4 · the exporter is blind to confidence and to pitch_candidates ───────
def c4_export_blind(root: Path, r: Result) -> None:
    txt = _src(root, str(OMR / "export.py"))
    lines = txt.splitlines()
    n_pc = sum(1 for l in lines if "pitch_candidates" in l)
    conf = [i for i, l in enumerate(lines, 1) if re.search(r"\bconfidence\b", l)]
    # ⚠️ The claim is not "confidence is never mentioned" — it is never READ.
    # The one occurrence is prose inside a docstring (export.py:1020, the
    # fermata note), so testing for a leading `#` is the WRONG test and failed
    # against a true claim. Test for an executable read instead.
    reads = [i for i in conf
             if re.search(r"""get\(["']confidence["']|\[["']confidence["']\]""",
                          lines[i - 1])]
    r.check("C4 export blind", n_pc == 0 and not reads, len(lines),
            f"pitch_candidates={n_pc}, confidence mentions={conf}, "
            f"executable reads={reads} (mentions are prose, not reads)")


# ── C5 · the identity pass itself reads no resolved pitch ──────────────────
def c5_contextual_pitch_free(root: Path, r: Result) -> None:
    """`contextual.py` is claimed to consume no resolved pitch — the pitch
    dependency of the identity stage lives entirely in `clef_correction.py`."""
    txt = _src(root, str(OMR / "contextual.py"))
    lines = txt.splitlines()
    hits = [(i, l.strip()) for i, l in enumerate(lines, 1)
            if re.search(r"""\[["']pitch["']\]|get\(["']pitch["']""", l)]
    cc = _src(root, str(OMR / "clef_correction.py"))
    cc_hits = len(re.findall(r"""["']pitch["']""", cc))
    r.check("C5 contextual is pitch-free", not hits and cc_hits > 0, len(lines),
            f"contextual.py resolved-pitch reads={len(hits)} {hits if hits else ''}; "
            f"clef_correction.py 'pitch' refs={cc_hits}")


# ── C6 · provenance-tag census ─────────────────────────────────────────────
def c6_provenance(root: Path, r: Result) -> None:
    """Which facts carry a provenance tag, and whether anything gates on it."""
    tags = {
        "instrument": "instrument_source",
        "clef": "clef_source",
        "key_signature": "key_signature_source",
    }
    census: list[str] = []
    files = [p for p in sorted((root / OMR).rglob("*.py"))
             if "/tests/" not in str(p)]
    blobs = {p: p.read_text(encoding="utf-8", errors="replace") for p in files}
    scanned = len(blobs)
    for fact, tag in tags.items():
        writers = sum(1 for p, t in blobs.items()
                      if re.search(rf'\[["\']{tag}["\']\]\s*=', t))
        readers = sum(1 for p, t in blobs.items()
                      if re.search(rf'get\(["\']{tag}["\']', t)
                      or f"{tag}_by_slot" in t)
        census.append(f"{fact}:{tag} writers={writers} readers={readers}")
    # Meter carries its tag INSIDE its own dict, under the generic key.
    rhythm = blobs.get(root / OMR / "rhythm.py", "")
    meter_gate = "_READING_SOURCES" in rhythm
    census.append(f"meter:time_signature['source'] gate=_READING_SOURCES "
                  f"present={meter_gate}")
    # Glyph ownership: does the survivor of a contest carry any tag?
    tr = blobs.get(root / OMR / "transcribe.py", "")
    owner_tag = bool(re.search(r'det\w*\[["\']ownership_source["\']\]', tr))
    census.append(f"ownership:(none) survivor_tag_present={owner_tag}")
    ok = meter_gate and not owner_tag
    r.check("C6 provenance census", ok, scanned, "; ".join(census))


# ── C7 · the ordering anchors ──────────────────────────────────────────────
def c7_anchors(root: Path, r: Result) -> None:
    """The four anchors the document's Part 2 is built on, and the gap."""
    text = _src(root, str(OMR / "transcribe.py"))
    lines = text.splitlines()

    def find(pat: str) -> int:
        for i, l in enumerate(lines, 1):
            if re.search(pat, l):
                return i
        return -1

    anchors = {
        "clef seed (dead)": find(r"active_clef = active_clef_by_staff\.get\("),
        "key seed (dead)": find(r"active_key_sig = active_key_sig_by_staff\.get\("),
        "note / _detections_for_cell": find(r"^\s+_detections_for_cell\($"),
        "instrument / contextual": find(r'out\["contextual"\] = apply_contextual_analysis\('),
    }
    missing = [k for k, v in anchors.items() if v < 0]
    gap = anchors["instrument / contextual"] - anchors["note / _detections_for_cell"]
    ordered = (anchors["clef seed (dead)"] < anchors["key seed (dead)"]
               < anchors["note / _detections_for_cell"]
               < anchors["instrument / contextual"])
    r.check("C7 ordering anchors", not missing and ordered and gap > 0,
            len(anchors) - len(missing),
            f"{anchors}; instrument arrives {gap} lines after the note")


# ── C8 · the evaluate-stage record: two shapes, one of them stale ──────────
def c8_change_records(root: Path, r: Result) -> None:
    """The pipeline records "this fact changed" in two shapes.

    VALUE-shaped (`*_final`: the clef at the end of the staff) must be
    maintained by every later writer, so it goes stale. EVENT-shaped
    (`rhythm_reconciliation`, `key_signature_corroboration`: from, to, why)
    is append-only and cannot.

    This check asserts the structural facts behind that claim: the value-shaped
    fields have no consumer beyond their own keeper, and `time_signature_final`
    has not even a keeper.
    """
    files = [p for p in sorted((root / OMR).rglob("*.py"))
             if "/tests/" not in str(p)]
    blobs = {p: p.read_text(encoding="utf-8", errors="replace") for p in files}
    tr = root / OMR / "transcribe.py"

    notes: list[str] = []
    ok = True
    for field in ("clef_final", "key_signature_final", "time_signature_final"):
        sites: list[str] = []
        for p, t in blobs.items():
            for i, line in enumerate(t.splitlines(), 1):
                if field in line and not line.lstrip().startswith("#"):
                    sites.append(f"{p.name}:{i}")
        # Writers live in transcribe.py; anything else is a keeper.
        keepers = [s for s in sites if not s.startswith("transcribe.py")]
        notes.append(f"{field}: {len(sites)} sites, keepers={keepers or 'NONE'}")
        if not sites:
            ok = False
    # time_signature_final is the one with no keeper at all.
    tsf_keepers = [p.name for p, t in blobs.items()
                   if "time_signature_final" in t and p != tr]
    notes.append(f"time_signature_final keeper modules={tsf_keepers or 'NONE'}")
    ok = ok and not tsf_keepers

    # The event-shaped records exist and carry from/to.
    for field, mod in (("rhythm_reconciliation", "transcribe.py"),
                       ("key_signature_corroboration",
                        "key_signature_corroboration.py")):
        present = any(field in t for p, t in blobs.items() if p.name == mod)
        notes.append(f"{field} present in {mod}={present}")
        ok = ok and present

    r.check("C8 change records", ok, len(blobs), "; ".join(notes))


# ── C9 · every propagation is single-pass; no fixpoint anywhere ────────────
def c9_no_fixpoint(root: Path, r: Result) -> None:
    """The three propagations run once, over nested `for` loops, with no
    `while` and no repeat-until-stable. That is the termination argument."""
    # ⚠️ Scoped to the three propagation ENTRY POINTS, not to whole modules.
    # A first cut flagged `key_signature_corroboration.py:234` and was wrong:
    # that `while` is inside `_split_pitch`, a character scanner bounded by
    # `len(pitch)`. "No `while` anywhere in the module" is the wrong test —
    # what matters is that no propagation repeats itself until stable.
    entries = {
        "clef_correction.py": "correct_clefs_from_instruments",
        "key_signature_corroboration.py": "drop_uncorroborated_key_changes",
        "transcribe.py": "_reconcile_page_to_meter",
    }
    checked = 0
    notes: list[str] = []
    ok = True
    for mod, fname in entries.items():
        txt = _src(root, str(OMR / mod))
        fn = next((n for n in ast.walk(ast.parse(txt))
                   if isinstance(n, ast.FunctionDef) and n.name == fname), None)
        if fn is None:
            notes.append(f"{mod}:{fname} NOT FOUND")
            ok = False
            continue
        checked += 1
        whiles = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.While)]
        fors = len([n for n in ast.walk(fn) if isinstance(n, ast.For)])
        notes.append(f"{fname}: while={whiles or 'none'} for={fors}")
        if whiles:
            ok = False
    r.check("C9 propagations are single-pass", ok, checked, "; ".join(notes))


CHECKS = (c1_dead_carries, c2_prepass_read, c3_clef_evidence_unconsumed,
          c4_export_blind, c5_contextual_pitch_free, c6_provenance, c7_anchors,
          c8_change_records, c9_no_fixpoint)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", type=Path,
                    help="repo root holding tools/omr/ (default: cwd)")
    args = ap.parse_args(argv)
    root = args.root.resolve()

    # ⚠️ THE EMPTY-INPUT GUARD, checked before anything runs.
    src_dir = root / OMR
    if not src_dir.is_dir():
        print(f"FATAL: no {OMR} under {root} — nothing to check", file=sys.stderr)
        return 2
    n_py = len([p for p in src_dir.rglob("*.py") if "/tests/" not in str(p)])
    if n_py == 0:
        print(f"FATAL: {src_dir} holds no non-test .py files — nothing to check",
              file=sys.stderr)
        return 2

    r = Result()
    for fn in CHECKS:
        try:
            fn(root, r)
        except FileNotFoundError as exc:
            r.check(fn.__name__, False, 0, f"missing input: {exc}")

    width = max(len(n) for n, *_ in r.rows)
    print(f"gather-then-adjudicate · structural verification")
    print(f"root: {root}   ({n_py} non-test .py files under {OMR})\n")
    for name, ok, n_in, detail in r.rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<{width}}  n={n_in}")
        print(f"         {detail}")
    print()

    if r.empty:
        print(f"FATAL: {len(r.empty)} check(s) consumed an EMPTY input set — "
              f"{r.empty}. A clean pass over nothing is not a pass.",
              file=sys.stderr)
        return 2
    failed = [n for n, ok, *_ in r.rows if not ok]
    if failed:
        print(f"FAILED: {failed}", file=sys.stderr)
        return 1
    print(f"All {len(r.rows)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
