"""A CONFIRMATION UI for the five scan-gate rows that carry no `staves` map.

    python3 benchmarks/omr-staves-map-2026-09/server.py      # -> :5075

WHAT IT IS FOR
--------------
`works.json`'s `staves[i].parts` maps each PRINTED staff to the reference parts
it carries.  Ten of the twenty scan rows have one; ten do not, and five of those
are cheap: 109 printed staves whose confirmation would let ~72% of the
unattributable `entire staff` bucket be attributed.

⚠️ 109 STAVES IS 58 MAP ENTRIES, AND BOTH NUMBERS ARE RIGHT.  109 is printed
staff INSTANCES — `page.n_staves`, which `probe_map_coverage_cost.py` counts as
"staves a human would read", and it sums a page's systems (p.3 is 11 + 8).  A
`staves` map is not per instance: `page_normalise` emits ONE OUTPUT PART per
entry, and a part is continuous across the systems of a page, so p.3's 19
printed staves are 11 slots.  It could not be otherwise — 19 entries against 18
reference parts is arithmetically impossible, and a map naming a part twice is
refused here for the same reason `IncompleteMap` refuses one naming a part not
at all.  The five rows: 109 instances, 58 slots, 18/18/18/18/21 parts.

⚠️ AND THIS IS NOT THE DETECTOR FALLING SHORT.  The obvious worry — the page
prints 19 and phase 1 finds 11, so the map is built over a short population —
was measured and is false on all five: detected staves equal `works.json`'s
printed count exactly, system for system (19=11+8, 22=11+11, 19, 22, 27=14+13).
The precedent that makes the worry reasonable is real (Beethoven p.86 prints 17
where phase 1 detects 16) but p.86 is not one of these pages.

So every one of the 109 printed instances is SHOWN — the centre panel stacks a
crop per system that prints the current slot, joined through the hand-read
`systems_as_printed` lineups — while the map Sean confirms has 58 entries.

WHY IT IS A CONFIRMATION AND NOT A DATA ENTRY TOOL
--------------------------------------------------
All five rows ALREADY carry a hand-read, print-verified `systems_as_printed`
block.  What they lack is not the reading — it is the PAGE-LEVEL map, because
`systems_as_printed` is per SYSTEM and the systems of these pages disagree with
each other (11 staves against 8, 14 against 13, or the same 11 with a different
lineup).  A `staves` map has no system dimension, so somebody has to choose
which lineup is the page's, and that is a judgement, not a transcription.

So the UI proposes the system whose lineup names the most reference parts, shows
the disagreement with the other systems, and asks for a keystroke per staff.

⚠️ IT NEVER WRITES `works.json`.  Decisions go to a separate additions file and
a reviewed merge step applies them:

    python3 benchmarks/omr-staves-map-2026-09/merge_additions.py            # dry
    python3 benchmarks/omr-staves-map-2026-09/merge_additions.py --write

PATHS
-----
  reads   <MAIN>/benchmarks/omr-scan-e2e-2026-09/works.json
          <MAIN>/library/editions/...                         (the PDFs)
          <MAIN>/.claude/worktrees/reconciliation/.../fixtures (the canonical run)
          ~/.cache/reengrave-staves-map/                       (the built cache)
  writes  <MAIN>/benchmarks/omr-scan-e2e-2026-09/works.staves-additions.json

Every path is in the MAIN checkout, so the work outlives any worktree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
from build_cache import MAIN, SCAN, default_cache  # noqa: E402
from build_cache import staves_schema, strip_crop_geometry  # noqa: E402
from merge_additions import prove_normalises  # noqa: E402

OUT_DEFAULT = SCAN / "works.staves-additions.json"

README = [
    "Hand-confirmed page-level `staves` maps for scan-gate rows that had none.",
    "",
    "Each entry is ONE PRINTED STAFF of the page and names the reference part",
    "indices it carries, in `page_normalise`'s index space (music21 Score.parts",
    "of the row's trimmed truth). Shape is works.json's `staves` verbatim, so a",
    "merged row needs no translation.",
    "",
    "PROPOSED from the row's own hand-read `systems_as_printed` (per SYSTEM),",
    "collapsed to the page by taking the system whose lineup names the most",
    "parts; CONFIRMED staff by staff by Sean against 600 dpi margin crops with",
    "the canonical run's own detected staff band drawn on the print.",
    "",
    "`verdict` per staff: `confirmed` = the proposal was right; `edited` = Sean",
    "changed it, and `proposed` records what it had been.",
    "",
    "A row reaches `done` only when every staff is decided, every reference",
    "part is named exactly once, and no part is named twice.",
    "",
    "NOT MERGED INTO works.json BY THIS FILE. See merge_additions.py.",
]


# ------------------------------------------------------------------- storage

class Store:
    """Sean's decisions.  Written on every mutation; never lost."""

    def __init__(self, path: Path):
        self.path = path
        self.doc = self._read()

    def _read(self) -> dict:
        if self.path.is_file():
            try:
                return json.loads(self.path.read_text())
            except json.JSONDecodeError:
                bad = self.path.with_suffix(".corrupt.json")
                shutil.copy2(self.path, bad)
                print(f"  !! {self.path} was unreadable; kept a copy at {bad}",
                      file=sys.stderr)
        return {"_README": README,
                "generated_by": "benchmarks/omr-staves-map-2026-09/server.py",
                "rows": {}}

    def save(self) -> None:
        self.doc["_README"] = README
        self.doc["updated_at"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds")
        # Atomic: a crash mid-write must not destroy what is already decided.
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.doc, indent=1) + "\n")
        tmp.replace(self.path)

    def row(self, row_id: str, seed: dict) -> dict:
        r = self.doc["rows"].get(row_id)
        if r is None:
            r = {
                "row_id": row_id,
                "status": "in_progress",
                "proposal_source": seed["proposal"].get("source"),
                "n_reference_parts": seed["reference"]["n_parts_music21"],
                "reference": seed["reference"]["catalog_path"],
                "evidence": {
                    "run_artefact": seed["detected"]["artefact"],
                    "run_artefact_origin": seed["detected"]["artefact_origin"],
                    "truth_for_part_indices": seed["reference"]["source"],
                    "dpi": 600,
                },
                # ⚠️ THE SEED CARRIES THE PROPOSAL'S EXTRA FACTS. It used to
                # be a hand-written `{name, parts}`, which is why the four
                # `lines: 1` percussion rules of `mahler-…-p2` were gone before
                # the human ever saw the row: dropped here, absent from
                # `staves_for_works_json`, absent from `works.json`, and the
                # part join stayed unresolved for a reason the file no longer
                # recorded. `staves_schema.project` is the one definition.
                "staves": [
                    dict(staves_schema.project(s)[0],
                         proposed={"name": s["name"], "parts": list(s["parts"])},
                         verdict="pending")
                    for s in seed["proposal"]["staves"]
                ],
            }
            self.doc["rows"][row_id] = r
            self.save()
        return r


