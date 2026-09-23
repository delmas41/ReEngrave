"""ROADMAP 2.6 — price a GATHER change off a SAVED record, base against arm.

⚠️⚠️ WHY THIS EXISTS AND WHAT IT IS NOT. `readjudicate.py` and
`reexport_arm.py` rebuild a `Log` from a saved record and re-run a LATER stage,
so both are structurally blind to a GATHER change and a zero from either is not
evidence (CLAUDE.md §6b). 2.6 IS a GATHER change. This rebuilds the log the
same way and then RE-RUNS THE GATHER SITE ITSELF —
`gather.gather_ownership_evidence` — over inputs reconstructed from the
record's own rows, once with `origin/main`'s code and once with this tree's,
then runs ADJUDICATE · GROUPS · EVALUATE · INFER · EXPORT over each.

⚠️ IT IS STILL NOT A RE-GATHER. The DETECTIONS are the ones the saved run
made: this cannot see a detector change, a new gather site, a changed cell
crop or a changed staff reading, and it never re-reads the PDF. It prices
exactly one thing — what the contest admits — and `real_gather_agreement.py`
is the control that its answer matches a real base-vs-arm CLI gather on one
page.

⚠️ THE BASE ARM RUNS THE BASE CODE, IT DOES NOT RESTATE IT. `--base-ref` is
read with `git show <ref>:tools/omr/staged/gather.py` into a module loaded
under the package `tools.omr.staged`, so the base arm is that file's own
`gather_ownership_evidence`, byte for byte. A probe that restated the old
predicate would be measuring its own restatement.

⚠️⚠️ THE DEFAULT IS A SHA, NOT A BRANCH, AND THAT IS NOT PEDANTRY. The
remote-tracking ref for main moved NINE times during the session that built
this -- other lanes pushing, and the ref is shared by every worktree of this
repository -- and two of those commits changed `gather.py`. A base arm named
by a branch is a base arm that cannot be reproduced, and worse, two runs of
this tool hours apart could silently price against two different bases.
`848dda47` is the merged main ROADMAP 2.6 was built on (it contains
`64c83c5f` and `61ea81ef`), and its `gather.py` is the one every figure in
`FINDINGS.md` was measured against.

⚠️ THE RECORD IS APPEND-ONLY AND NOTHING HERE MUTATES A COMMITTED ROW. The
saved record is read (through `record_io.load_record`, never bare
`json.loads`) and a NEW `Log` is built from its GATHER rows, in id order, with
the two quantities `gather_ownership_evidence` produces —
`Q.GLYPH_BAND_DISTANCE` and `Q.GLYPH_LADDER` — left out, because the arm is
going to produce them. Verdicts are never copied; every one below is recomputed.

⚠️⚠️ THE CONTROL, AND IT CAN FAIL. `--control` runs the BASE arm and compares
every `Q.GLYPH_OWNER` verdict against the ones the saved record actually
carries. If the rebuild does not reproduce the record, nothing this tool prints
is comparable to anything. `OWNER_REGATHER_BREAK_CONTROL=1` perturbs the staff
spacing by 1 % and the control goes RED — run that arm before believing the
green one (CLAUDE.md rule 7).

⚠️ THE SHIM IS AN IDENTITY TRANSFORM, DELIBERATELY. `gather._page_box` maps a
canonical box to page pixels through the cell's `bbox_page_px` and
`upscale_factor`; the record carries the PAGE box directly. So the shim cell is
`bbox_page_px=(0,0,…)` with `upscale_factor=1.0` and the shim detection's
canonical coordinates ARE the recorded page box — `_page_box` then returns that
box bit-exactly rather than through a derived scale factor, and no float error
enters.

    python3 benchmarks/omr-owner-domain-2026-09/regather_ownership.py \\
        <record.json> --control
    OWNER_REGATHER_BREAK_CONTROL=1 ... --control        # the RED arm
    python3 .../regather_ownership.py <record.json> --json out/<name>.json
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

for _p in list(Path(__file__).resolve().parents):
    if (_p / "tools" / "omr" / "staged" / "record_io.py").exists():
        sys.path.insert(0, str(_p))
        ROOT = _p
        break

from tools.omr.staged import adjudicate, evaluate, groups, infer   # noqa: E402
from tools.omr.staged import adjudicators, consequences            # noqa: E402,F401
from tools.omr.staged import export as EXPORT                      # noqa: E402
from tools.omr.staged import gather as GATHER_ARM                  # noqa: E402
from tools.omr.staged.record import Log, Q, Subject                 # noqa: E402
from tools.omr.staged.record_io import load_record                  # noqa: E402

#: Produced ONLY by `gather_ownership_evidence` (verified by grep over
#: `tools/omr/`: `gather.py:665`, `:678` and `:725` are the sole writers), so
#: dropping them from the rebuild removes exactly this arm's output and nothing
#: else. If a third producer ever appears this tool is silently wrong, which is
#: why the control compares verdicts and not just counts.
CONTEST_QUANTITIES = (Q.GLYPH_BAND_DISTANCE, Q.GLYPH_LADDER)

NOTEHEAD_PREFIX = "notehead"
NEARER_BY_SPACES = 0.5          # §7b's "clearly nearer" — restated, not moved


# ─────────────────────────────────────────────────────────────────────────────
# The base arm's code, loaded from git
# ─────────────────────────────────────────────────────────────────────────────

def load_base_gather(ref: str):
    """`<ref>:tools/omr/staged/gather.py`, as an importable module."""
    src = subprocess.run(
        ["git", "show", f"{ref}:tools/omr/staged/gather.py"],
        cwd=str(ROOT), capture_output=True, text=True, check=True).stdout
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"_gather_base_{abs(hash(ref))}.py"
    tmp.write_text(src)
    spec = importlib.util.spec_from_file_location(
        "tools.omr.staged._gather_base", str(tmp))
    mod = importlib.util.module_from_spec(spec)
    # ⚠️ `gather.py` uses RELATIVE imports, so the module must believe it is
    # inside the package or `from .record import …` fails.
    mod.__package__ = "tools.omr.staged"
    sys.modules["tools.omr.staged._gather_base"] = mod
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# The shim: the gather site's five arguments, out of the record
# ─────────────────────────────────────────────────────────────────────────────

class _Det:
    """One detection, in PAGE PIXELS wearing canonical clothes.

    See the module docstring: with an identity cell transform `_page_box`
    returns these four numbers unchanged, so the boxes the contest compares are
    the record's own `bbox_page_px` and not a rescaling of them.
    """

    __slots__ = ("smufl_name", "category", "x_canonical", "y_canonical",
                 "width_canonical", "height_canonical", "confidence")

    def __init__(self, name, category, box, conf):
        self.smufl_name = name
        self.category = category
        self.x_canonical = box[0]
        self.y_canonical = box[1]
        self.width_canonical = box[2] - box[0]
        self.height_canonical = box[3] - box[1]
        self.confidence = conf


class _Cell:
    __slots__ = ("page_index", "staff_index", "measure_index",
                 "bbox_page_px", "upscale_factor")

    def __init__(self, page_index, staff_index, measure_index):
        self.page_index = page_index
        self.staff_index = staff_index
        self.measure_index = measure_index
        self.bbox_page_px = [0.0, 0.0, 1.0, 1.0]
        self.upscale_factor = 1.0


class _Staff:
    __slots__ = ("staff_index", "line_ys")

    def __init__(self, staff_index, line_ys):
        self.staff_index = staff_index
        self.line_ys = line_ys


class _Page:
    def __init__(self, page_index):
        self.page_index = page_index


class _PWS:
    def __init__(self, page_index, staves):
        self.staves = staves
        self.page = _Page(page_index)


def build_inputs(rec: Dict[str, Any], break_control: bool = False):
    """Per page: (pws, cells, local, detections), from the record's own rows.

    ⚠️ ONE CALL PER PAGE, because `gather_ownership_evidence` reads
    `pws.page.page_index` for every subject it writes — the real gather calls
    it per page too.
    """
    staff_lines: Dict[Tuple[int, int, int], List[float]] = {}
    for o in rec["observations"]:
        if o["quantity"] != Q.STAFF_LINES:
            continue
        p = o["subject"].split("/")
        ys = [float(y) for y in o["value"]]
        if len(ys) >= 2:
            if break_control:
                # ⚠️ THE RED ARM. Stretch the band 1 % about its top edge, so
                # every band distance and every spacing moves and the base arm
                # can no longer reproduce the record.
                top = min(ys)
                ys = [top + (y - top) * 1.01 for y in ys]
            staff_lines[(int(p[1]), int(p[2]), int(p[3]))] = ys

    glyphs: Dict[Tuple[int, int, int, int], Dict[int, _Det]] = (
        collections.defaultdict(dict))
    for o in rec["observations"]:
        if o["quantity"] != Q.GLYPH_BOX:
            continue
        p = o["subject"].split("/")
        detail = o.get("detail") or {}
        box = detail.get("bbox_page_px")
        if box is None:
            # ⚠️ DECLINED, not defaulted: a glyph with no page position cannot
            # enter a cross-staff contest and the real gather skips it too
            # (`_page_box` returns None). Counted by the caller.
            continue
        glyphs[(int(p[1]), int(p[2]), int(p[3]), int(p[4]))][int(p[5])] = _Det(
            str(o["value"][0]), str(detail.get("category")),
            [float(v) for v in box], float(o.get("score") or 0.0))

    pages = sorted({k[0] for k in staff_lines})
    out = []
    for page in pages:
        staves, local = [], {}
        for i, (key, ys) in enumerate(
                sorted((k, v) for k, v in staff_lines.items() if k[0] == page)):
            staves.append(_Staff(i, ys))
            local[i] = (key[1], key[2])
        staff_of = {(s, t): i for i, (s, t) in local.items()}
        cells, dets = [], {}
        for (pg, system, staff, cell), by_index in sorted(glyphs.items()):
            if pg != page:
                continue
            idx = staff_of.get((system, staff))
            if idx is None:
                continue
            cells.append(_Cell(page, idx, cell))
            # ⚠️ THE GLYPH ORDINAL IS THE LIST POSITION. `enumerate(dets)` is
            # what names the subject, so the list must be dense and in the
            # record's own order or every subject key shifts.
            n = max(by_index) + 1
            if sorted(by_index) != list(range(n)):
                raise SystemExit(
                    f"glyph ordinals are not dense at cell/{pg}/{system}/"
                    f"{staff}/{cell}: {sorted(by_index)}")
            dets[Subject.from_key(
                f"cell/{page}/{system}/{staff}/{cell}").to_key()] = [
                by_index[i] for i in range(n)]
        out.append((_PWS(page, staves), cells, local, dets))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The rebuild
# ─────────────────────────────────────────────────────────────────────────────

def rebuild(rec: Dict[str, Any]) -> Log:
    """One Log holding the saved record's GATHER rows MINUS the contest's."""
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        if r["quantity"] in CONTEST_QUANTITIES:
            continue
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def run_arm(rec: Dict[str, Any], gather_mod, inputs, label: str,
            progress: bool = True) -> Dict[str, Any]:
    """Rebuild · contest · ADJUDICATE · GROUPS · EVALUATE · INFER · EXPORT."""
    t0 = time.time()
    log = rebuild(rec)
    for pws, cells, local, dets in inputs:
        gather_mod.gather_ownership_evidence(log, pws, cells, local, dets)
    band = [r for r in log.all_rows()
            if getattr(r, "quantity", None) == Q.GLYPH_BAND_DISTANCE]
    if progress:
        print(f"  [{label}] contest rows {len(band)}  "
              f"({time.time() - t0:.0f}s)", flush=True)
    adjudicate.run(log)
    groups.run(log)
    report = evaluate.run(log)
    if infer.stage_should_run():
        infer.run(log, report)
    result = {"record": log.to_json()}
    if progress:
        print(f"  [{label}] stages done ({time.time() - t0:.0f}s), "
              f"exporting", flush=True)
    unbalanced = None
    try:
        _xml, xrep = EXPORT.to_musicxml(result)
        notes = int((xrep.get("written") or {}).get("notes", 0))
    except EXPORT.Unbalanced as exc:            # pragma: no cover - a defect
        unbalanced, xrep, notes = str(exc), {}, 0
        _xml = ""
    out = {
        "label": label,
        "band_rows": len(band),
        "band_subjects": sorted({r.subject.to_key() for r in band}),
        "ladder_rows": sum(1 for r in log.all_rows()
                           if getattr(r, "quantity", None) == Q.GLYPH_LADDER),
        "owner_verdicts": {v["subject"]: {
            "outcome": v["outcome"], "value": v.get("value"),
            "reason": v.get("reason")}
            for v in log.to_json()["verdicts"]
            if v["quantity"] == Q.GLYPH_OWNER},
        "notes_written": notes,
        "note_elements": _xml.count("<note") if _xml else 0,
        # ⚠️⚠️ THE WHOLE `written` COUNTER, NOT JUST THE NOTES. `category` is
        # COARSE -- `structural` is beam + slur + tie + ledgerLine + dot, and
        # `dynamic` is every letter and both hairpins -- so widening the
        # identity test to it widens the contest for families the notehead
        # accounting control cannot see. `adjudicate_dynamic` DROPS a letter
        # whose owner names another staff (`text.py:151`), which is exactly
        # the kind of loss a note-only count would report as clean.
        "written": dict(xrep.get("written") or {}),
        "decided_and_unwritten_total": xrep.get("decided_and_unwritten_total"),
        "detected_and_unrepresented_total": xrep.get(
            "detected_and_unrepresented_total"),
        "notes_not_written": dict(xrep.get("notes_not_written") or {}),
        "balance": xrep.get("balance"),
        "unaccounted": list((xrep.get("status_census") or {})
                            .get("unaccounted") or []),
        "unbalanced": unbalanced,
        "seconds": round(time.time() - t0, 1),
    }
    if progress:
        print(f"  [{label}] notes {out['notes_written']}  "
              f"owner verdicts {len(out['owner_verdicts'])}  "
              f"({out['seconds']}s)", flush=True)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The §7b/§10 population, recomputed here so before/after is one definition
# ─────────────────────────────────────────────────────────────────────────────

def suspicious_population(rec: Dict[str, Any]) -> List[Tuple[str, str, float,
                                                             str, float]]:
    """Noteheads a neighbouring staff is CLEARLY nearer to (> 0.5 space).

    ⚠️ 358 IS NOT A MISATTRIBUTION COUNT (§7b). It is the population carrying
    the geometric signature of the two subjects Sean adjudicated against the
    print, and it is used here only because it is the population §10 counted
    161 / 189 / 8 over — so before and after are the same question.
    """
    geom = {}
    for o in rec["observations"]:
        if o["quantity"] != Q.STAFF_LINES:
            continue
        ys = [float(y) for y in o["value"]]
        if len(ys) >= 2:
            geom[o["subject"]] = (ys, (max(ys) - min(ys)) / (len(ys) - 1))
    by_system = collections.defaultdict(list)
    for key in geom:
        p = key.split("/")
        by_system[(p[1], p[2])].append(key)

    def band(y, lines, sp):
        top, bottom = min(lines), max(lines)
        if top <= y <= bottom:
            return 0.0
        gap = (top - y) if y < top else (y - bottom)
        return gap / sp if sp else gap

    out = []
    for o in rec["observations"]:
        if o["quantity"] != Q.GLYPH_BOX:
            continue
        name = str(o["value"][0])
        if not name.lower().startswith(NOTEHEAD_PREFIX):
            continue
        box = (o.get("detail") or {}).get("bbox_page_px")
        if box is None:
            continue
        p = o["subject"].split("/")
        own = f"staff/{p[1]}/{p[2]}/{p[3]}"
        if own not in geom:
            continue
        y = (float(box[1]) + float(box[3])) / 2.0
        own_d = band(y, *geom[own])
        best, best_d = None, None
        for cand in by_system[(p[1], p[2])]:
            if cand == own:
                continue
            d = band(y, *geom[cand])
            if best_d is None or d < best_d:
                best, best_d = cand, d
        if best is None:
            continue
        if best_d + NEARER_BY_SPACES < own_d:
            out.append((o["subject"], own, own_d, best, best_d))
    return out


def split(pop, verdicts: Dict[str, Any]) -> Dict[str, List[str]]:
    """§7b's four buckets over one arm's verdicts."""
    near, elsewhere, never = [], [], []
    for sub, own, _od, best, _bd in pop:
        v = verdicts.get(sub)
        if v is None:
            never.append(sub)
        elif v.get("value") == best:
            near.append(sub)
        else:
            elsewhere.append(sub)
    return {"near": near, "elsewhere": elsewhere, "never": never}


# ─────────────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--base-ref", default="848dda47")
    ap.add_argument("--control", action="store_true",
                    help="run the BASE arm only and diff it against the record")
    ap.add_argument("--json", dest="out_json")
    a = ap.parse_args(argv)

    break_control = os.environ.get("OWNER_REGATHER_BREAK_CONTROL") == "1"
    print(f"loading {a.record} ...", flush=True)
    t0 = time.time()
    rec = load_record(a.record)["record"]
    print(f"  observations {len(rec['observations'])}  "
          f"abstentions {len(rec['abstentions'])}  "
          f"verdicts {len(rec['verdicts'])}  ({time.time() - t0:.0f}s)",
          flush=True)

    saved_owner = {v["subject"]: {"outcome": v["outcome"],
                                  "value": v.get("value"),
                                  "reason": v.get("reason")}
                   for v in rec["verdicts"] if v["quantity"] == Q.GLYPH_OWNER}
    saved_band = sum(1 for o in rec["observations"]
                     if o["quantity"] == Q.GLYPH_BAND_DISTANCE)
    print(f"  the record's own: {saved_band} band rows, "
          f"{len(saved_owner)} glyph_owner verdicts", flush=True)

    inputs = build_inputs(rec, break_control=break_control)
    print(f"  shim: {len(inputs)} page(s), "
          f"{sum(len(c) for _p, c, _l, _d in inputs)} cells"
          + ("   ⚠️ SPACING PERTURBED 1% (RED ARM)" if break_control else ""),
          flush=True)

    base_mod = load_base_gather(a.base_ref)
    print(f"  base code: {a.base_ref}  CONTEST_IOU="
          f"{base_mod.CONTEST_IOU}   arm code: this tree  CONTEST_IOU="
          f"{GATHER_ARM.CONTEST_IOU}", flush=True)

    base = run_arm(rec, base_mod, inputs, "base")

    # ── THE CONTROL ─────────────────────────────────────────────────────────
    same = sorted(k for k in saved_owner
                  if k in base["owner_verdicts"]
                  and base["owner_verdicts"][k] == saved_owner[k])
    changed = sorted(k for k in saved_owner
                     if base["owner_verdicts"].get(k) != saved_owner[k])
    extra = sorted(k for k in base["owner_verdicts"] if k not in saved_owner)
    print()
    print(f"CONTROL  base arm vs the record's own glyph_owner verdicts: "
          f"{len(same)} of {len(saved_owner)} reproduced exactly, "
          f"{len(changed)} differ, {len(extra)} extra")
    print(f"         band rows: record {saved_band}, base arm "
          f"{base['band_rows']}")
    ok = not changed and not extra and base["band_rows"] == saved_band
    if not ok:
        print("  ⚠️ THE REBUILD IS NOT THE RECORD — nothing below is comparable")
        for k in changed[:10]:
            print(f"     {k}  record {saved_owner[k]}  "
                  f"base {base['owner_verdicts'].get(k)}")
    if a.control:
        if a.out_json:
            Path(a.out_json).write_text(json.dumps(
                {"record": a.record, "base_ref": a.base_ref,
                 "break_control": break_control,
                 "reproduced": len(same), "of": len(saved_owner),
                 "changed": changed[:200], "extra": extra[:200],
                 "band_rows_record": saved_band,
                 "band_rows_base": base["band_rows"]}, indent=1))
            print(f"wrote {a.out_json}")
        return 0 if ok else 1
    if not ok:
        return 1

    arm = run_arm(rec, GATHER_ARM, inputs, "arm")

    # ── REACH FIRST ─────────────────────────────────────────────────────────
    pop = suspicious_population(rec)
    b_split = split(pop, base["owner_verdicts"])
    a_split = split(pop, arm["owner_verdicts"])
    handed_in = sorted(set(b_split["never"]) - set(a_split["never"]))
    print()
    print("REACH  (the §7b population: a neighbouring staff clearly nearer)")
    print(f"  noteheads carrying the signature        : {len(pop)}")
    print(f"  never contested   base {len(b_split['never']):5d}"
          f"  ->  arm {len(a_split['never']):5d}"
          f"   (handed in {len(handed_in)})")
    print(f"  resolved to the NEAR staff  base {len(b_split['near']):5d}"
          f"  ->  arm {len(a_split['near']):5d}")
    print(f"  resolved elsewhere          base {len(b_split['elsewhere']):5d}"
          f"  ->  arm {len(a_split['elsewhere']):5d}")
    print(f"  band-distance rows          base {base['band_rows']:5d}"
          f"  ->  arm {arm['band_rows']:5d}")
    print(f"  glyph_owner verdicts        base "
          f"{len(base['owner_verdicts']):5d}  ->  arm "
          f"{len(arm['owner_verdicts']):5d}")

    # ── THE CONTROL THAT MUST HOLD: the pre-existing verdicts ───────────────
    moved = sorted(k for k, v in base["owner_verdicts"].items()
                   if arm["owner_verdicts"].get(k) != v)
    prev_near_moved = sorted(set(moved) & set(b_split["near"]))
    print()
    print("THE 189 CONTROL  (every verdict the BASE arm already had)")
    print(f"  pre-existing glyph_owner verdicts that CHANGED: {len(moved)}")
    print(f"  of them, in the correctly-contested population : "
          f"{len(prev_near_moved)}")
    for k in moved[:40]:
        print(f"    {k}  base {base['owner_verdicts'][k]}  "
              f"arm {arm['owner_verdicts'].get(k)}")
    if len(moved) > 40:
        print(f"    ... {len(moved) - 40} more, all in the --json")

    # ── what the handed-in glyphs got ───────────────────────────────────────
    outcomes = collections.Counter()
    for sub in handed_in:
        v = arm["owner_verdicts"].get(sub)
        if v is None:
            outcomes["no verdict even now"] += 1
            continue
        own = "staff/" + "/".join(sub.split("/")[1:4])
        if v["outcome"] != "decided":
            outcomes[f"{v['outcome']}:{v.get('reason')}"] += 1
        elif v.get("value") == own:
            outcomes["decided -> its OWN staff"] += 1
        else:
            outcomes["decided -> the NEAR staff"] += 1
    print()
    print("WHAT THE NEWLY HANDED-IN GLYPHS GOT")
    for k, n in outcomes.most_common():
        print(f"    {k:40s} {n:5d}")

    # ── the accounting control ──────────────────────────────────────────────
    print()
    print("EXPORT")
    for arm_d in (base, arm):
        b = arm_d["balance"] or {}
        print(f"  [{arm_d['label']:4s}] <note> {arm_d['note_elements']:6d}  "
              f"notes {arm_d['notes_written']:6d}  "
              f"balanced={b.get('balanced')}  "
              f"unaccounted={arm_d['unaccounted']}  "
              f"Unbalanced={arm_d['unbalanced']}")
        print(f"         owned_by_another_staff="
              f"{arm_d['notes_not_written'].get('owned_by_another_staff', 0)}"
              f"   not_written_total="
              f"{sum(arm_d['notes_not_written'].values())}")
    print("  refusals, base -> arm:")
    for reason in sorted(set(base["notes_not_written"])
                         | set(arm["notes_not_written"])):
        b = base["notes_not_written"].get(reason, 0)
        c = arm["notes_not_written"].get(reason, 0)
        if b != c:
            print(f"    {reason:42s} {b:6d} -> {c:6d}  ({c - b:+d})")
    # ⚠️ EVERY counter that moved, because `category` is coarse and the
    # notehead balance cannot see a dynamic, an arc or a hairpin go.
    print("  EVERY written counter that moved, base -> arm:")
    moved_counters = 0
    for key in sorted(set(base["written"]) | set(arm["written"])):
        b = base["written"].get(key, 0)
        c = arm["written"].get(key, 0)
        if b != c:
            moved_counters += 1
            print(f"    {key:42s} {b:6d} -> {c:6d}  ({c - b:+d})")
    if not moved_counters:
        print("    (none)")
    print(f"  decided_and_unwritten      "
          f"{base['decided_and_unwritten_total']} -> "
          f"{arm['decided_and_unwritten_total']}")
    print(f"  detected_and_unrepresented "
          f"{base['detected_and_unrepresented_total']} -> "
          f"{arm['detected_and_unrepresented_total']}")

    if a.out_json:
        Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "record": a.record, "base_ref": a.base_ref,
            "control": {"reproduced": len(same), "of": len(saved_owner),
                        "changed": changed, "extra": extra,
                        "band_rows_record": saved_band,
                        "band_rows_base": base["band_rows"]},
            "population": len(pop),
            "never_contested": {"base": len(b_split["never"]),
                                "arm": len(a_split["never"])},
            "near": {"base": len(b_split["near"]),
                     "arm": len(a_split["near"])},
            "elsewhere": {"base": len(b_split["elsewhere"]),
                          "arm": len(a_split["elsewhere"])},
            "handed_in": handed_in,
            "handed_in_outcomes": dict(outcomes),
            "pre_existing_verdicts_changed": [
                {"subject": k, "base": base["owner_verdicts"][k],
                 "arm": arm["owner_verdicts"].get(k)} for k in moved],
            "arms": {k: {kk: vv for kk, vv in d.items()
                         if kk not in ("owner_verdicts", "band_subjects")}
                     for k, d in (("base", base), ("arm", arm))},
            "band_subjects_added": sorted(set(arm["band_subjects"])
                                          - set(base["band_subjects"])),
            # ⚠️ The arm's verdict on every subject the arm newly contested —
            # what `crop_contested.py` samples from, so the crops and the
            # numbers in FINDINGS come from ONE artefact and cannot drift.
            "arm_verdicts_on_added": {
                s: arm["owner_verdicts"].get(s)
                for s in sorted(set(arm["band_subjects"])
                                - set(base["band_subjects"]))},
            # The positive controls: verdicts the BASE arm already had, i.e.
            # the population §8 measured 189 of 197 correct on.
            "base_verdicts": base["owner_verdicts"],
        }
        Path(a.out_json).write_text(json.dumps(payload, indent=1))
        print(f"\nwrote {a.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
