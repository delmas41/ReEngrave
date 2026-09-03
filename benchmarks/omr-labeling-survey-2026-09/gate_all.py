"""Re-gate the shipping fine-tune: run BOTH axes (forgetting dense-recall +
hollow payoff) on a set of checkpoints, all on --device cpu, and print a
comparison table vs production.

  forgetting axis: tools.omr.training.wtc_forgetting_eval (CPU, imgsz 1280,
                   center match) — reports each ckpt AND production in one call.
  hollow axis:     benchmarks/omr-labeling-survey-2026-09/hollow_eval.py on
                   Beethoven 5 p.1 scan (scored vs reference), forced to CPU
                   via OMR_DEVICE=cpu.

Usage:
  python3 benchmarks/omr-labeling-survey-2026-09/gate_all.py \
     --prod omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
     --ckpt e4=<save_dir>/weights/epoch3.pt e6=<...>/epoch5.pt e8=<...>/epoch7.pt \
     --beet5-pdf <p1.pdf> --page 1
(ultralytics epochN.pt is 0-indexed: epoch3.pt == the 4th epoch.)
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

BENCH = Path("benchmarks/omr-labeling-survey-2026-09")
PRIMARY = Path("/Users/seanjohnson/Desktop/ReEngrave")
CELLS = PRIMARY / "benchmarks/omr-phase2.5/cells"
DETS = PRIMARY / "benchmarks/omr-phase3.4/detections-yolo-realft"
VERD = PRIMARY / "benchmarks/omr-phase3.4/verdicts-yolo-realft-ported"


def nh_recall(model_block):
    rc = model_block["rec_by_cat"].get("notehead", [0, 0])
    return (rc[0], rc[1], rc[0] / rc[1] if rc[1] else 0.0)


def run_forgetting(prod, ckpt, tag):
    out = BENCH / f"gate_forgetting_{tag}.json"
    cmd = [sys.executable, "-m", "tools.omr.training.wtc_forgetting_eval",
           "--prod", str(prod), "--ft", str(ckpt),
           "--cells-dir", str(CELLS), "--detections-dir", str(DETS),
           "--verdicts-dir", str(VERD), "--device", "cpu",
           "--imgsz", "1280", "--match", "center",
           "--json-out", str(out)]
    print(f"[forgetting {tag}] running ...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FORGETTING FAILED:\n", r.stdout[-1500:], r.stderr[-1500:]); return None
    d = json.loads(out.read_text())
    return d


def run_hollow(weights, tag, pdf, page):
    env = dict(os.environ, OMR_DEVICE="cpu")
    cmd = [sys.executable, str(BENCH / "hollow_eval.py"),
           "--weights", str(weights), "--tag", tag,
           "--pdf", str(pdf), "--page", str(page), "--stem", "beet5-p1", "--score"]
    print(f"[hollow {tag}] running ...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    print(r.stdout[-800:])
    if r.returncode != 0:
        print("HOLLOW FAILED:\n", r.stderr[-1500:]); return None
    jf = BENCH / f"hollow_eval_{tag}.json"
    return json.loads(jf.read_text()) if jf.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod", required=True)
    ap.add_argument("--ckpt", nargs="+", required=True, help="tag=path pairs")
    ap.add_argument("--beet5-pdf", required=True)
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--skip-forgetting", action="store_true")
    ap.add_argument("--skip-hollow", action="store_true")
    args = ap.parse_args()

    ckpts = []
    for pair in args.ckpt:
        tag, path = pair.split("=", 1)
        ckpts.append((tag, path))

    rows = []
    prod_forget = None
    prod_hollow = None

    if not args.skip_hollow:
        prod_hollow = run_hollow(args.prod, "prod", args.beet5_pdf, args.page)

    for tag, path in ckpts:
        if not Path(path).exists():
            print(f"!! missing checkpoint {tag}: {path}"); continue
        forget = None if args.skip_forgetting else run_forgetting(args.prod, path, tag)
        hollow = None if args.skip_hollow else run_hollow(path, tag, args.beet5_pdf, args.page)
        if forget and prod_forget is None:
            prod_forget = forget["production"]
        rows.append({"tag": tag, "path": path, "forget": forget, "hollow": hollow})

    # ---- table ----
    print("\n" + "=" * 100)
    print("RE-GATE SUMMARY (all evals --device cpu)")
    print("=" * 100)
    if prod_forget:
        pm, pt, pr = nh_recall(prod_forget)
        print(f"PRODUCTION forgetting: notehead recall {pm}/{pt}={pr:.3f}  "
              f"overallR={prod_forget['recall']:.3f} P={prod_forget['precision']:.3f} F1={prod_forget['f1']:.3f}")
    if prod_hollow:
        h = prod_hollow["hollow_histogram"]; p = prod_hollow.get("pooled", {})
        half = h.get("noteheadHalfInSpace", 0) + h.get("noteheadHalfOnLine", 0)
        wd = p.get("with_duration", {})
        print(f"PRODUCTION hollow: half={half} hollow_total={h.get('hollow_total',0)} "
              f"black={h.get('black_total',0)} with_dur_R={wd.get('recall')} exact_R={p.get('exact',{}).get('recall')}")
    print("-" * 100)
    hdr = f"{'ckpt':<8}{'nh_recall':>16}{'overallF1':>11}{'half':>6}{'hollowT':>9}{'black':>7}{'withDurR':>10}{'exactR':>9}{'stepR':>8}"
    print(hdr)
    for row in rows:
        tag = row["tag"]
        nh = ovf = "?"
        if row["forget"]:
            m, t, r = nh_recall(row["forget"]["fine_tuned"])
            nh = f"{m}/{t}={r:.3f}"
            ovf = f"{row['forget']['fine_tuned']['f1']:.3f}"
        half = ht = black = wd = ex = st = "?"
        if row["hollow"]:
            h = row["hollow"]["hollow_histogram"]; p = row["hollow"].get("pooled", {})
            half = h.get("noteheadHalfInSpace", 0) + h.get("noteheadHalfOnLine", 0)
            ht = h.get("hollow_total", 0); black = h.get("black_total", 0)
            wd = p.get("with_duration", {}).get("recall")
            ex = p.get("exact", {}).get("recall"); st = p.get("step", {}).get("recall")
        print(f"{tag:<8}{nh:>16}{ovf:>11}{str(half):>6}{str(ht):>9}{str(black):>7}{str(wd):>10}{str(ex):>9}{str(st):>8}")
    print("=" * 100)

    (BENCH / "gate_all_summary.json").write_text(json.dumps(
        {"production_forgetting": prod_forget, "production_hollow": prod_hollow,
         "rows": rows}, indent=2))
    print(f"wrote {BENCH/'gate_all_summary.json'}")


if __name__ == "__main__":
    main()
