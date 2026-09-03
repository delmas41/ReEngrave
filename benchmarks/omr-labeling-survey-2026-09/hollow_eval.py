"""Hollow-payoff eval: transcribe a real scan page with a given weights set,
score it against reference MusicXML (eval_first_run), and count hollow-notehead
detections. Run for prod / control / treatment to see whether hollow detection
rises without collapsing.

Usage:
  python3 benchmarks/omr-labeling-survey-2026-09/hollow_eval.py \
      --weights <path.pt> --tag prod --pdf <p1.pdf> --page 0 --stem beet5-p1
"""
import argparse, json, subprocess, sys, shutil
from collections import Counter
from pathlib import Path

BENCH = Path("benchmarks/omr-first-run-2026-08")
OUT = BENCH / "out"

def count_hollow(omr_json: Path) -> dict:
    d = json.loads(omr_json.read_text())
    cnt = Counter()
    for page in d.get("pages", []):
        for sysm in page.get("systems", []):
            for staff in sysm.get("staves", []):
                for meas in staff.get("measures", []):
                    for det in meas.get("detections", []):
                        c = det.get("class", "")
                        cl = c.lower()
                        if cl.startswith("noteheadhalf") or cl.startswith("noteheadwhole") or cl.startswith("noteheaddoublewhole"):
                            cnt["hollow_total"] += 1
                            cnt[c] += 1
                        elif cl.startswith("noteheadblack"):
                            cnt["black_total"] += 1
    return dict(cnt)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--stem", default="beet5-p1")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--score", action="store_true", help="run eval_first_run scoring (Beethoven5 p1 only)")
    args = ap.parse_args()

    stem = f"{args.stem}-{args.tag}"
    OUT.mkdir(parents=True, exist_ok=True)
    omr_json = OUT / f"{stem}.omr.json"
    omr_xml = OUT / f"{stem}.omr.musicxml"

    print(f"[{args.tag}] transcribe {Path(args.pdf).name} page {args.page} ...", flush=True)
    r = subprocess.run([sys.executable, "-m", "tools.omr.transcribe", args.pdf,
                        "--pages", str(args.page), "--weights", args.weights,
                        "--dpi", str(args.dpi), "--out", str(omr_json)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("TRANSCRIBE FAILED:\n", r.stderr[-2000:]); sys.exit(1)

    print(f"[{args.tag}] export musicxml ...", flush=True)
    r = subprocess.run([sys.executable, "-m", "tools.omr.export", str(omr_json),
                        "--format", "musicxml", "--out", str(omr_xml)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("EXPORT FAILED:\n", r.stderr[-2000:]); sys.exit(1)

    hist = count_hollow(omr_json)
    print(f"[{args.tag}] hollow histogram: {hist}", flush=True)

    result = {"tag": args.tag, "weights": args.weights, "hollow_histogram": hist}
    if args.score:
        r = subprocess.run([sys.executable, str(BENCH / "eval_first_run.py"), "--stem", stem],
                           capture_output=True, text=True)
        print(r.stdout[-2500:])
        if r.returncode != 0:
            print("SCORE FAILED:\n", r.stderr[-2000:])
        else:
            fr = json.loads((BENCH / f"{stem}-firstrun.json").read_text())
            result["pooled"] = fr["pooled"]
            result["clef_accuracy"] = fr["clef_accuracy"]
            result["measures_omr"] = fr["structure"]["measures_omr"]
    (Path("benchmarks/omr-labeling-survey-2026-09") / f"hollow_eval_{args.tag}.json").write_text(json.dumps(result, indent=2))
    print(f"[{args.tag}] wrote hollow_eval_{args.tag}.json", flush=True)

if __name__ == "__main__":
    main()