# --------------------------------------------------------------- validation

def validate(row_state: dict, n_parts: int, *, needs_ack: bool = False) -> dict:
    """Everything that must hold before a row may be called done.

    ⚠️ `page_normalise` RAISES `IncompleteMap` on a map that does not name every
    part, on purpose — dropping a reference part makes the score go DOWN for the
    wrong reason.  A part named TWICE is the mirror fault and nothing downstream
    checks it, so it is checked here.
    """
    staves = row_state["staves"]
    counts: dict[int, int] = {}
    for s in staves:
        for i in s["parts"]:
            counts[i] = counts.get(i, 0) + 1
    unnamed = [i for i in range(n_parts) if i not in counts]
    doubled = sorted(i for i, c in counts.items() if c > 1)
    out_of_range = sorted(i for i in counts if i < 0 or i >= n_parts)
    empty = [k for k, s in enumerate(staves) if not s["parts"]]
    undecided = [k for k, s in enumerate(staves) if s["verdict"] == "pending"]
    problems = []
    if unnamed:
        problems.append(f"{len(unnamed)} reference part(s) unassigned: "
                        f"{unnamed} — page_normalise would refuse this map")
    if doubled:
        problems.append(f"part(s) named by more than one staff: {doubled}")
    if out_of_range:
        problems.append(f"part index out of range 0..{n_parts - 1}: {out_of_range}")
    if empty:
        problems.append(f"staff row(s) with no parts at all: {empty}")
    if undecided:
        problems.append(f"{len(undecided)} staff/staves not yet decided")
    # ⚠️ Where the page's systems print DIFFERENT lineups, one page-level map
    # cannot express both and the choice is a judgement with a cost. Beethoven
    # p.4 is the case: system 1 suppresses Timpani and SPLITS Violoncello from
    # Basso, system 2 keeps Timpani and condenses them. Whichever lineup the
    # map takes, the other system's staves pair against it imperfectly. That
    # must be acknowledged deliberately, not passed over by holding `t`.
    if needs_ack and not row_state.get("lineup_conflict_acknowledged"):
        problems.append("this page's systems print different lineups and one "
                        "page-level map cannot express both — acknowledge the "
                        "choice (press k) before marking it done")
    return {
        "n_parts": n_parts,
        "assigned": sorted(counts),
        "unnamed": unnamed,
        "doubled": doubled,
        "decided": len(staves) - len(undecided),
        "n_staves": len(staves),
        "ok": not problems,
        "problems": problems,
        "needs_ack": needs_ack,
        "acknowledged": bool(row_state.get("lineup_conflict_acknowledged")),
    }


# ---------------------------------------------------------------------- app


# ------------------------------- would it actually normalise? (the real gate)

