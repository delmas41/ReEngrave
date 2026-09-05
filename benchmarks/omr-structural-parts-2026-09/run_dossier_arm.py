"""Price the dossier count source — a CEILING / REAL-USE arm, never a benchmark figure.

⚠️ Dossiers are generated from the same Gradus MusicXML the scan benchmark
scores against, so a dossier-fed figure measures what the pipeline does for
someone who can NAME their score, not what it does on an unknown page. Reported
separately and labelled, exactly as `orchestral_eval` handles dossier seeding.

Arms: base / dossier+stitch / cap2 / the two gates, to be read beside Phase 1's
oracle (−9,369), which is the ceiling a perfect count reaches.

MEASURED 2026-09-05, 20 rows:

    base                  0.8441  74,962         ES 17,520
    dossier + stitch      0.7007  71,507  −3,455  ES  5,894   5 rows REGRESS
    dossier cap2 + stitch 0.7205  71,803  −3,159  ES  9,765   5 rows regress
    gate_instr + stitch   0.7007  71,507  −3,455  ES  5,894   identical, no-op
    gate_system + stitch  0.7900  72,365  −2,597  ES 16,980   ZERO regressions

⚠️ THE INSTRUMENT GATE IS A PURE NO-OP — byte-for-byte the ungated arm on all
20 rows. What it refuses (Violin on beethoven p2, Contrabass/Bassoon on Mahler)
was never carrying a split. A gate that changes nothing is a result: the
per-instrument identity has no purchase on this corpus.

⚠️ THE SYSTEM GATE IS THE ONLY ARM THAT MAKES NO PAGE WORSE. It removes every
harm — dvorak p7 +1,501 → 0, mahler p3/p4/p5 +233/+660/+238 → 0, brahms p2
+198 → −216 — and pays with most of the Beethoven gain (p2 −1,423 → 0, p3
−1,054 → −9). 858 pooled edits to make the source incapable of regressing a
page.

⚠️ THAT TRADE READS DIFFERENTLY FOR A BENCHMARK AND FOR A USER. Pooled, −3,455
beats −2,597. But this is the REAL-USE path — someone transcribes a score they
can name, page by page — and a tool that silently makes one page 26% worse is
not paid for by two other pages improving.

⚠️ Zero regressions is an EMPIRICAL property of these 20 rows, not a guarantee
the identity provides. Brahms p1 sums exactly (21 = 21), passes the gate, and
keeps its horn over-count; the gate fires on dvorak p7 only because the
mis-read instrument's parts were already fully allocated, so the total
inflated. See `probe_sum_identity.py` — a sum cannot see a permutation.

FIXTURE PROVENANCE. 20-row transcriptions from
`.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`. The main checkout's `fixtures/` still holds
the ELEVEN-row era's `.restamp-composed` set.

    export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
    python3 benchmarks/omr-structural-parts-2026-09/run_dossier_arm.py --json arms20-dossier.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import omr_ned  # noqa: E402
from tools.omr.export import to_musicxml  # noqa: E402

_spec = importlib.util.spec_from_file_location("dc", HERE / "dossier_counts.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)

SUFFIX = ".reconciliation.omr.json"
ES = "entire staff insert/delete"
EM = "entire measure insert/delete"

#: arm -> (OMR_SLOT_STITCH, OMR_CONDENSED_PARTS, inject?, cap, gate)
#: gate "" none | "system" the system's assigned players must equal n_parts
#:              | "instr"  each instrument's assigned total must equal its parts
ARMS = {"base":                ("0", "0", False, 0, ""),
        "dossier_stitch":      ("1", "1", True,  0, ""),
        "dossier_cap2_stitch": ("1", "1", True,  2, ""),
        "gate_system_stitch":  ("1", "1", True,  0, "system"),
        "gate_instr_stitch":   ("1", "1", True,  0, "instr")}


def inject_dossier(result: dict, parts, cap: int = 0, gate: str = "",
                   dossier: dict | None = None) -> int:
    """Write `condensed_parts` from the work's parts/staves ratio.

    Abstains exactly where `dossier_counts.counts_for_system` abstains — an
    unreadable staff instrument, an instrument the dossier does not hold, or
    parts that do not divide evenly by the staves printed for them.

    `cap` > 0 REFUSES a split above that many players rather than clamping to
    it. Clamping would assert a count the evidence does not support; refusing
    forgoes a gain, which is the cheap direction — a split the reference does
    not make invents parts that pair with nothing, while a split withheld only
    leaves the row at baseline.
    """
    n_parts = int((dossier or {}).get("n_parts") or 0)
    n = 0
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            if not system.get("staves"):
                continue
            recs = dc.counts_for_system(system, parts)
            blocked: set[str] = set()
            if gate == "system":
                if sum(r["players"] for r in recs) != n_parts:
                    continue                      # the whole system abstains
            elif gate == "instr":
                by: dict[str, int] = {}
                for r in recs:
                    if r["instrument"]:
                        by[r["instrument"]] = by.get(r["instrument"], 0) + r["players"]
                blocked = {k for k, v in by.items() if v != parts.get(k, 0)}
            for staff, rec in zip(system["staves"], recs):
                if rec["abstained"] is not None or rec["players"] <= 1:
                    continue
                if cap and rec["players"] > cap:
                    continue
                if rec["instrument"] in blocked:
                    continue
                staff["condensed_parts"] = rec["players"]
                n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(dc.DEFAULT_FIXTURES))
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    fx, out = Path(args.fixtures), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = sorted(p.name[:-len(SUFFIX)] for p in fx.glob(f"*{SUFFIX}"))

    results: dict = {}
    cache: dict = {}
    for arm, (stitch, cond, use, cap, gate) in ARMS.items():
        os.environ["OMR_SLOT_STITCH"] = stitch
        os.environ["OMR_CONDENSED_PARTS"] = cond
        rowscores = []
        for r in rows:
            result = json.loads((fx / f"{r}{SUFFIX}").read_text())
            if use:
                dos = dc.dossier_for(r)
                if dos:
                    doc = json.loads((dc.DOSSIERS / f"{dos}.json").read_text())
                    parts, _ = dc.parts_by_instrument(doc)
                    inject_dossier(result, parts, cap, gate, doc)
            p = out / f"{r}.{arm}.musicxml"
            p.write_text(to_musicxml(result))
            key = f"{r}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
            if key not in cache:
                s = omr_ned.score_pair(pred=p, truth=fx / f"{r}.truth.musicxml",
                                       name=f"{r}.{arm}")
                cache[key] = {k: s[k] for k in ("omr_ned", "omr_ed",
                                                "pred_symbols", "truth_symbols")}
                cache[key]["categories"] = s.get("categories", {})
                print(f"  [{arm}] {r:<34} ned {s['omr_ned']:.4f} "
                      f"ed {s['omr_ed']}", flush=True)
            rowscores.append(dict(cache[key], row=r))
        ed = sum(x["omr_ed"] for x in rowscores)
        den = sum(x["pred_symbols"] + x["truth_symbols"] for x in rowscores)
        results[arm] = {"rows": rowscores, "pooled_omr_ed": ed,
                        "pooled_omr_ned": ed / den,
                        "ES": sum(x["categories"].get(ES, 0) for x in rowscores),
                        "EM": sum(x["categories"].get(EM, 0) for x in rowscores)}

    b = results["base"]
    print(f"\n{'arm':<16} {'OMR-NED':>9} {'edits':>8} {'Δ':>8} "
          f"{'ES':>7} {'ΔES':>7} {'EM':>7} {'ΔEM':>7}")
    for arm, rr in results.items():
        print(f"{arm:<16} {rr['pooled_omr_ned']:>9.4f} {rr['pooled_omr_ed']:>8} "
              f"{rr['pooled_omr_ed']-b['pooled_omr_ed']:>+8} {rr['ES']:>7} "
              f"{rr['ES']-b['ES']:>+7} {rr['EM']:>7} {rr['EM']-b['EM']:>+7}")

    other = [a for a in results if a != "base"]
    print(f"\n{'row':<34} {'base ed':>8} " + " ".join(f"{a:>20}" for a in other))
    for i, r in enumerate(rows):
        cells = " ".join(
            f"{results[a]['rows'][i]['omr_ed']-b['rows'][i]['omr_ed']:>+20}"
            for a in other)
        print(f"{r:<34} {b['rows'][i]['omr_ed']:>8} " + cells)

    print("\n⚠️ CEILING / REAL-USE ARM — dossiers derive from the same reference "
          "that scores the run.\n   Not a benchmark figure, and never quoted as "
          "one.")

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = HERE / dest
        dest.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
