"""Real ink against its own null, through the registered decision.

⚠️ THE NULL IS A CIRCULAR SHIFT of each staff-bar's page x, which makes it the
STRONGER control: it keeps every within-staff interval and every chord exactly
as printed and destroys the PHASE alone. A re-draw would also destroy each
staff's own rhythmic spacing, so beating one would only show that music is not
uniform noise.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "_onset_harness", HERE / "run_on_transcription.py")
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)

from tools.omr.staged import adjudicate            # noqa: E402
from tools.omr.staged.record import Q              # noqa: E402

#: ⚠️ THE BANDS ARE TERTILES OF THE REAL ARM'S OWN DISTRIBUTION, NOT CONSTANTS.
#: A first cut used fixed cuts at 1 and 2 events per staff space and put ALL 51
#: bars in one bucket, reporting a density split that did not exist —
#: `events_per_space` is summed over every staff of the system, so on a
#: 14-staff page it is an order of magnitude above a per-staff figure. Bands
#: read off the data cannot be wrong about the data.
BAND_NAMES = ("sparse", "mid", "dense")


def _bars(doc, seed):
    log = H.build_log(doc, None, null_seed=seed)
    adjudicate.run(log, order=(Q.EVENT, Q.ONSET_COLUMN))
    bars, res = [], []
    for v in log.all_verdicts():
        if v.quantity != Q.ONSET_COLUMN or v.value is None:
            continue
        for b in v.value["bars"]:
            if "columns" not in b:
                continue
            bars.append(b)
            res += [c["residual_spaces"] for c in b["columns"]
                    if c["n_witness"] > 1]
    return bars, res


def _summarise(bars, res, edges):
    n_col = sum(b["n_columns"] for b in bars)
    n_cor = sum(b["n_corroborated"] for b in bars)
    by_band = {}
    for i, name in enumerate(BAND_NAMES):
        lo = edges[i]
        hi = edges[i + 1] if i + 1 < len(edges) else float("inf")
        sel = [b for b in bars
               if b["events_per_space"] is not None
               and (lo <= b["events_per_space"] < hi
                    or (i == len(BAND_NAMES) - 1
                        and b["events_per_space"] >= lo))]
        c = sum(b["n_columns"] for b in sel)
        by_band[name] = {
            "bars": len(sel), "columns": c,
            "corroborated": sum(b["n_corroborated"] for b in sel),
            "rate": round(sum(b["n_corroborated"] for b in sel) / c, 4) if c else None,
        }
    return {"bars": len(bars), "columns": n_col, "corroborated": n_cor,
            "rate": round(n_cor / n_col, 4) if n_col else None,
            "alone": sum(len(b["alone"]) for b in bars),
            "median_residual_spaces": round(statistics.median(res), 4) if res else None,
            "by_density": by_band}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("transcription", type=Path)
    ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2, 3, 4, 5])
    ap.add_argument("--json-out", type=Path, default=None)
    a = ap.parse_args()
    doc = json.loads(a.transcription.read_text())

    real_bars, real_res = _bars(doc, None)
    dens = sorted(b["events_per_space"] for b in real_bars
                  if b["events_per_space"] is not None)
    n = len(dens)
    edges = [0.0, dens[n // 3], dens[2 * n // 3]] if n >= 3 else [0.0, 0.0, 0.0]
    real = _summarise(real_bars, real_res, edges)
    nulls = []
    for s in a.seeds:
        nb, nr = _bars(doc, s)
        nulls.append(_summarise(nb, nr, edges))
    print(f"density tertiles (events per staff space, summed over the "
          f"system's staves): {edges[1]:.2f}, {edges[2]:.2f}\n")

    def band(arm, k, f="rate"):
        return arm["by_density"][k][f]

    print(f"REAL   columns {real['columns']:>5}  corroborated {real['corroborated']:>4} "
          f"({real['rate']:.3f})  alone {real['alone']:>5}  "
          f"median residual {real['median_residual_spaces']}")
    for s, n in zip(a.seeds, nulls):
        print(f"null {s} columns {n['columns']:>5}  corroborated {n['corroborated']:>4} "
              f"({n['rate']:.3f})  alone {n['alone']:>5}  "
              f"median residual {n['median_residual_spaces']}")
    nc = statistics.mean(n["columns"] for n in nulls)
    nr = statistics.mean(n["rate"] for n in nulls)
    na = statistics.mean(n["alone"] for n in nulls)
    print(f"\ncolumns needed:   real {real['columns']}  null {nc:.0f}  "
          f"({nc / real['columns']:.2f}x)")
    print(f"corroboration:    real {real['rate']:.3f}  null {nr:.3f}  "
          f"({real['rate'] / nr:.2f}x)")
    print(f"standing alone:   real {real['alone']}  null {na:.0f}  "
          f"({na / real['alone']:.2f}x)")
    print("\nby density (corroboration rate, real vs null mean):")
    for name in BAND_NAMES:
        rr, nn = band(real, name), [band(n, name) for n in nulls]
        nn = [x for x in nn if x is not None]
        if rr is None or not nn:
            print(f"  {name:<7} (no bars)")
            continue
        m = statistics.mean(nn)
        print(f"  {name:<7} bars {real['by_density'][name]['bars']:>3}  "
              f"real {rr:.3f}  null {m:.3f}  ({rr / m:.2f}x)")

    if a.json_out:
        a.json_out.parent.mkdir(parents=True, exist_ok=True)
        a.json_out.write_text(json.dumps(
            {"density_tertile_edges": edges, "real": real,
             "nulls": dict(zip(map(str, a.seeds), nulls))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