class Prover:
    """Runs `merge_additions.prove_normalises` off the request thread.

    ⚠️ WHY THIS EXISTS. Until 2026-09-07 this UI checked only the CHEAP
    structural facts — every part named once, every staff decided — and never
    asked `page_normalise` anything. `merge_additions` does ask, before it
    writes, so a row could go green here, be marked `done`, and refuse at merge
    time with the human's whole pass already spent. That is exactly what two
    `page_normalise` faults did to Mahler p3 and p4.

    ⚠️ AND IT MAY NEVER COST A VERDICT. Sean's decisions are irreplaceable and
    the proof is a nicety beside them, so:

      * nothing here runs on the save path — a PATCH stores the verdict and
        returns; the proof is computed afterwards, on a worker thread;
      * a proof that RAISES is caught and reported as "could not run", never
        propagated into a request;
      * `done` is the one place that waits, because it is one deliberate
        keystroke, and even there a proof that could not RUN only warns.

    MEASURED on the five completion rows: 0.18-0.47 s per proof (Mahler's
    38-part truth 0.35-0.47 s, Bach 0.18 s). Fast enough that the worker is
    finished before the next keystroke lands, and far too slow to sit on
    `/api/index`, which would pay it five times on every page load.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._done: dict = {}          # fingerprint -> result
        self._running: set = set()

    @staticmethod
    def fingerprint(row_id: str, staves) -> str:
        body = json.dumps([[s.get("name"), list(s.get("parts") or [])]
                           for s in staves], sort_keys=True)
        return f"{row_id}:{hashlib.sha256(body.encode()).hexdigest()[:16]}"

    def _compute(self, row_id: str, staves, source_reference) -> dict:
        t0 = time.time()
        try:
            res = prove_normalises(row_id, staves,
                                   source_reference=source_reference)
        except Exception as exc:                       # noqa: BLE001
            # ⚠️ The prover itself failing is NOT the map being wrong.
            res = {"ok": False, "unavailable": True, "normalised": None,
                   "problem": f"the normalisation check could not run: "
                              f"{type(exc).__name__}: {exc}"}
        res["state"] = "ok" if res["ok"] else (
            "unavailable" if res.get("unavailable") else "refused")
        res["seconds"] = round(time.time() - t0, 3)
        return res

    def peek(self, row_id: str, staves, source_reference=None) -> dict:
        """The cached proof, or `checking` — and start one if none is running.

        Never blocks. The browser re-reads the row when it sees `checking`.
        """
        fp = self.fingerprint(row_id, staves)
        with self._lock:
            hit = self._done.get(fp)
            if hit is not None:
                return hit
            if fp in self._running:
                return {"state": "checking", "ok": None, "problem": None}
            self._running.add(fp)
        snapshot = [{"name": s.get("name"), "parts": list(s.get("parts") or [])}
                    for s in staves]

        def work() -> None:
            res = self._compute(row_id, snapshot, source_reference)
            with self._lock:
                self._done[fp] = res
                self._running.discard(fp)

        threading.Thread(target=work, daemon=True).start()
        return {"state": "checking", "ok": None, "problem": None}

    def wait(self, row_id: str, staves, source_reference=None,
             timeout_s: float = 20.0) -> dict:
        """The proof, computing it here if it is not cached. Used by `done`."""
        fp = self.fingerprint(row_id, staves)
        deadline = time.time() + timeout_s
        while True:
            with self._lock:
                hit = self._done.get(fp)
                running = fp in self._running
            if hit is not None:
                return hit
            if not running:
                snapshot = [{"name": s.get("name"),
                             "parts": list(s.get("parts") or [])}
                            for s in staves]
                res = self._compute(row_id, snapshot, source_reference)
                with self._lock:
                    self._done[fp] = res
                return res
            if time.time() > deadline:
                return {"state": "unavailable", "ok": False, "unavailable": True,
                        "problem": "the normalisation check did not finish in "
                                   f"{timeout_s:.0f}s — merge_additions will "
                                   "still check before anything is written"}
            time.sleep(0.05)


def done_problems(validation: dict, proof: dict) -> list[str]:
    """What still blocks `done`. The structural problems, plus a REFUSED proof.

    ⚠️ A proof that could not RUN does not block, and that asymmetry is
    deliberate — see `merge_additions.prove_normalises`. A missing fixture on
    this machine is not evidence about the map, and `merge_additions` refuses
    on it anyway before anything reaches `works.json`.
    """
    out = list(validation.get("problems") or [])
    if proof.get("state") == "refused" and proof.get("problem"):
        out.append(proof["problem"])
    return out


class StaffPatch(BaseModel):
    # ⚠️ `Optional[...]`, not `str | None`: the host is Python 3.9 and pydantic
    # evaluates these annotations at runtime, where PEP 604 does not exist.
    name: Optional[str] = None
    parts: Optional[List[int]] = None
    verdict: Optional[str] = None


def create_app(cache: Path, out: Path) -> FastAPI:
    index = json.loads((cache / "index.json").read_text())
    seeds = {r["row_id"]: r for r in index["rows"]}
    # ⚠️ THE CROP ORIGIN IS SHIPPED, NOT RE-DERIVED IN THE BROWSER. The overlay
    # used to recompute it in JavaScript under a comment claiming it was "the
    # same arithmetic build_cache.py used" — a reimplementation, and the shape
    # `prove_normalises` exists to prevent. Stamped here rather than baked into
    # the cache so an existing cache needs no rebuild.
    for _r in seeds.values():
        for _sys in _r.get("detected", {}).get("systems", []):
            if _sys.get("staves"):
                _sys["crop"] = strip_crop_geometry(_sys["staves"])
    store = Store(out)
    prover = Prover()

    app = FastAPI(title="staves-map confirmation")

    def seed_or_404(row_id: str) -> dict:
        if row_id not in seeds:
            raise HTTPException(404, f"no cached row {row_id}")
        return seeds[row_id]

    def check(seed: dict, st: dict, *, prove: bool = True) -> dict:
        conflicts = (seed["proposal"].get("conflicts") or [])
        # Only a lineup DIFFERENCE needs acknowledging. A system that merely
        # suppresses staves (p.3's 8 against 11) is a subset of the chosen
        # lineup and the map covers it exactly; there is nothing to choose.
        needs = any(c.get("staves_only_in_this_system") for c in conflicts)
        v = validate(st, seed["reference"]["n_parts_music21"], needs_ack=needs)
        if prove:
            # NON-BLOCKING. `peek` returns the cached proof or `checking` and
            # starts a worker; it never runs page_normalise on the request
            # thread, so a verdict is stored and answered at the speed it
            # always was.
            v["normalise"] = prover.peek(
                seed["row_id"], st["staves"],
                source_reference=seed["reference"].get("catalog_path"))
            v["ok_to_finish"] = not done_problems(v, v["normalise"])
        return v

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return PAGE

    @app.get("/api/index")
    def api_index() -> dict:
        rows = []
        for r in index["rows"]:
            st = store.row(r["row_id"], r)
            v = check(r, st, prove=False)   # five proofs per page load: no
            rows.append({
                "row_id": r["row_id"], "label": r["label"],
                "usable": r["usable"], "blocking": r.get("blocking", False),
                "status": st["status"], "decided": v["decided"],
                "n_staves": v["n_staves"], "unnamed": len(v["unnamed"]),
                "n_detected_staves": r["detected"]["n_staves"],
            })
        return {"rows": rows, "out": str(out),
                "cache": str(cache),
                "generated_at": index.get("generated_at")}

    @app.get("/api/row/{row_id}")
    def api_row(row_id: str) -> dict:
        seed = seed_or_404(row_id)
        st = store.row(row_id, seed)
        return {"seed": seed, "state": st,
                "validation": check(seed, st)}

    @app.patch("/api/row/{row_id}/staff/{k}")
    def api_patch(row_id: str, k: int, patch: StaffPatch) -> dict:
        seed = seed_or_404(row_id)
        st = store.row(row_id, seed)
        if not 0 <= k < len(st["staves"]):
            raise HTTPException(400, f"staff {k} out of range")
        s = st["staves"][k]
        if patch.name is not None:
            s["name"] = patch.name
        if patch.parts is not None:
            # ⚠️ DE-DUPLICATE, DO NOT SORT. `page_normalise` keeps `parts[0]`,
            # so the order chooses which reference part the merged staff IS.
            # Sorting a map whose first entry carries tacet folds renames the
            # printed staff after the silent folded part — measured on the
            # 2026-09-07 pass, `Zwei Fagotte.` came back as `Piccolo`. Keep
            # the order the human gave; only drop repeats.
            s["parts"] = list(dict.fromkeys(patch.parts))
        if patch.verdict is not None:
            s["verdict"] = patch.verdict
        elif patch.name is not None or patch.parts is not None:
            prop = s.get("proposed") or {}
            same = (s["name"] == prop.get("name")
                    and s["parts"] == list(dict.fromkeys(
                        prop.get("parts") or [])))
            s["verdict"] = "confirmed" if same else "edited"
        # Any change reopens the row: `done` is a claim about the current map.
        if st["status"] == "done":
            st["status"] = "in_progress"
            st.pop("confirmed_at", None)
        store.save()
        return {"state": st,
                "validation": check(seed, st)}

    @app.post("/api/row/{row_id}/staff/{k}/insert")
    def api_insert(row_id: str, k: int) -> dict:
        seed = seed_or_404(row_id)
        st = store.row(row_id, seed)
        st["staves"].insert(min(k + 1, len(st["staves"])),
                            {"name": "", "parts": [], "proposed": None,
                             "verdict": "pending", "added_by_hand": True})
        st["status"] = "in_progress"
        store.save()
        return {"state": st,
                "validation": check(seed, st)}

    @app.delete("/api/row/{row_id}/staff/{k}")
    def api_delete(row_id: str, k: int) -> dict:
        seed = seed_or_404(row_id)
        st = store.row(row_id, seed)
        if not 0 <= k < len(st["staves"]):
            raise HTTPException(400, f"staff {k} out of range")
        st["staves"].pop(k)
        st["status"] = "in_progress"
        store.save()
        return {"state": st,
                "validation": check(seed, st)}

    @app.post("/api/row/{row_id}/accept_all")
    def api_accept_all(row_id: str) -> dict:
        seed = seed_or_404(row_id)
        st = store.row(row_id, seed)
        for s in st["staves"]:
            if s["verdict"] == "pending":
                s["verdict"] = "confirmed"
        store.save()
        return {"state": st,
                "validation": check(seed, st)}

    @app.post("/api/row/{row_id}/reset")
    def api_reset(row_id: str) -> dict:
        seed = seed_or_404(row_id)
        store.doc["rows"].pop(row_id, None)
        store.save()
        st = store.row(row_id, seed)
        return {"state": st,
                "validation": check(seed, st)}

    @app.post("/api/row/{row_id}/done")
    def api_done(row_id: str) -> JSONResponse:
        seed = seed_or_404(row_id)
        st = store.row(row_id, seed)
        v = check(seed, st, prove=False)
        # ⚠️ THE ONE PLACE THAT WAITS. `done` is a single deliberate
        # keystroke, so the proof is computed here if the worker has not
        # already cached it — the same proof `merge_additions` runs.
        v["normalise"] = prover.wait(
            row_id, st["staves"],
            source_reference=seed["reference"].get("catalog_path"))
        problems = done_problems(v, v["normalise"])
        v["ok_to_finish"] = not problems
        if problems:
            # ⚠️ REFUSE. A half-finished map that reads as finished is worse
            # than no map: page_normalise would raise on it, or worse, quietly
            # normalise against a part list that is missing evidence.
            v = dict(v, ok=False, problems=problems)
            return JSONResponse(
                status_code=409,
                content={"error": "refusing to mark this page done",
                         "validation": v, "state": st})
        st["status"] = "done"
        st["confirmed_at"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds")
        # ⚠️ THE WORKS.JSON SHAPE, FROM `staves_schema` — the UI's own
        # bookkeeping (`proposed`, `verdict`, `adopted_from`) is dropped and a
        # hand-read fact about the engraving is KEPT. Both halves matter: the
        # old hand-written `{name, parts}` did the first and not the second.
        st["staves_for_works_json"] = [
            staves_schema.project(s)[0] for s in st["staves"]]
        store.save()
        return JSONResponse({"state": st, "validation": v})

    @app.post("/api/row/{row_id}/adopt")
    def api_adopt(row_id: str) -> JSONResponse:
        """Take the twin scan's finished decision wholesale.

        The 575951 rows are the SAME LITOLFF PLATE as the 984073 rows — their
        `systems_as_printed` is literally `same-as:` the twin, and the p.3
        window's own `verified_by` records a barline fingerprint with ZERO
        unmatched boundaries on either side and max normalised disagreement
        0.0013.  So the map is the same map, and re-deciding it staff by staff
        would be typing, not reading.

        ⚠️ It is still ADOPTED, not assumed: this row's own 600 dpi crops are
        rendered from its own PDF and stay on screen, so the adoption is
        checked against this scan's ink rather than the twin's.
        """
        seed = seed_or_404(row_id)
        twin_id = seed.get("same_as")
        if not twin_id:
            return JSONResponse(status_code=409, content={
                "error": "this row is not a `same-as` twin of another"})
        twin = store.doc["rows"].get(twin_id)
        if not twin or twin.get("status") != "done":
            return JSONResponse(status_code=409, content={
                "error": f"finish {twin_id} first — there is nothing to adopt"})
        st = store.row(row_id, seed)
        # Same plate, so the same map INCLUDING its `lines` / `printed_staves`
        # facts — adopting only `{name, parts}` would silently hand the twin a
        # different lineup from the one that was confirmed.
        st["staves"] = [
            dict(staves_schema.project(s)[0],
                 proposed=s.get("proposed"), verdict=s["verdict"],
                 adopted_from=twin_id)
            for s in twin["staves"]]
        st["adopted_from"] = twin_id
        st["adopted_note"] = (
            "same Litolff plate as the twin; works.json already defers this "
            "row's systems_as_printed to it with `same-as:`")
        if twin.get("lineup_conflict_acknowledged"):
            st["lineup_conflict_acknowledged"] = True
            st["lineup_chosen"] = twin.get("lineup_chosen")
        store.save()
        return JSONResponse({"state": st, "validation": check(seed, st)})

    @app.post("/api/row/{row_id}/ack")
    def api_ack(row_id: str) -> dict:
        seed = seed_or_404(row_id)
        st = store.row(row_id, seed)
        st["lineup_conflict_acknowledged"] = \
            not st.get("lineup_conflict_acknowledged")
        if st["lineup_conflict_acknowledged"]:
            st["lineup_conflict"] = seed["proposal"].get("conflicts")
            st["lineup_chosen"] = seed["proposal"].get("source")
        store.save()
        return {"state": st, "validation": check(seed, st)}

    @app.post("/api/row/{row_id}/undone")
    def api_undone(row_id: str) -> dict:
        seed = seed_or_404(row_id)
        st = store.row(row_id, seed)
        st["status"] = "in_progress"
        st.pop("confirmed_at", None)
        store.save()
        return {"state": st,
                "validation": check(seed, st)}

    @app.get("/img/{row_id}/{name}")
    def img(row_id: str, name: str) -> FileResponse:
        p = (cache / row_id / name).resolve()
        if cache.resolve() not in p.parents or not p.is_file():
            raise HTTPException(404, name)
        return FileResponse(p)

    return app


# ---------------------------------------------------------------------- page

PAGE = r"""
<meta charset="utf-8"><title>staves map — confirm</title>
<style>
:root{--bg:#14161a;--fg:#e8e8ea;--dim:#9aa0a8;--ok:#4ec97b;--edit:#e8b64c;
      --bad:#e2624c;--line:#2a2e35;--pan:#1b1e24;--sel:#3d6fd6;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
     font:13px/1.45 -apple-system,Segoe UI,Helvetica,sans-serif}
