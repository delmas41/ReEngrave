"""The acceptance harness — plan Sec.4 / Sec.6, ROADMAP.md Phase 1 item 1.3.

    python3 -m tools.omr.acceptance                    # all three documents
    python3 -m tools.omr.acceptance --doc beethoven5-litolff
    python3 -m tools.omr.acceptance --no-write          # dry run, no current.json
    python3 -m tools.omr.acceptance --force             # write on a dirty tree

One command that scores the three acceptance documents named in
`benchmarks/acceptance/manifest.json` (CLAUDE.md Sec.6a, docs/DECISIONS.md
2026-09-22) and writes `benchmarks/acceptance/current.json`. It is the
instrument every later phase reports against, so it must be honest about
what it could not do rather than print a clean zero — a `skipped` or
`absent` block is never conflated with a zero-valued one anywhere in this
module or its output.

WHAT IT DOES, per document (Sec.6a):
    1. verify the record's md5 against a receipt in the manifest (recorded
       on first run; a mismatch REFUSES the whole run — a shared record
       under `library/_shared-records/` is machine-local and gitignored,
       so this receipt is the only way a later run can tell it changed);
    2. export MusicXML with `staged/export.py` (the exact call
       `staged/__main__.py` makes — no export logic is re-implemented here);
    3. compute the machine PROXIES from the coverage report the export
       returns (Sec.6a: "controls, never objectives");
    4. for the engraved document only: reading F1 against the exact page
       truth, and OMR-NED against the encoding;
    5. build a side-by-side for the fixed count page (a full print-page
       crop plus a best-effort Verovio render of the corresponding bars;
       falls back to the print crop alone if the bar-range render fails);
    6. for the engraved document only: `musicxml2ly` + `lilypond`, if both
       binaries are on PATH, and the bar-check failure count.

Each step is wrapped in its own time budget (`--step-timeout`, default 900s
= 15 minutes) and its own `try/except`; a step that times out or raises is
recorded as `skipped`/`error` with a reason, and every OTHER step and
document still runs. `absent`/`skipped` are DISTINCT from a numeric 0
everywhere in the JSON this module writes — see `_SKIPPED`/`_ABSENT`.

LEGACY vs STAGED (CLAUDE.md Sec.3, rule 2): every mechanism this module
calls is STAGED (`staged/export.py`) except `tools/omr/preprocessing.py`
(shared, used here only for a plain page raster) and the print-side
Verovio/fitz calls, which belong to neither pipeline. Nothing here reads a
legacy-only flag or calls `transcribe.py`.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import hashlib
import importlib.util
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr.staged import export as X  # noqa: E402
from tools.omr import omr_ned as ON  # noqa: E402

MANIFEST_PATH = REPO / "benchmarks" / "acceptance" / "manifest.json"
CURRENT_PATH = REPO / "benchmarks" / "acceptance" / "current.json"
OUT_DIR = REPO / "benchmarks" / "acceptance" / "out"

DEFAULT_STEP_TIMEOUT_S = 900.0  # 15 minutes, per the brief's own cap

#: Sentinels distinct from a real value, so a JSON reader (and this module's
#: own tests) can never read "the tool did not run this" as "the tool ran
#: this and got zero". `absent` = the input does not exist on this machine;
#: `skipped` = the input exists but this run declined or failed to use it.
_ABSENT = "absent"
_SKIPPED = "skipped"

_STAGED_READING_MODULE = (REPO / "benchmarks" / "omr-staged-engraved-2026-09"
                          / "staged_reading.py")
_BAR_FILL_MODULE = (REPO / "benchmarks" / "omr-rest-sizing-2026-09" / "probe"
                    / "bar_fill.py")
_SIDE_BY_SIDE_MODULE = (REPO / "benchmarks" / "omr-cleanup-count-2026-09"
                        / "build_sidebyside.py")

_BARCHECK_RE = re.compile(r"barcheck failed", re.I)


class TimeBudgetExceeded(RuntimeError):
    """A step ran longer than its allotted time budget."""


class AcceptanceError(RuntimeError):
    """A whole-run refusal (dirty tree, bad manifest, receipt mismatch)."""


# ─────────────────────────────────────────────────────────────────────────
# small utilities
# ─────────────────────────────────────────────────────────────────────────

def _import_from_path(name: str, path: Path):
    """Import a standalone benchmark script as a module, by file path.

    None of the three modules this reaches (`staged_reading.py`,
    `bar_fill.py`, `build_sidebyside.py`) live under a package with an
    `__init__.py` — they are one-off benchmark scripts, deliberately, per
    CLAUDE.md's rule that mutation batteries and one-off probes are not
    promoted into `tools/`. Reusing their PURE functions (never their CLI
    `main()`) is cheaper and safer than re-deriving the same arithmetic a
    second time, which this repo's own chronicle names as a recurring
    failure ("`_pair_arcs` has no dedupe", the hairpin export built twice).
    """
    if not path.is_file():
        raise FileNotFoundError(str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _git(args: List[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=str(REPO),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@contextlib.contextmanager
def _os_level_stdout_to_stderr():
    """Redirect file descriptor 1 to fd 2 for the duration of the block.

    `verovio`'s toolkit is a C++ library and writes its own warnings
    (`[Warning] ...`) straight to the process's real stdout fd, which a
    Python-level `contextlib.redirect_stdout` cannot see. Every OTHER
    printer in this module already writes progress to stderr and data to
    stdout ONLY via `print(json.dumps(...))` at the very end of `main()`,
    so redirecting fd 1 -> fd 2 for the whole run except that one final
    print keeps `--json` output valid JSON without losing the warnings.
    """
    stdout_fd = sys.stdout.fileno()
    saved = os.dup(stdout_fd)
    try:
        sys.stdout.flush()
        os.dup2(sys.stderr.fileno(), stdout_fd)
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, stdout_fd)
        os.close(saved)


@contextlib.contextmanager
def _time_budget(seconds: float, label: str):
    """Raise `TimeBudgetExceeded` if the `with` block runs past `seconds`.

    SIGALRM-based (Unix only, which is what this project runs on). A
    per-STEP budget, not a per-document one, because one slow step (a huge
    ink-laden record's export, say) must not swallow the budget of the
    other steps for the SAME document — the brief's own "stop it, mark it
    skipped, continue" is about the step, not the document.
    """
    if not seconds or seconds <= 0:
        yield
        return

    def _handler(signum, frame):  # noqa: ARG001
        raise TimeBudgetExceeded(f"{label} exceeded {seconds:.0f}s")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(int(seconds))
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _run_step(label: str, budget_s: float, fn, *args, **kwargs) -> Dict[str, Any]:
    """Run one step, catching a timeout OR any exception as a named finding.

    Returns `{"ok": True, "value": ...}` or `{"ok": False, "skipped"|
    "error": <reason>}` — never a bare value, so a caller cannot mistake a
    caught failure for a successful `None`.
    """
    t0 = time.time()
    try:
        with _time_budget(budget_s, label):
            value = fn(*args, **kwargs)
        return {"ok": True, "value": value, "wall_time_s": round(time.time() - t0, 3)}
    except TimeBudgetExceeded as exc:
        return {"ok": False, "skipped": f"too slow: {exc}",
                "wall_time_s": round(time.time() - t0, 3)}
    except Exception as exc:  # noqa: BLE001 — a step must never crash the run
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "wall_time_s": round(time.time() - t0, 3)}


# ─────────────────────────────────────────────────────────────────────────
# manifest
# ─────────────────────────────────────────────────────────────────────────

def _resolve_root(root_name: str) -> Path:
    if root_name == "repo":
        return REPO
    if root_name == "library":
        return library_root()
    raise AcceptanceError(f"unknown manifest root {root_name!r} (want 'repo' or 'library')")


def resolve_path(entry: Optional[Dict[str, Any]]) -> Optional[Path]:
    """A manifest `{"root": ..., "path": ...}` entry -> an absolute Path.

    Every real manifest entry has a `path` relative to `root`; an already-
    ABSOLUTE `path` is returned as-is regardless of `root`, which is what
    lets a test point a document at a temp file without needing to fake
    `library_root()` or write into the git tree.
    """
    if not entry:
        return None
    p = Path(entry["path"])
    if p.is_absolute():
        return p
    return _resolve_root(entry["root"]) / entry["path"]


def load_manifest(path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    if not path.is_file():
        raise AcceptanceError(f"no manifest at {path}")
    manifest = json.loads(path.read_text())
    ids = [d["id"] for d in manifest.get("documents", [])]
    if len(ids) != len(set(ids)):
        raise AcceptanceError(f"manifest has duplicate document ids: {ids}")
    for doc in manifest.get("documents", []):
        for required in ("id", "kind", "record", "count_page"):
            if required not in doc:
                raise AcceptanceError(
                    f"document {doc.get('id', '?')!r} is missing {required!r}")
        if doc["kind"] not in ("scan", "engraved"):
            raise AcceptanceError(
                f"document {doc['id']!r} has kind={doc['kind']!r}, want scan/engraved")
    return manifest


def save_manifest(manifest: Dict[str, Any], path: Path = MANIFEST_PATH) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n")


def select_documents(manifest: Dict[str, Any],
                     doc_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    docs = manifest.get("documents", [])
    if not doc_ids:
        return list(docs)
    wanted = set(doc_ids)
    have = {d["id"] for d in docs}
    missing = wanted - have
    if missing:
        raise AcceptanceError(f"no such document id(s) in the manifest: "
                              f"{sorted(missing)} (have: {sorted(have)})")
    return [d for d in docs if d["id"] in wanted]


def verify_receipts(manifest: Dict[str, Any], docs: List[Dict[str, Any]]
                    ) -> tuple[bool, List[str], bool]:
    """Compute or check each selected document's record md5.

    Returns `(ok, messages, manifest_changed)`. `manifest_changed` is True
    when a receipt was newly recorded (a first run) and the caller should
    persist the manifest. A MISMATCH is a hard refusal for the WHOLE run —
    "refuse a mismatch loudly" (the brief) — checked for every selected
    document BEFORE any expensive step runs, cheaply (md5 of a 461 MB file
    is under a second).
    """
    ok = True
    messages: List[str] = []
    changed = False
    for doc in docs:
        record_path = resolve_path(doc["record"])
        if record_path is None or not record_path.is_file():
            messages.append(f"{doc['id']}: record ABSENT at "
                            f"{doc.get('record', {}).get('path')}")
            continue
        actual = _md5(record_path)
        recorded = doc["record"].get("md5")
        if recorded is None:
            doc["record"]["md5"] = actual
            changed = True
            messages.append(f"{doc['id']}: receipt recorded ({actual})")
        elif recorded != actual:
            ok = False
            messages.append(
                f"{doc['id']}: RECORD MD5 MISMATCH — manifest says {recorded}, "
                f"file is {actual} ({record_path}). The frozen shared record "
                f"changed since the receipt was taken; refusing the whole run.")
        else:
            messages.append(f"{doc['id']}: receipt verified ({actual})")
    return ok, messages, changed


# ─────────────────────────────────────────────────────────────────────────
# machine proxies (Sec.6a — "controls, never objectives")
# ─────────────────────────────────────────────────────────────────────────

def _fraction(n: int, d: int) -> Optional[float]:
    return (n / d) if d else None


_DEFAULT_PART_NAME_RE = re.compile(r"^Staff p\d+-s\d+-\d+$")


def parts_named(xml_text: str) -> Dict[str, Any]:
    """Every `<part-name>` that is NOT the coordinate default `Staff p…`."""
    root = ET.fromstring(xml_text)
    names = [pn.text or "" for pn in root.findall(".//score-part/part-name")]
    named = [n for n in names if not _DEFAULT_PART_NAME_RE.match(n)]
    return {"n": len(named), "of": len(names),
            "fraction": _fraction(len(named), len(names)), "names": names}


def transpose_parts(xml_text: str) -> Dict[str, Any]:
    """How many `<part>`s carry a `<transpose>` (roadmap 2.1b's condensed
    Contrabass doubling — see `docs/DECISIONS.md` 2026-09-22)."""
    root = ET.fromstring(xml_text)
    n = sum(1 for p in root.findall("part") if p.find(".//transpose") is not None)
    return {"n": n, "of": len(root.findall("part"))}


def bars_add_up(xml_text: str) -> Dict[str, Any]:
    """Bars whose voice-1 timeline sums to the METER IN FORCE at that bar.

    Reuses `bar_fill.bar_total` (imported, not re-derived) for the
    per-measure sum, but drives it from EACH MEASURE'S OWN `<time>` in
    force rather than a caller-supplied constant. `bar_fill.py`'s own
    `--bar-beats` is REQUIRED precisely because a constant silently carries
    one document's meter onto another (its docstring, 2026-09-16 Brahms
    incident: 96.3% "overfull" against the wrong constant). The staged
    exporter tracks the meter in force per bar itself when
    `OMR_METER_SEGMENTS` is on (default; `export.meter_segments_enabled`),
    so the fact is already IN the file: each `<attributes><time>` starts a
    new meter that holds until the next one, per part. Reading it back out
    of the XML avoids a second, possibly-diverging read of `Q.METER`.

    A bar in a part that has not yet declared ANY `<time>` is
    UNASSESSABLE, counted apart — "where the meter is unknown the bar is
    unassessable" (the brief), never folded into "does not add up".
    """
    bar_fill = _import_from_path("acceptance_bar_fill", _BAR_FILL_MODULE)
    root = ET.fromstring(xml_text)
    exact = short = over = empty = unassessable = 0
    for part in root.findall("part"):
        div = None
        beats = beat_type = None
        for meas in part.findall("measure"):
            attrs = meas.find("attributes")
            if attrs is not None:
                d = attrs.find("divisions")
                if d is not None:
                    div = float(d.text)
                t = attrs.find("time")
                if t is not None:
                    b, bt = t.find("beats"), t.find("beat-type")
                    if b is not None and bt is not None:
                        beats, beat_type = float(b.text), float(bt.text)
            if div is None:
                continue
            if beats is None or beat_type is None:
                unassessable += 1
                continue
            total, _holds = bar_fill.bar_total(meas, div)
            want = beats * 4.0 / beat_type
            if abs(total) < 1e-9:
                empty += 1
            elif abs(total - want) < 1e-6:
                exact += 1
            elif total < want:
                short += 1
            else:
                over += 1
    assessed = exact + short + over + empty
    return {"exact": exact, "short": short, "overfull": over, "empty": empty,
            "unassessable": unassessable,
            "n": exact, "of": assessed,
            "fraction": _fraction(exact, assessed)}


def unread_bars(report: Dict[str, Any]) -> Dict[str, Any]:
    written = report.get("written", {})
    return {
        "empty_bars_padded": written.get("empty_bars_padded", 0),
        "empty_bars_padded_without_meter":
            written.get("empty_bars_padded_without_meter", 0),
        "tacet_bars_not_padded_without_meter":
            written.get("tacet_bars_not_padded_without_meter", 0),
    }


#: The specific `notes_not_written` reasons the brief names by name; every
#: OTHER reason the export report holds is still carried verbatim under
#: `report.notes_not_written` in the written JSON (Sec.6a item 3), so
#: nothing here is a filter on what gets recorded — only on what gets a
#: named proxy field.
_NAMED_DROP_REASONS = ("duration_narrowed", "no_pitch", "staff_not_identified",
                      "owned_by_another_staff", "ink_is_a_whole_rest")


def machine_proxies(xml_text: str, report: Dict[str, Any]) -> Dict[str, Any]:
    balance = report.get("balance", {})
    written_notes = report.get("written", {}).get("notes", 0)
    noteheads_in_log = balance.get("noteheads_in_log", 0)
    dropped = report.get("notes_not_written", {}) or {}
    return {
        "notes_reaching_file": {
            "n": written_notes, "of": noteheads_in_log,
            "fraction": _fraction(written_notes, noteheads_in_log),
        },
        "bars_add_up_to_the_meter_in_force": bars_add_up(xml_text),
        "parts_named": parts_named(xml_text),
        "held_out": {
            "staff_not_identified": dropped.get("staff_not_identified", 0),
            "of_noteheads_in_log": noteheads_in_log,
            "fraction": _fraction(dropped.get("staff_not_identified", 0),
                                  noteheads_in_log),
        },
        "unread_bars": unread_bars(report),
        "transpose_parts": transpose_parts(xml_text),
        "notes_doubled_to_condensed_slot":
            balance.get("notes_doubled_to_condensed_slot", 0),
        "named_drop_reasons": {k: dropped.get(k, 0) for k in _NAMED_DROP_REASONS},
        "all_drop_reasons": dict(dropped),
        "balanced": balance.get("balanced"),
    }


# ─────────────────────────────────────────────────────────────────────────
# engraved-only: reading F1 + OMR-NED
# ─────────────────────────────────────────────────────────────────────────

def reading_scores(record_path: Path, truth_path: Path, page_index: int) -> Dict[str, Any]:
    """Reading F1 against the exact page truth — STAGED path, unmodified
    scorer (`tools/omr/score_reading.py`), through the ADAPTER built for
    exactly this purpose in `benchmarks/omr-staged-engraved-2026-09/
    staged_reading.py` (its own docstring: "called here unchanged... so the
    staged number and the legacy number come out of one scorer"). Never
    re-implemented — that file's own history records the "page_index used
    positionally" trap this adapter exists to close.
    """
    SR_adapter = _import_from_path("acceptance_staged_reading", _STAGED_READING_MODULE)
    result = json.loads(record_path.read_text())
    truth = json.loads(truth_path.read_text())
    like, stats = SR_adapter.staged_as_result(result, page_index, apply_ownership=True)
    if not stats.get("detections_placed"):
        raise RuntimeError(f"adapter placed no detections on page {page_index} "
                          f"— reach stats: {stats}")
    SR_adapter._assert_report_sees_them(like, page_index, stats["detections_placed"])
    # `score_reading.report` is a CLI tool that also prints a table as a side
    # effect — captured and discarded here so `--json` output stays valid
    # JSON; the return value carries everything the table shows.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = SR_adapter.SR.report(truth, like, page_index, [0.5, 0.25, 0.75, 1.0, 1.5])
        # ⚠️ THE FRAME CONTROL, not an extra — `staged_reading.py`'s own
        # docstring calls it "THE DECISIVE CONTROL": a scorer reporting the
        # same F1 whether or not every detection is translated by two staff
        # spaces is measuring something other than position. Reused, not
        # re-derived.
        shift_spaces = 2.0
        dy = shift_spaces * stats["staff_space_px"]
        shifted = SR_adapter.SR.report(
            truth, SR_adapter._shift(like, page_index, 0.0, dy), page_index, [0.5])
    out["adapter"] = stats
    base_f1 = out["pooled"]["f1"]
    ctl_f1 = shifted["pooled"]["f1"]
    out["frame_control"] = {"shift_spaces": shift_spaces, "pooled_f1": ctl_f1,
                            "collapsed": ctl_f1 < base_f1 * 0.5}
    return out


def omr_ned_score(pred_xml_path: Path, truth_xml_path: Path) -> Dict[str, Any]:
    if not ON.available():
        raise RuntimeError("no musicdiff interpreter (OMRNED_PYTHON / "
                          ".venv-omrned) — see CLAUDE.md Sec.5a")
    return ON.score_pair(pred=pred_xml_path, truth=truth_xml_path,
                        name="acceptance", timeout_s=300.0)


# ─────────────────────────────────────────────────────────────────────────
# LilyPond (engraved only; a native staged exporter is roadmap 3.1)
# ─────────────────────────────────────────────────────────────────────────

def lilypond_check(xml_path: Path, out_dir: Path) -> Dict[str, Any]:
    import shutil as _shutil
    musicxml2ly = _shutil.which("musicxml2ly")
    lilypond = _shutil.which("lilypond")
    if not musicxml2ly or not lilypond:
        return {"available": False,
                "reason": f"musicxml2ly={musicxml2ly!r} lilypond={lilypond!r}"}
    out_dir.mkdir(parents=True, exist_ok=True)
    ly_path = out_dir / (xml_path.stem + ".ly")
    proc = subprocess.run([musicxml2ly, str(xml_path), "-o", str(ly_path)],
                         capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not ly_path.is_file():
        return {"available": True, "converted": False,
                "stderr": proc.stderr[-2000:], "stdout": proc.stdout[-2000:]}
    proc2 = subprocess.run([lilypond, "-o", str(out_dir), str(ly_path)],
                          capture_output=True, text=True, timeout=300)
    log = (proc2.stdout or "") + "\n" + (proc2.stderr or "")
    pdf_path = out_dir / (ly_path.stem + ".pdf")
    return {
        "available": True, "converted": True,
        "compiled": proc2.returncode == 0,
        "pdf_produced": pdf_path.is_file(),
        "barcheck_failures": len(_BARCHECK_RE.findall(log)),
        "lilypond_exit": proc2.returncode,
        "log_tail": log[-2000:],
    }


# ─────────────────────────────────────────────────────────────────────────
# side-by-side: the count page's print, plus a best-effort render of ours
# ─────────────────────────────────────────────────────────────────────────

def _print_page_png(pdf_path: Path, page_index: int, out_path: Path,
                    dpi: int = 150) -> Dict[str, Any]:
    import fitz  # PyMuPDF — shared dependency, neither LEGACY nor STAGED
    doc = fitz.open(pdf_path)
    try:
        if page_index < 0 or page_index >= doc.page_count:
            raise IndexError(f"page_index {page_index} out of range "
                            f"(0..{doc.page_count - 1})")
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_path))
    finally:
        doc.close()
    return {"path": str(out_path.relative_to(REPO)), "dpi": dpi,
            "page_index": page_index}


def _ours_render_png(xml_text: str, first_bar: int, last_bar: int,
                     out_path: Path) -> Dict[str, Any]:
    """A best-effort Verovio render of bars [first_bar, last_bar] of every
    part in `xml_text`, reusing `build_sidebyside.slice_measures` /
    `render_svg` (imported, not re-derived — that module's own docstring
    records why the attribute-carry-forward matters: a system that is not a
    part's first often opens with no clef/key/divisions at all)."""
    SBS = _import_from_path("acceptance_side_by_side", _SIDE_BY_SIDE_MODULE)
    root = ET.fromstring(xml_text)
    part_ids = [sp.get("id") for sp in root.findall(".//part-list/score-part")]
    if not part_ids:
        raise RuntimeError("exported file has no score-part elements")
    wanted = {pid: (first_bar, last_bar) for pid in part_ids}
    sliced = SBS.slice_measures(xml_text, wanted)

    import verovio
    tk = verovio.toolkit()
    svg = SBS.render_svg(tk, sliced, page_width=30000)
    if not svg:
        raise RuntimeError("verovio could not render the sliced excerpt")
    svg_path = out_path.with_suffix(".svg")
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg)

    import shutil as _shutil
    rsvg = _shutil.which("rsvg-convert")
    if rsvg:
        proc = subprocess.run([rsvg, "-o", str(out_path), str(svg_path)],
                             capture_output=True, text=True, timeout=60)
        if proc.returncode == 0 and out_path.is_file():
            return {"svg": str(svg_path.relative_to(REPO)),
                    "png": str(out_path.relative_to(REPO)),
                    "first_bar": first_bar, "last_bar": last_bar}
    # SVG written even where PNG conversion failed/absent — still usable.
    return {"svg": str(svg_path.relative_to(REPO)), "png": None,
            "first_bar": first_bar, "last_bar": last_bar,
            "note": "rsvg-convert unavailable or failed; SVG only"}


def build_side_by_side(doc: Dict[str, Any], xml_text: str, out_dir: Path
                       ) -> Dict[str, Any]:
    """The print page, plus a best-effort render of the corresponding bars.

    Per the brief: "if that needs a whole-movement export or fails, write
    the print page alone and say so." The print crop is always attempted
    first and independently of the "ours" render, so a failure in the
    second never costs the first.
    """
    pdf_path = resolve_path(doc["pdf"])
    count_page = doc["count_page"]
    page_index = count_page["pdf_page_index"]
    result: Dict[str, Any] = {}

    if pdf_path is None or not pdf_path.is_file():
        result["print"] = {"built": False, "reason": f"no PDF at {pdf_path}"}
    else:
        try:
            result["print"] = {"built": True,
                              **_print_page_png(pdf_path, page_index,
                                                out_dir / "print.png")}
        except Exception as exc:  # noqa: BLE001
            result["print"] = {"built": False,
                              "reason": f"{type(exc).__name__}: {exc}"}

    first_bar, last_bar = _bar_range_for_count_page(doc)
    if first_bar is None:
        result["ours"] = {"built": False,
                         "reason": "no bar-range mapping for this count page "
                                  "(needs a works.json window row, or the "
                                  "engraved fixture's known bar range) — "
                                  "print page alone"}
    else:
        try:
            result["ours"] = {"built": True,
                             **_ours_render_png(xml_text, first_bar, last_bar,
                                                out_dir / "ours.png")}
        except Exception as exc:  # noqa: BLE001
            result["ours"] = {"built": False,
                             "reason": f"{type(exc).__name__}: {exc} — "
                                      "print page alone"}
    return result


def _bar_range_for_count_page(doc: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    count_page = doc["count_page"]
    if "first_bar" in count_page and "last_bar" in count_page:
        return count_page["first_bar"], count_page["last_bar"]
    works_json_path = doc.get("works_json")
    row_id = count_page.get("works_row_id")
    if not works_json_path or not row_id:
        return None, None
    works_path = REPO / works_json_path
    if not works_path.is_file():
        return None, None
    rows = json.loads(works_path.read_text()).get("rows", [])
    row = next((r for r in rows if r.get("row_id") == row_id), None)
    if row is None:
        return None, None
    window = row.get("window") or {}
    lo, hi = window.get("first_ref_measure"), window.get("last_ref_measure")
    if lo is None or hi is None:
        return None, None
    return int(lo), int(hi)


# ─────────────────────────────────────────────────────────────────────────
# per-document orchestration
# ─────────────────────────────────────────────────────────────────────────

def process_document(doc: Dict[str, Any], *, step_timeout_s: float
                     ) -> Dict[str, Any]:
    doc_id = doc["id"]
    block: Dict[str, Any] = {"id": doc_id, "kind": doc["kind"],
                             "label": doc.get("label")}
    out_dir = OUT_DIR / doc_id
    out_dir.mkdir(parents=True, exist_ok=True)

    record_path = resolve_path(doc["record"])
    if record_path is None or not record_path.is_file():
        block["status"] = _ABSENT
        block["reason"] = f"no record at {doc.get('record', {}).get('path')}"
        return block
    block["record"] = {"path": str(doc["record"]["path"]),
                       "root": doc["record"]["root"],
                       "md5": doc["record"].get("md5")}

    # ── load + export ──────────────────────────────────────────────────
    def _load_and_export():
        result = json.loads(record_path.read_text())
        provenance = result.get("provenance") or {}
        xml, report = X.to_musicxml(result)
        return {"xml": xml, "report": report, "provenance": provenance}

    step = _run_step("load+export", step_timeout_s, _load_and_export)
    if not step["ok"]:
        block["status"] = "error" if "error" in step else _SKIPPED
        block["export"] = {k: v for k, v in step.items() if k != "value"}
        return block

    xml_text = step["value"]["xml"]
    report = step["value"]["report"]
    block["record"]["provenance"] = step["value"]["provenance"]
    block["export"] = {"ok": True, "bytes": len(xml_text),
                       "wall_time_s": step["wall_time_s"],
                       "report": report}
    xml_path = out_dir / f"{doc_id}.musicxml"
    xml_path.write_text(xml_text)
    block["export"]["path"] = str(xml_path.relative_to(REPO))

    if step["value"]["provenance"].get("dirty"):
        block.setdefault("caveats", []).append(
            "this record's own provenance is dirty:true — it was gathered "
            "from an uncommitted tree, not a reproducibility problem in "
            "this run, but worth knowing before trusting its figures")
    if doc["kind"] == "scan":
        block.setdefault("caveats", []).append(
            "this is a FROZEN four-page shared record (ROADMAP.md Phase 1 "
            "item 1.1, whole-movement gather, is not yet done), and its own "
            "ADJUDICATE/EVALUATE/INFER verdicts are exactly as they were at "
            "the commit named in record.provenance.commit above — a later "
            "ADJUDICATE/INFER rule (e.g. roadmap 2.1/2.1b's condensed-slot "
            "collapse) that landed AFTER that commit is not reflected here "
            "unless the record is re-gathered or re-adjudicated; compare "
            "that commit against ROADMAP.md before reading held_out/"
            "notes_doubled_to_condensed_slot as current")

    # ── machine proxies ────────────────────────────────────────────────
    proxy_step = _run_step("machine_proxies", step_timeout_s,
                           machine_proxies, xml_text, report)
    block["machine_proxies"] = (proxy_step["value"] if proxy_step["ok"]
                                else {"status": ("error" if "error" in proxy_step
                                                else _SKIPPED),
                                     **{k: v for k, v in proxy_step.items()
                                        if k != "value"}})

    # ── engraved-only: reading + omr_ned + lilypond ────────────────────
    if doc["kind"] == "engraved":
        truth = doc.get("truth") or {}
        pagetruth_path = REPO / truth["pagetruth"] if truth.get("pagetruth") else None
        truth_xml_path = REPO / truth["musicxml"] if truth.get("musicxml") else None
        count_page_index = doc["count_page"]["pdf_page_index"]

        if pagetruth_path and pagetruth_path.is_file():
            rstep = _run_step("reading_f1", step_timeout_s, reading_scores,
                              record_path, pagetruth_path, count_page_index)
            block["reading"] = (rstep["value"] if rstep["ok"] else
                                {"status": ("error" if "error" in rstep else _SKIPPED),
                                 **{k: v for k, v in rstep.items() if k != "value"}})
        else:
            block["reading"] = {"status": _ABSENT, "reason": "no page truth file"}

        if truth_xml_path and truth_xml_path.is_file():
            nstep = _run_step("omr_ned", step_timeout_s, omr_ned_score,
                              xml_path, truth_xml_path)
            block["omr_ned"] = (nstep["value"] if nstep["ok"] else
                                {"status": ("error" if "error" in nstep else _SKIPPED),
                                 **{k: v for k, v in nstep.items() if k != "value"}})
        else:
            block["omr_ned"] = {"status": _ABSENT, "reason": "no truth musicxml"}

        lstep = _run_step("lilypond", step_timeout_s, lilypond_check,
                          xml_path, out_dir / "lilypond")
        block["lilypond"] = (lstep["value"] if lstep["ok"] else
                             {"status": ("error" if "error" in lstep else _SKIPPED),
                              **{k: v for k, v in lstep.items() if k != "value"}})
    else:
        block["reading"] = {"status": _SKIPPED,
                           "reason": "reading F1 needs an exact page truth; "
                                    "the two scans have none (Sec.6a)"}
        block["omr_ned"] = {"status": _SKIPPED,
                           "reason": "OMR-NED needs an encoding truth; "
                                    "the two scans have none (Sec.6a)"}
        block["lilypond"] = {"status": _SKIPPED,
                            "reason": "LilyPond conversion is scoped to the "
                                     "engraved document by this item's brief"}

    # ── side-by-side ────────────────────────────────────────────────────
    sstep = _run_step("side_by_side", step_timeout_s, build_side_by_side,
                      doc, xml_text, out_dir / "side-by-side")
    block["side_by_side"] = (sstep["value"] if sstep["ok"] else
                             {"status": ("error" if "error" in sstep else _SKIPPED),
                              **{k: v for k, v in sstep.items() if k != "value"}})

    block["status"] = "ok"
    return block


# ─────────────────────────────────────────────────────────────────────────
# summary + table
# ─────────────────────────────────────────────────────────────────────────

def build_summary(documents: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for doc_id, block in documents.items():
        if block.get("status") != "ok":
            summary[doc_id] = {"status": block.get("status"),
                              "reason": block.get("reason")}
            continue
        mp = block.get("machine_proxies", {})
        row = {"status": "ok"}
        if isinstance(mp, dict) and "notes_reaching_file" in mp:
            row["notes_reaching_file"] = mp["notes_reaching_file"]
            row["bars_add_up"] = mp["bars_add_up_to_the_meter_in_force"]
            row["parts_named"] = mp["parts_named"]
            row["held_out"] = mp["held_out"]
            row["unread_bars"] = mp["unread_bars"]
        else:
            row["machine_proxies"] = mp
        if block["kind"] == "engraved":
            reading = block.get("reading", {})
            if isinstance(reading, dict) and "pooled" in reading:
                row["reading_pooled_f1"] = reading["pooled"].get("f1")
            else:
                row["reading"] = reading.get("status", reading)
            ned = block.get("omr_ned", {})
            row["omr_ned"] = (ned.get("omr_ned") if isinstance(ned, dict)
                             and "omr_ned" in ned else ned.get("status", ned))
        summary[doc_id] = row
    return summary


def render_table(current: Dict[str, Any]) -> str:
    lines = [f"tree {current['tree']}  dirty={current['dirty']}  "
            f"{current['date']}  wall_time_s={current.get('wall_time_s')}"]
    for doc_id, block in current["documents"].items():
        status = block.get("status")
        lines.append(f"\n[{doc_id}]  status={status}")
        if status != "ok":
            lines.append(f"  reason: {block.get('reason')}")
            continue
        mp = block.get("machine_proxies", {})
        if "notes_reaching_file" in mp:
            nrf = mp["notes_reaching_file"]
            baf = mp["bars_add_up_to_the_meter_in_force"]
            pn = mp["parts_named"]
            ho = mp["held_out"]
            ub = mp["unread_bars"]
            lines.append(f"  notes reaching file   {nrf['n']:>6} / {nrf['of']:<6} "
                        f"({nrf['fraction']:.3f})" if nrf["fraction"] is not None
                        else f"  notes reaching file   {nrf}")
            lines.append(f"  bars add up           {baf['n']:>6} / {baf['of']:<6} "
                        f"(unassessable={baf['unassessable']})")
            lines.append(f"  parts named           {pn['n']:>6} / {pn['of']:<6}")
            lines.append(f"  held_out (staff_not_identified)  {ho['staff_not_identified']}")
            lines.append(f"  unread bars (empty_bars_padded)  "
                        f"{ub['empty_bars_padded']}")
        else:
            lines.append(f"  machine_proxies: {mp.get('status', mp)}")
        if block["kind"] == "engraved":
            reading = block.get("reading", {})
            if isinstance(reading, dict) and "pooled" in reading:
                lines.append(f"  reading pooled F1     {reading['pooled']['f1']:.3f}")
            else:
                lines.append(f"  reading:              "
                            f"{reading.get('status', reading)}")
            ned = block.get("omr_ned", {})
            if isinstance(ned, dict) and "omr_ned" in ned:
                lines.append(f"  OMR-NED               {ned['omr_ned']:.4f}")
            else:
                lines.append(f"  OMR-NED:              {ned.get('status', ned)}")
            ly = block.get("lilypond", {})
            if isinstance(ly, dict) and ly.get("available"):
                lines.append(f"  LilyPond              compiled="
                            f"{ly.get('compiled')} pdf={ly.get('pdf_produced')} "
                            f"barcheck_failures={ly.get('barcheck_failures')}")
            else:
                lines.append(f"  LilyPond:             "
                            f"{ly.get('reason', ly.get('status'))}")
        sbs = block.get("side_by_side", {})
        if isinstance(sbs, dict) and "print" in sbs:
            lines.append(f"  side-by-side print:   "
                        f"{sbs['print'].get('built')}  "
                        f"ours: {sbs.get('ours', {}).get('built')}")
        else:
            lines.append(f"  side-by-side:         {sbs.get('status', sbs)}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────

def run(manifest_path: Path = MANIFEST_PATH, doc_ids: Optional[List[str]] = None,
       step_timeout_s: float = DEFAULT_STEP_TIMEOUT_S
       ) -> tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    """Run the whole harness. Returns `(current, manifest, receipt_messages)`.

    `manifest` is the (possibly receipt-mutated) in-memory dict; the caller
    decides whether to persist it. Raises `AcceptanceError` on a receipt
    mismatch or a bad manifest — that refusal happens BEFORE any document is
    processed.
    """
    manifest = load_manifest(manifest_path)
    docs = select_documents(manifest, doc_ids)
    ok, messages, manifest_changed = verify_receipts(manifest, docs)
    if not ok:
        raise AcceptanceError(
            "REFUSED — one or more record receipts do not match:\n  "
            + "\n  ".join(m for m in messages if "MISMATCH" in m))

    t0 = time.time()
    documents: Dict[str, Any] = {}
    for doc in docs:
        documents[doc["id"]] = process_document(doc, step_timeout_s=step_timeout_s)
    wall_time_s = round(time.time() - t0, 3)

    head = _git(["rev-parse", "HEAD"])
    status = _git(["status", "--porcelain"])
    current = {
        "tree": head,
        "dirty": bool(status),
        "date": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest_md5": hashlib.md5(
            json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "wall_time_s": wall_time_s,
        "documents": documents,
        "summary": build_summary(documents),
    }
    return current, manifest, messages


def write_current(current: Dict[str, Any], *, force: bool = False,
                  out_path: Path = CURRENT_PATH) -> Path:
    if current["dirty"] and not force:
        raise AcceptanceError(
            "refusing to write current.json on a DIRTY tree (uncommitted "
            "changes present); commit first, or pass --force to write "
            "anyway and record dirty=true.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(current, indent=2, sort_keys=False,
                                   default=str) + "\n")
    return out_path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    ap.add_argument("--doc", action="append",
                    help="restrict to this document id (repeatable)")
    ap.add_argument("--out", type=Path, default=CURRENT_PATH)
    ap.add_argument("--force", action="store_true",
                    help="write current.json even on a dirty tree")
    ap.add_argument("--no-write", action="store_true",
                    help="dry run: compute and print, write nothing")
    ap.add_argument("--json", action="store_true",
                    help="print the full current.json to stdout")
    ap.add_argument("--step-timeout", type=float, default=DEFAULT_STEP_TIMEOUT_S,
                    help="per-step time budget in seconds (default 900 = 15 min)")
    args = ap.parse_args(argv)

    try:
        # fd-1 -> fd-2 for the whole run: verovio's C++ layer writes its own
        # warnings straight to the real stdout descriptor, which would
        # otherwise land ahead of (and corrupt) the one JSON `print` below
        # when `--json` is requested. Progress already goes to stderr.
        with _os_level_stdout_to_stderr():
            current, manifest, messages = run(args.manifest, args.doc,
                                              args.step_timeout)
    except AcceptanceError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    for m in messages:
        print(m, file=sys.stderr)

    manifest_changed = any("recorded" in m for m in messages)
    if manifest_changed:
        save_manifest(manifest, args.manifest)
        print(f"wrote {args.manifest.relative_to(REPO)} (new receipt(s))",
              file=sys.stderr)

    if not args.no_write:
        try:
            path = write_current(current, force=args.force, out_path=args.out)
        except AcceptanceError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            print(render_table(current))
            return 2
        print(f"wrote {path.relative_to(REPO) if path.is_relative_to(REPO) else path}",
              file=sys.stderr)

    if args.json:
        print(json.dumps(current, indent=2, default=str))
    else:
        print(render_table(current))

    any_error = any(
        block.get("status") == "error"
        or (isinstance(block.get("export"), dict) and "error" in block["export"])
        for block in current["documents"].values()
    )
    return 1 if any_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
