"""Direction-word reader timing + cheaper arms, ONE page per run (Sean 2026-10-08: "Why is it 4:30 a page?").

Runs the real staged GATHER (--through gather) on one page with OMR_DIRECTION_TEXT_SCAN_GATE off, and at the place
`gather_direction_words` would run, REPLACES it with this measurement (same inputs: pws, page_dict built by the gather's
own `_direction_page_dict`). Nothing in the product changes; arms are keyword/inline only.

    python3 direction_timing.py <pdf> <page> <tag> <out.json>

Parts timed (wall clock, this page): Surya worker start-up + first/second call; candidate finding; crop+upscale;
Surya (count, total, mean); Tesseract (count, total, mean); lexicon gate.
Arms: full | A tess only | B tess then surya on lexicon-failures | C surya only | D one crop per band strip |
E size-filtered candidates (full) | E+B.
"""
from __future__ import annotations
import json, os, sys, time, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
os.environ.pop("OMR_DIRECTION_TEXT_SCAN_GATE", None)          # gate OFF (default)

import cv2
import numpy as np

WEIGHTS = "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
RESULT: dict = {}
OUT: Path


def now():
    return time.perf_counter()


def norm(t: str) -> str:
    return " ".join(t.lower().replace(".", " ").split())


def decide(cands, texts_by_reader, order, lookup):
    """Replicates read_directions' acceptance: first accepted reader in `order` wins. -> {cand_index: (reader, text)}"""
    out = {}
    for i, _c in enumerate(cands):
        for name in order:
            ts = texts_by_reader.get(name)
            if ts is None or i >= len(ts) or not ts[i]:
                continue
            if lookup(ts[i]) is not None:
                out[i] = (name, ts[i])
                break
    return out