header{padding:6px 12px;border-bottom:1px solid var(--line);display:flex;
       gap:14px;align-items:center;flex-wrap:wrap;background:var(--pan)}
header b{font-size:14px}
.tab{padding:3px 9px;border:1px solid var(--line);border-radius:4px;
     cursor:pointer;white-space:nowrap}
.tab.on{background:var(--sel);border-color:var(--sel)}
.tab .n{color:var(--dim);font-size:11px;margin-left:5px}
.tab.done{border-color:var(--ok)}
main{display:grid;grid-template-columns:230px 1fr 300px;height:calc(100vh - 46px)}
.col{overflow:auto;padding:8px}
.col+.col{border-left:1px solid var(--line)}
#strips img{width:100%;display:block;background:#fff}
.stripbox{position:relative;margin-bottom:2px}
.stripbox .here{position:absolute;left:0;right:0;display:none;pointer-events:none;
  border:2px solid #ffd24a;background:rgba(255,210,74,.22);border-radius:2px}
.staffrow{display:flex;gap:7px;align-items:flex-start;padding:5px 6px;
          border:1px solid var(--line);border-radius:4px;margin-bottom:5px;
          cursor:pointer}
.staffrow.cur{border-color:var(--sel);background:#20263a}
/* A printed staff the REFERENCE cannot represent. Shown so the list can be
   counted against the page, never selectable: it is not a map entry and
   `page_normalise` refuses an entry naming no part. */
.staffrow.unrep{cursor:default;opacity:.62;border-style:dashed;
                background:repeating-linear-gradient(135deg,
                  transparent 0 6px, rgba(255,255,255,.03) 6px 12px)}
.staffrow.unrep .nm{font-weight:500;font-style:italic}
.staffrow.unrep .pp{color:#8a8f98}
.staffrow .k{width:20px;color:var(--dim);text-align:right;flex:none}
.staffrow .nm{flex:1;font-weight:600}
.staffrow .pp{color:var(--dim);font-variant-numeric:tabular-nums}
.v-pending{color:var(--dim)} .v-confirmed{color:var(--ok)} .v-edited{color:var(--edit)}
.dot{flex:none;width:9px;height:9px;border-radius:50%;margin-top:5px;
     background:#4a4f58}
.dot.confirmed{background:var(--ok)} .dot.edited{background:var(--edit)}
img.crop{width:100%;background:#fff;display:block;border-radius:3px;
  margin-bottom:8px}
#cropwrap{background:var(--pan);padding-bottom:6px}
.inst{color:var(--dim);font-size:11.5px;margin:2px 0 3px}
.inst b{color:var(--fg)}
.part{display:flex;gap:6px;padding:2px 5px;border-radius:3px;cursor:pointer;
      font-variant-numeric:tabular-nums}
.part:hover{background:#252a33}
.part .i{width:22px;color:var(--dim);text-align:right}
.part.here{background:#2b3d5c}
.part.free{color:var(--bad)}
.part .own{color:var(--dim);font-size:11px;margin-left:auto}
h3{margin:10px 0 5px;font-size:11px;letter-spacing:.09em;color:var(--dim);
   text-transform:uppercase}
#status{margin-left:auto;display:flex;gap:12px;align-items:center}
.pill{padding:2px 8px;border-radius:10px;border:1px solid var(--line)}
.pill.ok{border-color:var(--ok);color:var(--ok)}
.pill.bad{border-color:var(--bad);color:var(--bad)}
button{background:#262b34;color:var(--fg);border:1px solid var(--line);
       border-radius:4px;padding:3px 10px;cursor:pointer;font:inherit}
button:hover{background:#30363f}
input{background:#0e1014;color:var(--fg);border:1px solid var(--sel);
      border-radius:3px;padding:3px 6px;font:inherit;width:100%}
.note{color:var(--dim);font-size:11.5px;white-space:pre-wrap}
.warn{color:var(--edit);border-left:2px solid var(--edit);padding-left:7px;
      margin:6px 0;font-size:11.5px}
.err{color:var(--bad);border-left:2px solid var(--bad);padding-left:7px;
     margin:6px 0;font-size:11.5px}
kbd{background:#0e1014;border:1px solid var(--line);border-radius:3px;
    padding:0 4px;font-size:11px}
#keys{color:var(--dim);font-size:11px}
#banner{display:none;background:#3a1c19;color:#ffb9a8;border-bottom:1px solid
  var(--bad);padding:5px 12px;font-weight:600}
</style>
<header>
  <b>staves map</b>
  <div id="tabs" style="display:flex;gap:6px;flex-wrap:wrap"></div>
  <div id="status"></div>
</header>
<div id="banner"></div>
<main>
  <div class="col" id="strips"></div>
  <div class="col">
    <div id="cropwrap"></div>
    <div id="editor"></div>
    <div id="list"></div>
    <div id="keys">
      <kbd>t</kbd> confirm &amp; next · <kbd>f</kbd> edit parts ·
      <kbd>n</kbd> edit name · <kbd>u</kbd> un-decide ·
      <kbd>Tab</kbd>/<kbd>&#8679;Tab</kbd> next/prev ·
      <kbd>A</kbd> confirm all remaining · <kbd>+</kbd> add staff ·
      <kbd>&#8998;</kbd> delete staff · <kbd>k</kbd> acknowledge a lineup
      difference · <kbd>d</kbd> mark page done ·
      click a part on the right to toggle it onto this staff
    </div>
  </div>
  <div class="col" id="right"></div>
</main>
<script>
let IDX=null, ROW=null, DATA=null, CUR=0, EDITING=null;
// ⚠️ A confirmation tool is used by someone holding `t` down. Two patches can
// be in flight at once, and the SECOND server reply can be the OLDER state —
// which would silently un-confirm a staff the human just decided. So every
// mutation takes a sequence number and only the newest reply is applied; the
// UI moves optimistically in the meantime so the keystrokes never feel laggy.
let SEQ=0;
const $=s=>document.querySelector(s);

async function j(u,o){const r=await fetch(u,o);
  const b=await r.json().catch(()=>({}));return {ok:r.ok,status:r.status,body:b};}

async function loadIndex(){const r=await j('/api/index');IDX=r.body;drawTabs();}

function drawTabs(){
  $('#tabs').innerHTML='';
  IDX.rows.forEach(r=>{
    const d=document.createElement('div');
    d.className='tab'+(r.row_id===ROW?' on':'')+(r.status==='done'?' done':'');
    d.innerHTML=r.row_id.replace('-mvt1','')+
      '<span class="n">'+r.decided+'/'+r.n_staves+
      (r.status==='done'?' ✓':'')+'</span>';
    d.onclick=()=>load(r.row_id);
    $('#tabs').appendChild(d);
  });
}

async function load(id){
  ROW=id;const r=await j('/api/row/'+id);DATA=r.body;CUR=firstPending();
  await loadIndex();draw();
}

// The proof runs on a worker thread, so the first answer for a changed map is
// `checking`. Re-read the row once it should be ready, and redraw ONLY the
// proof's own panel state — never the verdicts, which are already saved.
let PROOF_T=null;
async function refreshProof(){
  const at=ROW;
  const r=await j('/api/row/'+at);
  if(at!==ROW)return;                       // Sean moved on; drop the answer
  if(r.ok&&r.body&&r.body.validation)DATA.validation=r.body.validation;
  draw();
}
function firstPending(){
  const i=DATA.state.staves.findIndex(s=>s.verdict==='pending');
  return i<0?0:i;
}

function draw(){
  const seed=DATA.seed,st=DATA.state,v=DATA.validation;
  // ---- strips
  const strips=$('#strips');strips.innerHTML='<h3>the page, as detected</h3>';
  const psys=proposalSystemIndex(seed);
  Object.keys(seed.images.systems).sort().forEach(k=>{
    const box=document.createElement('div');box.className='stripbox';
    const img=document.createElement('img');
    img.src='/img/'+ROW+'/'+seed.images.systems[k];
    img.title='system '+k;box.appendChild(img);
    const cap=document.createElement('div');cap.className='note';
    // ⚠️ SAY WHY THERE IS NO MARKER. The overlay abstains wherever the join
    // cannot place this slot's band, which is right — it used to point at the
    // wrong staff instead — but an unexplained absence reads as a broken tool.
    const inst0=instancesFor(CUR,seed).find(x=>x.system===Number(k));
    const why=(inst0&&!inst0.printed)
      ? '  — slot '+CUR+' is not marked here: '+(inst0.name
          ? inst0.name : 'no staff of this system carries its parts')
      : '';
    cap.textContent='system '+(Number(k)+1)+
      (Number(k)===psys?'  — the proposal is this system\u2019s lineup':'')+why;
    const hl=document.createElement('div');hl.className='here';box.appendChild(hl);
    strips.appendChild(box);strips.appendChild(cap);
    // Every system that PRINTS this slot is marked, not only the proposal's —
    // the join is per system and abstains on its own where it cannot place the
    // band, so there is nothing left for a psys guard to protect against.
    const sysi=Number(k);
    const place=()=>placeHighlight(img,hl,seed.detected.systems[sysi],CUR,
                                   seed,sysi);
    img.complete?place():img.onload=place;
  });
  const nn=document.createElement('div');nn.className='note';
  nn.textContent=seed.n_staves_note||'';strips.appendChild(nn);

  // ---- header status
  const need=v.unnamed.length?('<span class="pill bad">'+v.unnamed.length+
      ' part(s) unassigned: '+v.unnamed.join(', ')+'</span>')
    :'<span class="pill ok">all '+v.n_parts+' parts named</span>';
  const dbl=v.doubled.length?'<span class="pill bad">part named twice: '+
      v.doubled.join(', ')+'</span>':'';
  const seen=instancesFor(CUR,seed).filter(x=>x.printed).length;
  const totInst=seed.detected.n_staves;
  const ack=v.needs_ack?('<span class="pill '+(v.acknowledged?'ok':'bad')+
    '" style="cursor:pointer" id="ackpill">'+(v.acknowledged?
      'lineup choice acknowledged':'systems differ — acknowledge (k)')+
    '</span>'):'';
  const twin=seed.same_as?('<span class="pill" id="adoptpill" '+
    'style="cursor:pointer">'+(st.adopted_from?'adopted from the twin':
    'same plate as '+seed.same_as.replace('beethoven-sym5-mvt1-','')+
    ' — adopt its decision (y)')+'</span>'):'';
  $('#status').innerHTML='<span class="pill">'+v.decided+'/'+v.n_staves+
    ' slots decided</span>'+twin+
    '<span class="pill">'+totInst+' printed staves on this page · '+
    seen+' show this slot</span>'+need+dbl+ack+
    '<button onclick="markDone()">'+(st.status==='done'?
      'page ✓ done (click to reopen)':'mark page done (d)')+'</button>';
  $('#status').querySelector('button').onclick=
    st.status==='done'?reopen:markDone;
  if($('#ackpill'))$('#ackpill').onclick=ackConflict;
  if($('#adoptpill'))$('#adoptpill').onclick=adoptTwin;
  $('#banner').textContent=BANNER;
  $('#banner').style.display=BANNER?'block':'none';

  // ---- EVERY printed instance of this slot, one crop per system
  const W=$('#cropwrap');W.innerHTML='';
  const inst=instancesFor(CUR,seed);
  inst.forEach(x=>{
    const cap=document.createElement('div');cap.className='inst';
    cap.innerHTML='<b>system '+(x.system+1)+'</b> '+
      (x.printed?('· printed as <b>'+x.name+'</b> · detected staff #'+
                  x.staff_index+' of the page')
                : '· <i>not printed in this system</i> (tacet-suppressed)');
    W.appendChild(cap);
    if(x.printed){
      const img=document.createElement('img');img.className='crop';
      img.src='/img/'+ROW+'/'+seed.images.staves[x.staff_index];
      W.appendChild(img);
    }
  });

  // ---- staff list
  const L=$('#list');L.innerHTML='<h3>printed staves of this page — '+
    'the map, one entry per staff</h3>';
  // Printed staves the REFERENCE cannot represent, keyed by the mapped staff
  // they are printed BELOW. They are NOT map entries -- they carry no index,
  // are not selectable, and never enter st.staves -- but they are printed, so
  // omitting them makes the list uncountable against the page.
  const UNREP=((seed.proposal||{}).unrepresentable_printed_staves||[])
    .map(u=>(typeof u==='string'?{name:u,after:undefined,reason:''}:u));
  const unrepAfter=(nm)=>UNREP.filter(u=>u.after===nm);
  const addUnrep=(u)=>{
    const d=document.createElement('div');
    d.className='staffrow unrep';
    d.innerHTML='<div class="dot"></div>'+
      '<div class="k">—</div>'+
      '<div class="nm">'+u.name+
        '<div class="note">printed on this page; the reference has no part '+
        'for it, so it is not a map entry'+
        (u.lines===1?' · 1-line staff':'')+'</div></div>'+
      '<div class="pp">n/a<br><span style="font-size:11px">unmappable</span></div>';
    d.title=u.reason||'';
    L.appendChild(d);
  };
  // one printed above every mapped staff
  UNREP.filter(u=>u.after===null).forEach(addUnrep);
  st.staves.forEach((s,k)=>{
    const d=document.createElement('div');
    d.className='staffrow'+(k===CUR?' cur':'');
    const prop=s.proposed?('proposed '+(s.proposed.parts||[]).join(', ')):'added by hand';
    // A one-line percussion rule and a grand staff are facts about the
    // ENGRAVING that ride into works.json and decide the arity gate there.
    // They were invisible here while they were being confirmed, which is how
    // a lineup could be confirmed staff by staff and still be wrong about
    // what the page prints.
    const shape=(s.lines===1?' · 1-line staff':'')+
      (s.printed_staves>1?(' · '+s.printed_staves+' printed staves'):'');
    d.innerHTML='<div class="dot '+s.verdict+'"></div>'+
      '<div class="k">'+k+'</div>'+
      '<div class="nm">'+(s.name||'<i style="color:#e2624c">unnamed</i>')+
        '<div class="note">'+prop+shape+'</div></div>'+
      '<div class="pp v-'+s.verdict+'">'+(s.parts.length?s.parts.join(' '):'—')+
        '<br><span style="font-size:11px">'+s.verdict+'</span></div>';
    d.onclick=()=>{CUR=k;EDITING=null;draw();};
    L.appendChild(d);
    unrepAfter(s.name).forEach(addUnrep);
  });
  // An entry whose `after` names no staff of this map would vanish silently,
  // which is the fault this whole block exists to fix. Show it at the foot.
  {const placed=new Set(st.staves.map(s=>s.name));
   UNREP.filter(u=>u.after!==null&&u.after!==undefined&&!placed.has(u.after))
        .forEach(addUnrep);}

  // ---- warnings / conflicts / provenance
  (seed.warnings||[]).forEach(w=>{
    const e=document.createElement('div');e.className='warn';e.textContent='⚠ '+w;
    L.appendChild(e);});
  (v.problems||[]).forEach(p=>{
    const e=document.createElement('div');e.className='err';e.textContent=p;
    L.appendChild(e);});

  // ---- WOULD IT MERGE? the same page_normalise proof merge_additions runs.
  // Shown while Sean works, not at the end: the whole point is that a row
  // which cannot merge says so before the pass is spent on it.
  const nm=v.normalise;
  if(nm){
    const e=document.createElement('div');
    if(nm.state==='checking'){
      e.className='note';e.textContent='… checking this map against '+
        'page_normalise';
      // one poll; the proof is 0.2-0.5s and the worker is already running
      clearTimeout(PROOF_T);PROOF_T=setTimeout(refreshProof,400);
    }else if(nm.state==='ok'){
      e.className='note';e.style.color='#7fd18c';
      const n=nm.normalised||{};
      e.textContent='✓ this map NORMALISES — '+n.n_source_parts+
        ' reference parts → '+n.n_output_parts+' printed staves'+
        ' (divisi '+(n.divisi_share!==undefined?n.divisi_share:'?')+')'+
        '. merge_additions will accept it.';
    }else if(nm.state==='refused'){
      e.className='err';
      e.textContent='✗ WOULD NOT MERGE — '+nm.problem;
    }else{
      e.className='warn';
      e.textContent='⚠ the merge check could not run here — '+(nm.problem||'')+
        '. Your verdicts are saved; merge_additions still checks before '+
        'anything is written.';
    }
    L.appendChild(e);
  }
  const p=seed.proposal;
  const prov=document.createElement('div');prov.className='note';
  prov.textContent='PROPOSAL: '+p.source+' of '+p.n_systems+
    ' — the system whose lineup names the most reference parts.\n'+
    (p.conflicts||[]).map(c=>'⚠ '+c.system+' disagrees: staves only there = ['+
      c.staves_only_in_this_system.join(', ')+'], parts only there = ['+
      c.parts_this_system_names_that_the_proposal_does_not.join(', ')+']').join('\n')+
    '\nbands from '+seed.detected.artefact_origin+
    ' — '+seed.detected.artefact.split('/').pop()+
    '\npart indices from '+seed.reference.source.split('/').pop()+
    ' ('+seed.reference.n_parts_music21+' music21 parts, '+
    seed.reference.n_parts_score_part_elements+' <score-part> elements)';
  L.appendChild(prov);

  drawEditor();drawParts();
}

function proposalSystemIndex(seed){
  const n=(seed.proposal.source||'system_1').replace('system_','');
  const i=parseInt(n,10)-1;
  return (i>=0&&i<seed.detected.systems.length)?i:0;
}

function placeHighlight(img,hl,sys,k,seed,sysi){
  // ⚠️ THE BAND IS FOUND BY PARTS, NOT BY ORDINAL. `sys.staves[k]` indexes the
  // DETECTED bands by the MAP ENTRY's number, and those are different spaces
  // the moment a page's map is longer than its detected band list — which is
  // every Mahler page, because the one-line percussion rules are mapped and
  // only some are detected. Measured on p2: 21 map entries against 19 bands,
  // and entry 14 `Kleine Trommel` was marked on the band whose instrument is
  // `Violin`, 4416 page px away. `instancesFor` already does this join
  // correctly and ABSTAINS where the lineup and the detection disagree; the
  // overlay silently did not, which is the whole defect.
  //
  // ⚠️ The crop origin is READ, not recomputed — `sys.crop` comes from
  // build_cache.strip_crop_geometry, the one function that cut the strip.
  if(!img.naturalWidth||!sys||!sys.crop){hl.style.display='none';return;}
  const inst=instancesFor(k,seed).find(x=>x.system===sysi);
  if(!inst||!inst.printed){hl.style.display='none';return;}
  const st=sys.staves.find(b=>b.staff_index===inst.staff_index);
  if(!st){hl.style.display='none';return;}
  const yoff=sys.crop.y_off, div=sys.crop.divisor;
  // page px -> saved-strip px is /divisor; saved-strip px -> displayed px is
  // clientWidth/naturalWidth, because the strip is shown at width:100%.
  const s=(img.clientWidth/img.naturalWidth)/div;
  hl.style.display='block';
  hl.style.top =(img.offsetTop+(st.y0-yoff)*s-3)+'px';
  hl.style.height=Math.max(4,(st.y1-st.y0)*s+6)+'px';
}

function instancesFor(k,seed){
  // Every PRINTED instance of map entry k, one per system.
  //
  // ⚠️ The join is through the hand-read `systems_as_printed` lineups, by PARTS
  // — not by ordinal. On a page whose systems suppress staves, system 2's third
  // staff is not system 1's third staff, and pairing by position is exactly the
  // failure works.json records for brahms p.2 (a margin misread let a Trumpet
  // entry silently claim the Es-horn staff). A slot printed in no other system
  // is reported as suppressed, which is information, not a gap.
  const ent=DATA.state.staves[k];
  const want=new Set((ent&&ent.parts.length?ent.parts
                      :((ent&&ent.proposed&&ent.proposed.parts)||[])));
  const out=[];
  seed.systems_as_printed.forEach((sys,i)=>{
    const det=seed.detected.systems[i];
    let hit=-1;
    sys.staves.forEach((s,j)=>{
      if(hit<0&&s.parts.some(x=>want.has(x)))hit=j;
    });
    // Positional correspondence between the hand-read lineup and the detected
    // bands holds only where the two agree about how many staves the system
    // has; where they do not, say so rather than box the wrong staff.
    const aligned=det&&det.staves.length===sys.staves.length;
    if(hit>=0&&aligned)
      out.push({system:i,printed:true,name:sys.staves[hit].name,
                staff_index:det.staves[hit].staff_index});
    else if(hit>=0)
      out.push({system:i,printed:false,
                name:sys.staves[hit].name+' (lineup and detection disagree '+
                     'about this system: '+sys.staves.length+' read vs '+
                     (det?det.staves.length:0)+' detected)'});
    else out.push({system:i,printed:false,name:null});
  });
  return out;
}

function drawEditor(){
  const s=DATA.state.staves[CUR];const E=$('#editor');
  if(!s){E.innerHTML='';return;}
  if(EDITING==='parts'){
    E.innerHTML='<h3>parts on staff '+CUR+' — space or comma separated, '+
      'Enter to commit, Esc to cancel</h3>';
    const i=document.createElement('input');i.value=s.parts.join(' ');
    i.onkeydown=async ev=>{
      ev.stopPropagation();
      if(ev.key==='Enter'){
        const v=i.value.split(/[^0-9]+/).filter(x=>x!=='').map(Number);
        EDITING=null;await patch({parts:v});
      } else if(ev.key==='Escape'){EDITING=null;draw();}
    };
    E.appendChild(i);i.focus();i.select();return;
  }
  if(EDITING==='name'){
    E.innerHTML='<h3>printed name of staff '+CUR+
      ' — Enter to commit, Esc to cancel</h3>';
    const i=document.createElement('input');i.value=s.name;
    i.onkeydown=async ev=>{
      ev.stopPropagation();
      if(ev.key==='Enter'){EDITING=null;await patch({name:i.value.trim()});}
      else if(ev.key==='Escape'){EDITING=null;draw();}
    };
    E.appendChild(i);i.focus();i.select();return;
  }
  E.innerHTML='<h3>staff '+CUR+' of '+DATA.state.staves.length+' — <b>'+
    (s.name||'unnamed')+'</b> → parts '+(s.parts.join(', ')||'none')+
    ' — '+s.verdict+'</h3>';
}

function drawParts(){
  const R=$('#right');const seed=DATA.seed;
  const owner={};
  DATA.state.staves.forEach((s,k)=>s.parts.forEach(i=>{
    owner[i]=(owner[i]===undefined?String(k):owner[i]+','+k);}));
  R.innerHTML='<h3>reference parts — '+
    seed.reference.catalog_path.split('/').pop()+'</h3>';
  const cur=DATA.state.staves[CUR];
  seed.reference.parts.forEach(p=>{
    const d=document.createElement('div');
    const mine=cur&&cur.parts.includes(p.index);
    const free=owner[p.index]===undefined;
    d.className='part'+(mine?' here':'')+(free?' free':'');
    d.innerHTML='<div class="i">'+p.index+'</div><div>'+p.name+
      (p.abbrev?' <span style="color:#9aa0a8">('+p.abbrev+')</span>':'')+'</div>'+
      '<div class="own">'+(free?'unassigned':'staff '+owner[p.index])+'</div>';
    d.onclick=async()=>{
      if(!cur)return;
      const set=new Set(cur.parts);
      set.has(p.index)?set.delete(p.index):set.add(p.index);
      await patch({parts:[...set].sort((a,b)=>a-b)});
    };
    R.appendChild(d);
  });
  const w=document.createElement('div');w.className='note';
  w.style.marginTop='10px';
  w.textContent='window: reference measures '+seed.window.first_ref_measure+
    '–'+seed.window.last_ref_measure+' ('+seed.window.confidence+')';
  R.appendChild(w);
}

async function patch(p,k){
  BANNER='';
  const at=(k===undefined)?CUR:k;
  const mine=++SEQ;
  const r=await j('/api/row/'+ROW+'/staff/'+at,
    {method:'PATCH',headers:{'Content-Type':'application/json'},
     body:JSON.stringify(p)});
  if(mine!==SEQ)return;               // a newer patch already answered
  DATA.state=r.body.state;DATA.validation=r.body.validation;
  await loadIndex();draw();
}

async function verdict(v){
  const k=CUR;
  DATA.state.staves[k].verdict=v;                       // optimistic
  if(v!=='pending'&&k<DATA.state.staves.length-1)CUR=k+1;
  draw();
  await patch({verdict:v},k);
}

let BANNER='';
async function markDone(){
  const r=await j('/api/row/'+ROW+'/done',{method:'POST'});
  DATA.state=r.body.state||DATA.state;
  DATA.validation=r.body.validation||DATA.validation;
  // An inline banner, not an alert(): a modal steals the keyboard, and the
  // whole point of this tool is that the keyboard never leaves the human.
  BANNER=r.ok?'':('REFUSED — '+r.body.validation.problems.join(' · '));
  if(!r.ok&&r.body.validation&&r.body.validation.normalise&&
     r.body.validation.normalise.state==='refused'){
    BANNER+='   [this is the SAME check merge_additions runs before it '+
            'writes works.json — nothing you have decided is lost]';
  }
  await loadIndex();draw();
}
async function adoptTwin(){
  if(!DATA.seed.same_as){BANNER='this row is not a twin of another — nothing '+
    'to adopt';draw();return;}
  const r=await j('/api/row/'+ROW+'/adopt',{method:'POST'});
  if(!r.ok){BANNER=r.body.error;draw();return;}
  DATA.state=r.body.state;DATA.validation=r.body.validation;
  BANNER='';CUR=0;await loadIndex();draw();
}
async function ackConflict(){
  const r=await j('/api/row/'+ROW+'/ack',{method:'POST'});
  DATA.state=r.body.state;DATA.validation=r.body.validation;
  BANNER='';await loadIndex();draw();
}
async function reopen(){
  const r=await j('/api/row/'+ROW+'/undone',{method:'POST'});
  DATA.state=r.body.state;DATA.validation=r.body.validation;
  await loadIndex();draw();
}

document.addEventListener('keydown',async e=>{
  if(EDITING)return;
  if(e.target.tagName==='INPUT')return;
  const n=DATA?DATA.state.staves.length:0;
  if(e.key==='Tab'){e.preventDefault();
    CUR=(CUR+(e.shiftKey?-1:1)+n)%n;draw();return;}
  if(e.key==='t'){e.preventDefault();await verdict('confirmed');return;}
  if(e.key==='u'){e.preventDefault();await patch({verdict:'pending'});return;}
  if(e.key==='f'){e.preventDefault();EDITING='parts';drawEditor();return;}
  if(e.key==='n'){e.preventDefault();EDITING='name';drawEditor();return;}
  if(e.key==='A'){e.preventDefault();
    const r=await j('/api/row/'+ROW+'/accept_all',{method:'POST'});
    DATA.state=r.body.state;DATA.validation=r.body.validation;
    await loadIndex();draw();return;}
  if(e.key==='+'||e.key==='='){e.preventDefault();
    const r=await j('/api/row/'+ROW+'/staff/'+CUR+'/insert',{method:'POST'});
    DATA.state=r.body.state;DATA.validation=r.body.validation;CUR++;
    await loadIndex();draw();return;}
  if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();
    if(!confirm('delete map entry '+CUR+'?'))return;
    const r=await j('/api/row/'+ROW+'/staff/'+CUR,{method:'DELETE'});
    DATA.state=r.body.state;DATA.validation=r.body.validation;
    CUR=Math.min(CUR,DATA.state.staves.length-1);
    await loadIndex();draw();return;}
  if(e.key==='k'){e.preventDefault();await ackConflict();return;}
  if(e.key==='y'){e.preventDefault();await adoptTwin();return;}
  if(e.key==='d'){e.preventDefault();await markDone();return;}
});

(async()=>{await loadIndex();await load(IDX.rows[0].row_id);})();
</script>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    # 5050/5051/5052 belong to tools.omr.annotate — stay clear of them.
    ap.add_argument("--port", type=int, default=5075)
    ap.add_argument("--cache-dir", default=str(default_cache()))
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args(argv)

    cache = Path(args.cache_dir)
    if not (cache / "index.json").is_file():
        print(f"no cache at {cache}. Build it first:\n"
              f"  python3 {BENCH / 'build_cache.py'}", file=sys.stderr)
        return 2
    out = Path(args.out)
    print(f"  reads  {MAIN / 'benchmarks/omr-scan-e2e-2026-09/works.json'}")
    print(f"  reads  {cache}")
    print(f"  writes {out}")
    print(f"\n  http://{args.host}:{args.port}\n")
    uvicorn.run(create_app(cache, out), host=args.host, port=args.port,
                log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
