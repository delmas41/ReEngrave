"""Summarise staff_lines_off_ink.py output (lane-staff-lines-off-ink)."""
import json, sys
import numpy as np

rows = []
for p in sys.argv[1:]:
    rows += json.load(open(p))
ok = [r for r in rows if "off" in r]
bad = [r for r in rows if "off" not in r]
print("staves", len(rows), "measured", len(ok), "unmeasured", len(bad),
      {r.get("error") for r in bad})
for doc in sorted({r["doc"] for r in ok}) + ["ALL"]:
    sub = [r for r in ok if doc == "ALL" or r["doc"] == doc]
    off = np.concatenate([np.array(r["off"]).ravel() for r in sub])
    goff = np.concatenate([np.array(r["goff"]).ravel() for r in sub])
    spf = np.concatenate([np.array(r["off"]).ravel() / r["sp"] for r in sub])
    a = np.abs(off)
    print(f"[{doc}] staves {len(sub)} points {len(off)}  signed median {np.median(off):+.2f}px "
          f"(gray {np.median(goff):+.2f}) abs median {np.median(a):.2f} p90 {np.percentile(a,90):.2f} max {a.max():.2f} px;"
          f" abs sp median {np.median(np.abs(spf)):.3f} p90 {np.percentile(np.abs(spf),90):.3f} max {np.abs(spf).max():.3f}")
    for thr in (0.25, 0.4):
        n = sum(1 for r in sub if (np.abs(np.array(r["off"])) / r["sp"]).max() >= thr)
        nm = sum(1 for r in sub if abs(r["med_px"]) / r["sp"] >= thr)
        print(f"    staves with any point >= {thr} sp: {n}   with MEDIAN offset >= {thr} sp: {nm}")
    # shape of the offset
    shifted = tilt = wander = line = 0
    for r in sub:
        sp = r["sp"]
        if r["worst_px"] / sp < 0.25:
            continue
        if abs(r["tilt_px"]) / sp >= 0.25 and r["resid_sd_px"] / sp < 0.15:
            tilt += 1
        elif r["resid_sd_px"] / sp >= 0.15:
            wander += 1
        elif r["line_spread_px"] / sp >= 0.25:
            line += 1
        else:
            shifted += 1
    print(f"    of the >=0.25sp staves: constant shift {shifted}, tilt {tilt}, wander(resid sd>=.15sp) {wander}, per-line {line}")
print("worst 10 (by max |offset| sp):")
for r in sorted(ok, key=lambda r: -(np.abs(np.array(r["off"])).max() / r["sp"]))[:10]:
    sp = r["sp"]
    print(f"  {r['doc']} staff {r['staff']} sp {sp:.1f}: max {np.abs(np.array(r['off'])).max()/sp:.2f} sp, "
          f"median {r['med_px']:+.1f}px, tilt {r['tilt_px']:+.1f}px over x, resid sd {r['resid_sd_px']:.1f}px, "
          f"line spread {r['line_spread_px']:.1f}px, n_clean {r['n_clean']}, wander(detector) {r['wander']}")
