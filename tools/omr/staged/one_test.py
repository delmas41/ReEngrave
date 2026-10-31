"""ROADMAP 2.244 -- ONE TEST COMMAND for lanes that run side by side (Sean, 2026-10-30: "Is there a way to work on big
items simultaneously and then run a single test that measure for the different jobs?" -- "Yes").

    python3 -m tools.omr.staged.one_test --flag OMR_A --flag OMR_B[=V] [--flag OMR_C ...] --out DIR
                                         [--plates litolff,brahms] [--from auto|adjudicate|gather]
                                         [--cell-map master] [--detector-cache DIR] [--tiles 9] [--unjudged-tiles 12]

Runs the frozen sample ONCE PER ARM, all on the same tree, stages, cells, detector cache and OCR:

    base         every flag OFF                      (the baseline every other arm is measured against)
    only-<FLAG>  that flag ON, the others OFF        (one per flag: each lane alone)
    all          every flag ON                       (the integration)

and prints, per arm against the baseline, the three measures of docs/measuring.md section 0 -- what changed in the exported
file by kind, the judged right->wrong (and unwritten->wrong), and the changed places nobody has judged -- then
INTERACTIONS: the places where `all` differs from the union of the singles (a change only the combination makes, a change a
single made that the combination loses), with the judged right->wrong that only the combination causes. One blind sheet
(Sean's tiles) is drawn across the lanes and the interactions, each tile's key naming its arm.

THE CONTROL LINE, AND WHAT IT REFUSES. Every arm records what it was built from (`arm_fingerprint`: the tree -- commit plus a
hash of any uncommitted tools/omr change --, the stage, the night record, the page list, the cells, the detector cache, the OCR
settings). `check_same` prints one control line and RAISES `ArmMismatch` if any arm differs from the baseline in any of them,
or if a tree cannot be named (an unnameable tree never equals anything, including itself). `--reuse` re-reads the arms already
under DIR/work and runs the same check, so arms from two runs, two trees or two stages cannot be compared.

Built on `lane_report` (the arm worker, the diff, the judged scorer, the tile cutter); it adds no reader and no flag.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import pathlib
import random
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DERIVED_CHECK = False

from . import lane_report as L

#: What an arm is built from; every one must be identical across the arms of one run.
FINGERPRINT_FIELDS = ("tree", "mode", "tag", "pages", "record", "gather_tree", "cells", "detector_cache", "ocr")


class ArmMismatch(SystemExit):
    """Arms built from different trees, stages, cells, detector caches or OCR cannot be compared."""


# ───────────────────────────── 1. what an arm was built from ─────────────────────────────

def tree_fingerprint(root: pathlib.Path = L.ROOT) -> Optional[str]:
    """`<commit12>:<hash12 of every uncommitted tools/omr change>`, or None when git cannot name the tree. None is never
    equal to anything (CLAUDE rule 8: a half-named tree is not a named tree)."""
    def git(*a: str) -> bytes:
        return subprocess.check_output(["git", *a], cwd=str(root), stderr=subprocess.DEVNULL)
    try:
        head = git("rev-parse", "HEAD").decode().strip()
        h = hashlib.sha256(git("diff", "HEAD", "--", "tools/omr"))
        for f in sorted(git("ls-files", "--others", "--exclude-standard", "--", "tools/omr").decode().split("\n")):
            if f.endswith(".py"):
                h.update(f.encode())
                h.update((root / f).read_bytes())
        return "%s:%s" % (head[:12], h.hexdigest()[:12])
    except Exception:                                           # noqa: BLE001
        return None


def arm_fingerprint(plate: str, mode: str, tag: str, pages: Sequence[int], gather_prov: Optional[Dict[str, Any]],
                    flag_names: Sequence[str]) -> Dict[str, Any]:
    """Built by the arm's own process (`lane_report.run_arm`). The parent adds `detector_cache` (it alone knows it)."""
    gp = gather_prov or {}
    rec = None
    if mode == "adjudicate" and not os.path.isdir(tag):
        try:
            st = L.record_path(plate, tag).stat()
            rec = [st.st_size, int(st.st_mtime)]
        except OSError:
            rec = None
    ocr = sorted((k, v) for k, v in os.environ.items() if k.startswith(("OMR_SURYA", "OMR_OCR")) and k not in set(flag_names))
    return dict(plate=plate, tree=tree_fingerprint(), mode=mode, tag=tag, pages=sorted(pages), record=rec,
                gather_tree=[gp.get("commit"), gp.get("dirty")] if mode == "gather" else None,
                cells=json.dumps(gp.get("cell_map"), sort_keys=True, default=str) if mode == "gather" else "saved record's own cells",
                detector_cache=None, ocr=[list(x) for x in ocr])