def run_experiment(log, pws, cells, local, detections):
    from tools.omr import direction_text as DT
    from tools.omr import staff_labels_surya as SU
    from tools.omr import staff_labels_tesseract as TE
    from tools.omr.staged import gather as G
    from tools.omr.direction_lexicon import lookup

    R = RESULT
    page_t0 = now()
    page_dict = G._direction_page_dict(pws, cells, {}, {}) if False else None
    # the gather's own shim, with its real arguments
    page_dict = G._direction_page_dict(pws, cells, local, detections)
    cfg = DT.DEFAULT_BAND_CONFIG
    spacing = float(np.median([DT._spacing(s) for s in pws.staves]))
    R["spacing_px"] = spacing
    R["scan_gate_would_fire"] = bool(DT.page_is_scanned(pws.page))

    # ---- candidates -------------------------------------------------------------------------------------------
    t0 = now(); cands = DT.find_candidates(pws, page_dict); R["t_find_candidates"] = now() - t0
    t0 = now(); readers = DT.default_readers(pws.page); R["t_default_readers(incl page_is_engraved)"] = now() - t0
    R["readers"] = [n for n, _ in readers]
    R["n_candidates"] = len(cands)
    # ---- crops ------------------------------------------------------------------------------------------------
    t0 = now(); crops = [DT.crop_for(pws.page, c, spacing) for c in cands]; R["t_crop_upscale"] = now() - t0
    R["crop_shapes_median_hw"] = [int(statistics.median(c.shape[0] for c in crops)),
                                  int(statistics.median(c.shape[1] for c in crops))] if crops else None
    R["crop_px_total"] = int(sum(c.shape[0] * c.shape[1] for c in crops))

    # ---- surya start-up (worker session was opened by main() around the whole gather; time a FRESH one-shot too) --
    surya_rd = dict(readers).get("surya")
    tess_rd = dict(readers).get("tesseract")
    dummy = np.full((90, 360, 3), 255, np.uint8)
    cv2.putText(dummy, "legato", (10, 65), cv2.FONT_HERSHEY_SCRIPT_COMPLEX, 2.0, (0, 0, 0), 3)
    surya_calls = []

    def surya_read(cs, label):
        t = now(); o = SU.read_crops_text(cs); dt = now() - t
        surya_calls.append({"label": label, "n_crops": len(cs), "s": dt})
        return o, dt

    R["resident_server_before"] = (SU.resident_server() or {}).get("pid")
    _o, dt = surya_read([dummy], "warmup-1st-call-on-open-session"); R["t_surya_first_call_1crop"] = dt
    _o, dt = surya_read([dummy], "warmup-2nd-call"); R["t_surya_second_call_1crop"] = dt
    R["dummy_read"] = _o

    if os.environ.get("DT_PERCROP"):
        # per-crop Surya latency, one call each: which crops carry the time, and what they read
        rows = []
        for i, c in enumerate(crops):
            t = now(); o = SU.read_crops_text([c])[0]; rows.append({"cand": i, "s": now() - t, "text": o})
        R["percrop_surya"] = rows
        R["percrop_total"] = sum(r["s"] for r in rows)
        return
    # ---- FULL arm: the real read_directions, both rungs, instrumented -----------------------------------------
    stats = {"surya": [], "tesseract": []}

    def wrap(name, fn):
        def r(cs):
            t = now(); o = fn(cs); stats[name].append((len(cs), now() - t)); return o
        return r
    texts_full = {}

    def wrap_keep(name, fn):
        w = wrap(name, fn)
        def r(cs):
            o = w(cs); texts_full[name] = list(o); return o
        return r
    t0 = now()
    found, info = DT.read_directions(pws, page_dict, readers=[("surya", wrap_keep("surya", surya_rd)),
                                                              ("tesseract", wrap_keep("tesseract", tess_rd))])
    full_wall = now() - t0
    R["full_wall_read_directions"] = full_wall
    R["full_surya_calls"] = stats["surya"]; R["full_surya_total"] = sum(s for _, s in stats["surya"])
    R["full_tess_total_batch"] = sum(s for _, s in stats["tesseract"])
    R["full_n_read"] = info["n_read"]; R["full_n_accepted"] = info["n_accepted"]
    R["full_rejected_texts"] = info["rejected"]; R["full_conflicts"] = info["conflicts"]
    R["full_by_reader"] = info["by_reader"]
    # lexicon gate, timed alone over every raw string
    allstrings = [t for ts in texts_full.values() for t in ts]
    t0 = now()
    for _ in range(20):
        for s in allstrings:
            lookup(s)
    R["t_lexicon_per_pass"] = (now() - t0) / 20.0
    R["lexicon_calls_per_pass"] = len(allstrings)
    words_full = {i: v for i, v in decide(cands, texts_full, ["surya", "tesseract"], lookup).items()}
    R["full_words"] = [{"cand": i, "staff": cands[i].staff_index, "measure": cands[i].measure_index,
                        "placement": cands[i].placement, "reader": r, "text": t} for i, (r, t) in sorted(words_full.items())]
    R["raw_texts"] = [{"cand": i, "surya": texts_full.get("surya", [""] * len(cands))[i],
                       "tess": texts_full.get("tesseract", [""] * len(cands))[i]} for i in range(len(cands))]
    # candidate geometry (spaces) + outcome
    geo = []
    for i, c in enumerate(cands):
        x0, y0, x1, y1 = c.bbox_page
        geo.append({"cand": i, "w_sp": (x1 - x0) / spacing, "h_sp": (y1 - y0) / spacing, "n_comp": c.n_components,
                    "placement": c.placement, "accepted": i in words_full})
    R["geometry"] = geo

    keyset = lambda words: sorted((cands[i].staff_index, cands[i].measure_index, cands[i].x_page, norm(t))
                                  for i, (_r, t) in words.items())
    full_keys = keyset(words_full)

    def compare(words, subset_idx=None):
        got = keyset(words)
        gotn = [(a, b, c_, d) for a, b, c_, d in got]
        same = [k for k in full_keys if k in got]
        missing = [k for k in full_keys if k not in got]
        extra = [k for k in got if k not in full_keys]
        return {"n_words": len(got), "same": len(same), "missing": [list(k) for k in missing],
                "extra": [list(k) for k in extra]}

    # ---- arm A: tesseract only, one call per crop --------------------------------------------------------------
    def tess_each(cs):
        outs, ts = [], []
        for c in cs:
            t = now(); o = TE.read_crops_text([c])[0]; ts.append(now() - t); outs.append(o)
        return outs, ts
    tA, ts = tess_each(crops)
    R["tess_calls"] = {"n": len(ts), "total": sum(ts), "mean": sum(ts) / max(1, len(ts)),
                       "max": max(ts) if ts else 0}
    wA = decide(cands, {"tesseract": tA}, ["tesseract"], lookup)
    R["A_tess_only"] = {"time_read_s": sum(ts), "lexicon_s": R["t_lexicon_per_pass"] / 2, **compare(wA)}

    # ---- arm C: surya only (fresh run: also the repeatability of Surya) ----------------------------------------
    tC, dtC = surya_read(crops, "C-all-crops")
    wC = decide(cands, {"surya": tC}, ["surya"], lookup)
    R["C_surya_only"] = {"time_read_s": dtC, "per_crop_mean_s": dtC / max(1, len(crops)), **compare(wC)}
    R["C_vs_full_surya_texts_identical"] = sum(1 for a, b in zip(tC, texts_full.get("surya", [])) if a == b)

    # ---- arm B: tesseract first, surya only where tesseract's reading fails the lexicon ---------------------------
    fail = [i for i in range(len(crops)) if lookup(tA[i]) is None] if crops else []
    tB_s, dtB = (surya_read([crops[i] for i in fail], "B-lexicon-failures") if fail else ([], 0.0))
    sur = {i: t for i, t in zip(fail, tB_s)}
    wB = {}
    for i in range(len(crops)):
        if lookup(tA[i]) is not None:
            wB[i] = ("tesseract", tA[i])
        elif sur.get(i) and lookup(sur[i]) is not None:
            wB[i] = ("surya", sur[i])
    R["B_tess_then_surya"] = {"n_surya_crops": len(fail), "time_read_s": sum(ts) + dtB, "tess_s": sum(ts),
                              "surya_s": dtB, **compare(wB)}
    # B2: same but ONLY on crops with no usable (non-empty) tesseract text at all is not the specified arm; skip.

    # ---- arm E: size test on candidates -------------------------------------------------------------------------
    # The test (a priori, from the glyph facts in direction_text: a letter is 0.1-1.8 sp, a word is >= 2 letters):
    #   keep if  1.0 <= w <= 20 spaces  and  0.45 <= h <= 3.0 spaces  and  n_components >= 2
    def keep(g):
        return 1.0 <= g["w_sp"] <= 20.0 and 0.45 <= g["h_sp"] <= 3.0 and g["n_comp"] >= 2
    kept = [g["cand"] for g in geo if keep(g)]
    R["E_size_test"] = {"rule": "1.0<=w<=20 sp, 0.45<=h<=3.0 sp, n_components>=2", "kept": len(kept),
                        "dropped": len(geo) - len(kept),
                        "dropped_accepted_in_full": [i for i in words_full if i not in kept]}
    # E (both rungs on survivors): reuse the full-arm texts for the ANSWER; time it for real on the survivors
    kc = [crops[i] for i in kept]
    _o, dtE_s = surya_read(kc, "E-survivors") if kc else ([], 0.0)
    _t, tsE = tess_each(kc)
    texts_E = {"surya": [""] * len(cands), "tesseract": [""] * len(cands)}
    for j, i in enumerate(kept):
        texts_E["surya"][i] = _o[j]; texts_E["tesseract"][i] = _t[j]
    wE = decide(cands, texts_E, ["surya", "tesseract"], lookup)
    R["E_size_filtered_full_readers"] = {"time_read_s": dtE_s + sum(tsE), "surya_s": dtE_s, "tess_s": sum(tsE),
                                         **compare(wE)}
    # E+B: size filter, tesseract then surya on the failures
    failE = [i for i in kept if lookup(tA[i]) is None]
    _os, dtEB = surya_read([crops[i] for i in failE], "E+B-lexicon-failures") if failE else ([], 0.0)
    sE = dict(zip(failE, _os)); wEB = {}
    tsEB = sum(tsE)
    for i in kept:
        if lookup(tA[i]) is not None:
            wEB[i] = ("tesseract", tA[i])
        elif sE.get(i) and lookup(sE[i]) is not None:
            wEB[i] = ("surya", sE[i])
    R["EB_size_filtered_tess_then_surya"] = {"n_surya_crops": len(failE), "time_read_s": tsEB + dtEB,
                                             "tess_s": tsEB, "surya_s": dtEB, **compare(wEB)}
    # E2: a TIGHT size test, derived from where Brahms p1's 8 words sit (w 4.65-6.0 sp, h 1.2-1.82 sp, >=4 components).
    #     Derived on the page it is scored on -> an upper bound on what a size test can do, not a held-out result.
    keep2 = [g["cand"] for g in geo if g["w_sp"] >= 4.3 and g["h_sp"] >= 1.2 and g["n_comp"] >= 4]
    R["E2_tight_size_test"] = {"rule": "w>=4.3 sp, h>=1.2 sp, n_components>=4", "kept": len(keep2),
                               "dropped": len(geo) - len(keep2),
                               "dropped_accepted_in_full": [i for i in words_full if i not in keep2]}
    # E+A: size filter + tesseract only
    wEA = decide([cands[i] for i in range(len(cands))], {"tesseract": [tA[i] if i in set(kept) else "" for i in range(len(cands))]},
                 ["tesseract"], lookup)
    ttE = sum(t for t, i in zip(ts, range(len(ts))) if i in set(kept))
    R["EA_size_filtered_tess_only"] = {"time_read_s": ttE, **compare(wEA)}

    # ---- arm D: one crop per band strip (candidate-bearing bands) ---------------------------------------------------
    mask = DT._blank_detections(DT._page_ink(pws.page), page_dict, spacing, cfg)
    bands = {}
    for sdx, plc, yt, yb in DT._bands_for_page(pws, cfg):
        bands[(sdx.staff_index, plc)] = (sdx, yt, yb)
    groups = {}
    for i, c in enumerate(cands):
        groups.setdefault((c.staff_index, c.placement), []).append(i)
    strips = []
    for (si, plc), idxs in sorted(groups.items()):
        if (si, plc) not in bands:
            continue
        st, yt, yb = bands[(si, plc)]
        xs0 = max(0, min(cands[i].bbox_page[0] for i in idxs) - int(1.3 * spacing))
        xs1 = min(mask.shape[1], max(cands[i].bbox_page[2] for i in idxs) + int(1.3 * spacing))
        strip = 255 - mask[yt:yb, xs0:xs1]
        sc = min(2.0, 60.0 / spacing)
        if sc > 1.0:
            strip = cv2.resize(strip, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        strips.append({"staff": si, "placement": plc, "idxs": idxs, "img": cv2.cvtColor(strip, cv2.COLOR_GRAY2BGR),
                       "w": int(xs1 - xs0)})
    R["D_n_strips"] = len(strips)
    import pytesseract
    D_tess_words = []
    tD0 = now()
    for s in strips:
        g = cv2.cvtColor(s["img"], cv2.COLOR_BGR2GRAY)
        d = pytesseract.image_to_data(g, config="--psm 11", output_type=pytesseract.Output.DICT)
        toks = [(d["top"][k], d["left"][k], d["text"][k].strip()) for k in range(len(d["text"]))
                if d["text"][k].strip() and float(d["conf"][k]) >= 30]
        toks.sort(key=lambda t: (round(t[0] / (2 * spacing)), t[1]))
        words = [t[2] for t in toks]
        found_w = []; k = 0
        while k < len(words):
            hit = None
            for L in (4, 3, 2, 1):
                ph = " ".join(words[k:k + L])
                if len(words[k:k + L]) == L and lookup(ph) is not None:
                    hit = (L, ph); break
            if hit:
                found_w.append(hit[1]); k += hit[0]
            else:
                k += 1
        D_tess_words.append({"staff": s["staff"], "placement": s["placement"], "n_cands": len(s["idxs"]),
                             "strip_w_px": s["w"], "raw": words[:40], "words": found_w})
    R["D_tess_strips"] = {"time_s": now() - tD0, "n_calls": len(strips), "strips": D_tess_words}
    # surya on the strips (text order only)
    tD1 = now()
    sD, _ = surya_read([s["img"] for s in strips], "D-strips") if (strips and not os.environ.get("DT_SKIP_D_SURYA")) else ([""] * len(strips), 0)
    dtD = now() - tD1
    D_s = []
    for s, txt in zip(strips, sD):
        wl = txt.split(); found_w = []; k = 0
        while k < len(wl):
            hit = None
            for L in (4, 3, 2, 1):
                ph = " ".join(wl[k:k + L])
                if len(wl[k:k + L]) == L and lookup(ph) is not None:
                    hit = (L, ph); break
            if hit:
                found_w.append(hit[1]); k += hit[0]
            else:
                k += 1
        D_s.append({"staff": s["staff"], "placement": s["placement"], "raw": txt[:200], "words": found_w})
    R["D_surya_strips"] = {"time_s": dtD, "n_calls": len(strips), "strips": D_s}
    # full words per band for comparison, as bag-of-words per (staff, placement)
    bag = {}
    for i, (_r, t) in words_full.items():
        bag.setdefault(f"{cands[i].staff_index}/{cands[i].placement}", []).append(norm(t))
    R["D_full_bag_per_band"] = bag

    R["surya_calls_all"] = surya_calls
    R["page_experiment_wall_s"] = now() - page_t0


def main():
    pdf, page, tag, out = sys.argv[1:5]
    global OUT
    OUT = Path(out)
    from tools.omr.staged import gather as G
    from tools.omr import staff_labels_surya as SU
    orig = G.gather_direction_words

    def patched(log, pws, cells, local, detections):
        try:
            run_experiment(log, pws, cells, local, detections)
        except Exception:
            import traceback; RESULT["error"] = traceback.format_exc(); print(RESULT["error"])
        RESULT["tag"] = tag
        OUT.write_text(json.dumps(RESULT, indent=1, default=str))
    G.gather_direction_words = patched

    t0 = now()
    cm = SU.worker_session()
    sess = cm.__enter__()
    RESULT["t_surya_worker_session_open"] = now() - t0
    RESULT["session_opened"] = sess is not None
    try:
        from tools.omr.staged.__main__ import main as staged_main
        w0 = now()
        staged_main([pdf, "--pages", page, "--weights", WEIGHTS, "--through", "gather", "--progress"])
        RESULT["gather_wall_total_incl_experiment"] = now() - w0
    finally:
        cm.__exit__(None, None, None)
        OUT.write_text(json.dumps(RESULT, indent=1, default=str))


if __name__ == "__main__":
    main()
