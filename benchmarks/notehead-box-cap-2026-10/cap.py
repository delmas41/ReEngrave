"""2.222: candidate caps, what each keeps / rules out per plate, controls, and the 12 blind tiles.

    python3 benchmarks/notehead-box-cap-2026-10/cap.py numbers          # table -> stdout (+ numbers.json)
    python3 benchmarks/notehead-box-cap-2026-10/cap.py tiles            # out/print/2.222-cap/

A cap is "over" when width > W (width-only) or width > W or height > H. All sizes are own-staff spaces.
"""
import collections, json, pathlib, random, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import pops

ROOT = pathlib.Path(__file__).resolve().parents[2]
P = pops.load()
CAPS = {"W2.2": lambda g: g["w"] > 2.2, "W2.4": lambda g: g["w"] > 2.4, "W2.6": lambda g: g["w"] > 2.6, "W3.0": lambda g: g["w"] > 3.0,
        "W2.6|H2.8": lambda g: g["w"] > 2.6 or g["h"] > 2.8, "H2.8 only": lambda g: g["h"] > 2.8, "H3.5 only": lambda g: g["h"] > 3.5}
CAP = CAPS["W2.4"]
WCAP = 2.4


def numbers():
    out = {}
    for name, f in CAPS.items():
        out[name] = {}
        for plate, X in P.items():
            A = list(X["A"].values())
            Dw = [X["heads"][k] for k in X["D"] if k in X["A"] or k in X["B"]]
            Dall = [X["heads"][k] for k in X["D"]]
            out[name][plate] = dict(A_total=len(A), A_lost=sum(map(f, A)), A_keep_pct=round(100 - 100 * sum(map(f, A)) / len(A), 2),
                                    B_over=sum(map(f, X["B"].values())), B_total=len(X["B"]),
                                    clef_over=sum(map(f, X["clefs"])), clef_total=len(X["clefs"]),
                                    dyn_over=sum(map(f, X["dyns"])), dyn_total=len(X["dyns"]),
                                    D_over=sum(map(f, Dall)), D_total=len(Dall), Dw_over=sum(map(f, Dw)), Dw_total=len(Dw))
    (pathlib.Path(__file__).resolve().parent / "numbers.json").write_text(json.dumps(out, indent=1))
    for name, d in out.items():
        for plate, r in d.items():
            print("%-10s %-8s keep %.2f%% (lost %d/%d) B %d/%d clef %d/%d dyn %d/%d D %d/%d D_written %d/%d" % (
                name, plate, r["A_keep_pct"], r["A_lost"], r["A_total"], r["B_over"], r["B_total"], r["clef_over"], r["clef_total"],
                r["dyn_over"], r["dyn_total"], r["D_over"], r["D_total"], r["Dw_over"], r["Dw_total"]))
    # controls: sizes of known objects
    for label, plate, key in (("Sean 2.221 tile 4 head box (union with a natural was the drawn box)", "litolff", "glyph/10/1/3/14/4"),
                              ("Sean 2.221 tile 6 head box (union with an 8th rest was the drawn box)", "litolff", "glyph/2/1/9/11/3"),
                              ("preview: blob of heads", "litolff", "glyph/9/0/3/1/15"), ("preview: ff letters", "litolff", "glyph/4/0/0/11/15"),
                              ("preview: beam", "brahms", "glyph/5/0/4/0/16"), ("preview: F clef written as a note", "brahms", "glyph/19/0/12/3/9")):
        g = P[plate]["boxes"][key]
        print("CONTROL %-70s %s w %.2f h %.2f  W2.4 over: %s  H2.8 over: %s" % (label, key, g["w"], g["h"], g["w"] > 2.4, g["h"] > 2.8))


def tiles():
    from tools.omr.staged import lane_report as LR
    cand = []
    for plate, X in P.items():
        for g in X["A"].values():
            cand.append(dict(plate=plate, page=g["page"], box=g["box"], key=g["key"], w=round(g["w"], 2), h=round(g["h"], 2), cls=g["cls"]))
    over = sorted([c for c in cand if c["w"] > WCAP], key=lambda c: c["w"])
    under_w = sorted([c for c in cand if 2.0 < c["w"] <= WCAP], key=lambda c: -c["w"])
    tall = sorted([c for c in cand if c["w"] <= 2.0 and c["h"] > 3.0], key=lambda c: c["h"])
    rnd = random.Random(222)
    pick = []
    def take(pool, n, plates):
        got = []
        for pl in plates:
            got += [c for c in pool if c["plate"] == pl][:n]
        return got
    o = take(over, 4, ["litolff"]) + take(over, 2, ["brahms"])
    o = (o + [c for c in over if c not in o])[:6]
    u = take(under_w, 2, ["litolff", "brahms"])                      # 4 width-near, 2 per plate
    u += rnd.sample([c for c in tall if c["plate"] == "litolff"][:12], 1) + rnd.sample([c for c in tall if c["plate"] == "brahms"][:6], 1)   # 2 tall-narrow probes
    items = [dict(c, role="case", side="over" if c in o else "under") for c in o + u]
    rnd.shuffle(items)
    out = ROOT / "out" / "print" / "2.222-cap"
    out.mkdir(parents=True, exist_ok=True)
    LR.cut_tiles(items, out, "tiles")
    (out / "key.json").write_text(json.dumps(items, indent=1))
    (out / "tiles" / "README.md").write_text("# 2.222 notehead box tiles\n\nEach picture has ONE orange box. The orange box is a box the detector called a notehead; "
                                             "what is inside it: one note, two or more notes, a clef, a dynamic, or something else?\n")
    for i, it in enumerate(items, 1):
        print(i, it["side"], it["plate"], it["key"], it["w"], it["h"])


if __name__ == "__main__":
    {"numbers": numbers, "tiles": tiles}[sys.argv[1]]()