def control_line(fp: Dict[str, Any]) -> str:
    cells = fp.get("cells") or "?"
    return ("tree %s | stages %s | tag %s | pages %s | cells %s | detector cache %s | OCR %s"
            % (fp.get("tree"), fp.get("mode"), fp.get("tag"), fp.get("pages"), cells[:60], fp.get("detector_cache"),
               ",".join("%s=%s" % tuple(x) for x in fp.get("ocr") or ()) or "default"))


def check_same(arms: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
    """`arms[label][plate]` = that arm's fingerprint. Returns the ONE control line shared by every arm; raises `ArmMismatch`
    (printing every arm's line) if any arm differs from the first in any field of `FINGERPRINT_FIELDS`, or a tree is None."""
    labels = list(arms)
    plates = sorted({p for a in arms.values() for p in a})
    problems: List[str] = []
    for p in plates:
        ref_label = labels[0]
        ref = arms[ref_label].get(p)
        for lab in labels:
            fp = arms[lab].get(p)
            if fp is None or ref is None:
                problems.append("%s: arm %s has no %s run" % (p, lab, p) if fp is None else "%s: baseline missing" % p)
                continue
            if fp.get("tree") is None:
                problems.append("%s arm %s: the tree cannot be named (git failed), so it equals nothing" % (p, lab))
            for f in FINGERPRINT_FIELDS:
                if fp.get(f) != ref.get(f):
                    problems.append("%s arm %s differs from %s in %s: %r vs %r" % (p, lab, ref_label, f, fp.get(f), ref.get(f)))
    if problems:
        lines = ["REFUSED: these arms were not built from the same tree, cells and stages -- no comparison is made."]
        lines += ["  " + x for x in problems]
        lines += ["  control line, arm %s %s: %s" % (lab, p, control_line(fp)) for lab in labels for p, fp in sorted(arms[lab].items())]
        raise ArmMismatch("\n".join(lines))
    first = arms[labels[0]][plates[0]]
    return "CONTROL (every arm, every plate identical): " + control_line(first)


# ───────────────────────────── 2. the arms ─────────────────────────────

def arm_specs(flags: Sequence[Tuple[str, str, str]]) -> List[Tuple[str, List[Tuple[str, str, str]], str]]:
    """`[(label, flags for the worker, 'on'|'off')]`: base, one per flag, all. In a worker an arm 'on' sets each flag to its
    `on` value, so an arm with only some flags ON passes the others with `on` = `off`."""
    specs: List[Tuple[str, List[Tuple[str, str, str]], str]] = [("base", list(flags), "off")]
    if len(flags) > 1:
        for name, _off, _on in flags:
            specs.append(("only-" + name, [(n, o, v if n == name else o) for n, o, v in flags], "on"))
    specs.append(("all", list(flags), "on"))
    return specs


def _sig(c: dict) -> tuple:
    from .judged import key_place
    return (key_place(c.get("rg")) or ("page", c.get("page")), c["kind"], c["side"], str(c.get("value")), str(c.get("was")))


def interactions(singles: Dict[str, Sequence[dict]], together: Sequence[dict]) -> Dict[str, List[dict]]:
    """Where `all` differs from the UNION of the singles, by change signature (place, kind, side, value, was), as multisets:
    `only_together` = in `all` and in no single (the combination makes it); `only_alone` = in some single and not in `all`
    (the combination loses or replaces it; each carries its `arm`)."""
    union: collections.Counter = collections.Counter()
    where: Dict[tuple, List[Tuple[str, dict]]] = collections.defaultdict(list)
    for lab, ch in singles.items():
        per = collections.Counter(_sig(c) for c in ch)
        union |= per                                        # multiset union: the larger count
        for c in ch:
            where[_sig(c)].append((lab, c))
    allc = collections.Counter(_sig(c) for c in together)
    only_t, only_a = [], []
    seen: collections.Counter = collections.Counter()
    for c in together:
        s = _sig(c)
        seen[s] += 1
        if seen[s] > union.get(s, 0):
            only_t.append(c)
    seen = collections.Counter()
    for s, n in (union - allc).items():
        for lab, c in where[s][:n]:
            only_a.append(dict(c, arm=lab))
    return dict(only_together=only_t, only_alone=only_a)


# ───────────────────────────── 3. the measures of one plate ─────────────────────────────

def plate_measures(plate: str, base: Dict[str, Any], arm: Dict[str, Any], base_mini: Optional[pathlib.Path],
                   arm_mini: Optional[pathlib.Path]) -> Dict[str, Any]:
    """The three measures of one arm against the baseline, on one plate. `*_mini` None skips the judged and unjudged parts (tests)."""
    d = L.diff_arms(base, arm, tol=0.5 * L.PLATES[plate]["unit"])
    out = dict(counts=d["counts"], changes=d["changes"], same=d["same"], hosts=d["hosts"], paired=d["paired"],
               red_bars=[base["red_bars"], arm["red_bars"]], notes_not_written=[base["notes_not_written"], arm["notes_not_written"]],
               control=arm.get("control"))
    if base_mini is not None and arm_mini is not None:
        out["judged"] = L.judged_moves(base_mini, arm_mini, plate, base["hosts"], arm["hosts"])
        un = L.unjudged_for_plate(plate, d["changes"], arm_mini)
        out["unjudged"] = un
    return out


def worse_keys(m: Dict[str, Any]) -> set:
    j = m.get("judged") or {}
    return ({("worse", w["item"], w["tile"]) for w in j.get("worse", ())}
            | {("unwritten_wrong", w["item"], w["tile"]) for w in j.get("unwritten_wrong", ())})


def interaction_worse(meas: Dict[str, Dict[str, Any]]) -> List[tuple]:
    """Judged right->wrong / unwritten->wrong in `all` that no single causes: the combination's own damage."""
    singles = set().union(*[worse_keys(m) for lab, m in meas.items() if lab not in ("base", "all")] or [set()])
    return sorted(worse_keys(meas["all"]) - singles)


# ───────────────────────────── 4. the report ─────────────────────────────

def pick_lane_tiles(by_arm: Dict[str, Dict[str, List[dict]]], together: Dict[str, List[dict]], same_all: Dict[str, List[dict]],
                    seed: int, n_cases: int = 9, n_controls: int = 3) -> List[dict]:
    """One sheet across the lanes: `n_cases` split evenly between each single arm and the interactions (only-together
    changes), drawn by `lane_report.pick_tiles`; then up to `n_controls` unchanged symbols of the kinds drawn. Every tile
    carries the `arm` it came from. `by_arm[label][plate]` = that arm's changes."""
    groups = [(lab, ch) for lab, ch in by_arm.items() if any(ch.values())]
    if any(together.values()):
        groups.append(("interaction", together))
    if not groups:
        return []
    rng = random.Random(seed)
    base_q, extra = divmod(n_cases, len(groups))
    order = list(range(len(groups)))
    rng.shuffle(order)
    cases: List[dict] = []
    for rank, gi in enumerate(order):
        lab, ch = groups[gi]
        q = base_q + (1 if rank < extra else 0)
        for it in L.pick_tiles(ch, {}, seed + gi, n_cases=q, n_controls=0)[:q]:
            if not any(L._same_ink(it, x) for x in cases):
                cases.append(dict(it, arm=lab))
    controls: List[dict] = []
    pool = [dict(s, plate=p) for p, ss in sorted(same_all.items()) for s in ss if s.get("box") and s.get("page") is not None]
    rng.shuffle(pool)
    for kind in [c["kind"] for c in cases] + ["note"]:
        if len(controls) >= n_controls:
            break
        for s in pool:
            if s["kind"] == kind and not any(L._same_ink(s, x) for x in cases + controls):
                controls.append(dict(s, role="control", side="unchanged", arm="control"))
                break
    items = cases + controls
    rng.shuffle(items)
    return items


def render(rep: Dict[str, Any]) -> str:
    L_ = []
    L_.append("ONE TEST  flags %s  --from %s" % (", ".join("%s (OFF=%s ON=%s)" % tuple(f) for f in rep["flags"]), rep["mode"]))
    for n in rep["notes"]:
        L_.append("  " + n)
    L_.append(rep["control"])
    for p, per in rep["plates"].items():
        L_.append("")
        L_.append("%s  pages %s" % (p, per["pages"]))
        for lab, m in per["arms"].items():
            if lab == "base":
                c = m.get("control")
                L_.append("  base: %d notes+rests%s" % (m["hosts"][0], "" if not c else "; duration/rest verdicts differing from the saved record: %d of %d"
                                                          % (c["differ"], c["stored"])))
                continue
            L_.append("  arm %s" % lab)
            L_.append("    file:   " + L.format_counts(m["counts"]) + " | red bars %s -> %s | notes not written %s -> %s"
                      % (m["red_bars"][0], m["red_bars"][1], m["notes_not_written"][0], m["notes_not_written"][1]))
            j = m.get("judged")
            if j is not None:
                L_.append("    judged: right->wrong %s | unwritten->wrong %d | wrong->right %s | right->gone %d  (%d tiles on these pages)"
                          % (L.blue_count(j["worse"]), len(j.get("unwritten_wrong", ())), L.blue_count(j.get("better", ())), len(j["lost"]), j["scored"]))
                for w in j["worse"]:
                    L_.append("      RIGHT->WRONG  %s tile %s %s  Sean: %s  now: %s" % (w["item"], w["tile"], w["subject"], w["answer"], w["now"]))
                for w in j.get("unwritten_wrong", ()):
                    L_.append("      UNWRITTEN->WRONG  %s tile %s %s  Sean: %s  now: %s" % (w["item"], w["tile"], w["subject"], w["answer"], w["now"]))
            u = m.get("unjudged")
            if u is not None:
                L_.append("    NOT JUDGED: %d changed places no tile of Sean's covers (%d covered, %d without a page place): %s"
                          % (len(u["unjudged"]), u["judged"], u["no_place"],
                             ", ".join("%s %d" % kv for kv in sorted(collections.Counter(c["kind"] for c in u["unjudged"]).items())) or "none"))
        it = per["interactions"]
        L_.append("  INTERACTIONS (all vs the union of the singles): %d only together | %d a single made that the combination loses | "
                  "judged right->wrong only together: %d"
                  % (len(it["only_together"]), len(it["only_alone"]), len(it["worse"])))
        for c in it["only_together"][:15]:
            L_.append("      only together  p%s %s %s %s %s" % (c.get("page"), "/".join(map(str, L_place(c))), c["kind"], c["side"], c.get("value")))
        for c in it["only_alone"][:15]:
            L_.append("      lost in combination (%s)  p%s %s %s %s %s" % (c["arm"], c.get("page"), "/".join(map(str, L_place(c))), c["kind"], c["side"], c.get("value")))
        for k in it["worse"]:
            L_.append("      INTERACTION RIGHT->WRONG  %s %s tile %s" % k)
    L_.append("")
    for lab, line in rep["landing"].items():
        L_.append("%-14s %s" % (lab, line))
    t = rep["tiles"]
    L_.append("")
    L_.append("tiles: %d (%d from the changes, %d controls), seed %d -> tiles/ (sheet.png), key.json outside the folder, each tile's arm in the key"
              % (t["n"], t["cases"], t["controls"], rep["tile_seed"]))
    if "unjudged_tiles" in rep:
        L_.append("unjudged tiles: %d -> unjudged/" % rep["unjudged_tiles"]["n"])
    L_.append("wall time %.0f s" % rep["wall_seconds"])
    return "\n".join(L_)


def L_place(c: dict) -> list:
    from .judged import key_place
    return list(key_place(c.get("rg")) or ["-"])


def landing(meas_by_plate: Dict[str, Dict[str, Dict[str, Any]]], labels: Sequence[str]) -> Dict[str, str]:
    """One landing line per arm: judged right->wrong and unwritten->wrong summed over the plates (both must be 0)."""
    out = {}
    for lab in labels:
        if lab == "base":
            continue
        rw = sum(len(m[lab]["judged"]["worse"]) for m in meas_by_plate.values() if m[lab].get("judged"))
        uw = sum(len(m[lab]["judged"].get("unwritten_wrong", ())) for m in meas_by_plate.values() if m[lab].get("judged"))
        out[lab] = ("LANDING CHECK: judged right->wrong 0, unwritten->wrong 0" if rw == 0 and uw == 0 else
                    "LANDING CHECK FAILS: judged right->wrong %d, unwritten->wrong %d -- must be 0 to land" % (rw, uw))
    return out


def run(flags: Sequence[Tuple[str, str, str]], plates: Sequence[str], mode: str, out: pathlib.Path, tag: str, seed: int,
        workers: int, sample: Dict[str, Any], notes: Sequence[str], n_cases: int = 9, unjudged_tiles: int = 0,
        reuse: bool = False) -> Dict[str, Any]:
    t0 = time.time()
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    pages = {p: sample["plates"][p]["pages"] for p in plates}
    specs = arm_specs(flags)
    env0 = dict(os.environ)
    if mode == "adjudicate" and not reuse:
        for p in plates:
            L.ensure_slices(p, L.loaded_pages(sample, p), tag)
    done: Dict[Tuple[str, str], Dict[str, Any]] = {}
    jobs = [(lab, p) for lab, _f, _a in specs for p in plates]
    flag_map = {lab: (f, a) for lab, f, a in specs}
    gathered: Dict[Tuple[str, str], pathlib.Path] = {}
    if not reuse and mode == "gather":
        for lab, p in jobs:
            fl, arm = flag_map[lab]
            gathered[(lab, p)] = L.gather_one(p, lab, {n: (on if arm == "on" else off) for n, off, on in fl}, pages[p], work, env0)
    running: List[Tuple[Tuple[str, str], subprocess.Popen]] = []
    queue = [] if reuse else list(jobs)
    while queue or running:
        while queue and len(running) < max(1, workers):
            lab, p = queue.pop(0)
            fl, arm = flag_map[lab]
            w = work / lab
            w.mkdir(parents=True, exist_ok=True)
            args = ["arm", "--tag", tag, "--work", str(w), "--from", mode, "--plate", p, "--arm", arm, "--pages", ",".join(map(str, pages[p]))]
            for n, off, on in fl:
                args += ["--flag", "%s=%s:%s" % (n, off, on)]
            if mode == "gather":
                args += ["--gathered", str(gathered[(lab, p)])]
            running.append(((lab, p), L._spawn(args, dict(env0), w / ("%s.log" % p))))
        for item in list(running):
            (lab, p), proc = item
            if proc.poll() is not None:
                running.remove(item)
                if proc.returncode != 0:
                    raise SystemExit("arm %s %s failed: see %s" % (lab, p, work / lab / ("%s.log" % p)))
        time.sleep(1)
    arms: Dict[str, Dict[str, Dict[str, Any]]] = {lab: {} for lab, _f, _a in specs}
    for lab, p in jobs:
        arm = flag_map[lab][1]
        sym = json.loads((work / lab / ("%s.%s.symbols.json" % (p, arm))).read_text())
        sym["fingerprint"]["detector_cache"] = (str(L.DETECTOR_CACHE) if (L.DETECTOR_CACHE and mode == "gather") else None)
        arms[lab][p] = sym
    ctl = check_same({lab: {p: s["fingerprint"] for p, s in per.items()} for lab, per in arms.items()})
    meas: Dict[str, Dict[str, Dict[str, Any]]] = {p: {} for p in plates}
    inter: Dict[str, Dict[str, Any]] = {}
    for p in plates:
        base = arms["base"][p]
        base_mini = work / "base" / ("%s.off.mini-record.json" % p)
        meas[p]["base"] = dict(hosts=(len(base["hosts"]), len(base["hosts"])), control=base.get("control"))
        for lab, _f, _a in specs:
            if lab != "base":
                meas[p][lab] = plate_measures(p, base, arms[lab][p], base_mini, work / lab / ("%s.on.mini-record.json" % p))
        singles = {lab: meas[p][lab]["changes"] for lab, _f, _a in specs if lab not in ("base", "all")}
        it = interactions(singles, meas[p]["all"]["changes"])
        it["worse"] = interaction_worse(meas[p]) if len(specs) > 2 else []
        inter[p] = it
    labels = [lab for lab, _f, _a in specs]
    by_arm = {lab: {p: meas[p][lab]["changes"] for p in plates} for lab in labels if lab not in ("base", "all")} if len(specs) > 2 \
        else {"all": {p: meas[p]["all"]["changes"] for p in plates}}
    together = {p: inter[p]["only_together"] for p in plates}
    same_all = {p: meas[p]["all"]["same"] for p in plates}
    items = pick_lane_tiles(by_arm, together if len(specs) > 2 else {}, same_all, seed, n_cases=n_cases)
    rep: Dict[str, Any] = dict(flags=[list(f) for f in flags], mode=mode, notes=list(notes), control=ctl, tile_seed=seed, labels=labels,
                               plates={}, landing=landing(meas, labels))
    for p in plates:
        rep["plates"][p] = dict(pages=pages[p], arms={lab: {k: v for k, v in m.items() if k not in ("changes", "same")} for lab, m in meas[p].items()},
                                interactions=inter[p])
    rep["tiles"] = L.cut_tiles(items, out) if items else dict(n=0, cases=0, controls=0)
    if unjudged_tiles:
        pool: Dict[str, List[dict]] = {p: [] for p in plates}
        for p in plates:
            for lab, _f, _a in specs:
                if lab != "base" and meas[p][lab].get("unjudged"):
                    pool[p] += [dict(c, arm=lab) for c in meas[p][lab]["unjudged"]["unjudged"]]
        uitems = L.pick_tiles(pool, {}, seed, n_cases=unjudged_tiles, n_controls=0)[:unjudged_tiles]
        rep["unjudged_tiles"] = L.cut_tiles(uitems, out / "unjudged", readme_extra=(
            "\nThese tiles are places where our written mark CHANGED and none of your earlier answers covers them.\n")) \
            if uitems else dict(n=0, cases=0, controls=0)
    (out / "unjudged.txt").write_text("\n".join(
        l for p in plates for lab, m in meas[p].items() if m.get("unjudged") for l in L.unjudged_lines("%s/%s" % (p, lab), m["unjudged"]["unjudged"])) + "\n")
    rep["wall_seconds"] = round(time.time() - t0, 1)
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "report.txt").write_text(render(rep) + "\n")
    return rep


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flag", action="append", default=[], help="OMR_X (OFF=0, ON=1), OMR_X=V (ON=V) or OMR_X=OFFV:ONV; two or more")
    ap.add_argument("--plates", default="litolff,brahms")
    ap.add_argument("--from", dest="mode", default="auto", choices=("auto", "adjudicate", "gather"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default=None, help="the night record to replay (default lane_report.DEFAULT_TAG; a tag with no record raises)")
    ap.add_argument("--seed", type=int, default=2188)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--tiles", type=int, default=9, help="cases on the one blind sheet (3 controls are added)")
    ap.add_argument("--unjudged-tiles", type=int, default=0, metavar="N")
    ap.add_argument("--allow-unknown-flag", action="store_true")
    ap.add_argument("--detector-cache", default=None)
    ap.add_argument("--cell-map", default=None, metavar="DIR|master")
    ap.add_argument("--replay-gathered", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="re-read the arms already under OUT/work (and check them); runs nothing")
    a = ap.parse_args(argv)
    flags = L.parse_flags(a.flag)
    if len(flags) < 1:
        raise SystemExit("--flag NAME is required (two or more for a combined run; one gives base / all only)")
    sample = L.load_sample()
    tag = a.tag or L.DEFAULT_TAG
    plates = [p for p in a.plates.split(",") if p]
    L.check_tag(tag, plates, sample)
    mode, notes = L.decide_from(a.mode, flags, a.allow_unknown_flag, a.replay_gathered)
    if os.environ.get("LANE_REPORT_SAMPLE"):
        notes.append("NOT THE FROZEN SAMPLE: %s (a development control)" % L.SAMPLE_PATH)
    if a.detector_cache:
        L.DETECTOR_CACHE = None if a.detector_cache == "off" else pathlib.Path(a.detector_cache)
    if a.cell_map:
        if mode == "gather":
            L.CELL_MAP = L.CELL_MAP_ROOT if a.cell_map == "master" else pathlib.Path(a.cell_map)
            for p in plates:
                notes.append("cells LOADED from master %s (%s) for every arm" % (L.cell_map_version(p), p))
        else:
            notes.append("--cell-map applies to a re-gather only: --from %s replays the saved record's own cells" % mode)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = run(flags, plates, mode, out, tag, a.seed, min(4, max(1, a.workers)), sample, notes, n_cases=a.tiles,
              unjudged_tiles=min(12, max(0, a.unjudged_tiles)), reuse=a.reuse)
    print(render(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
