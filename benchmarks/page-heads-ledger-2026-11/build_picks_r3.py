"""ROADMAP 2.290 build round 3 -- the picks for `make_tiles_r3.py` (READ-ONLY on the records).

    python3 benchmarks/page-heads-ledger-2026-11/build_picks_r3.py WORKDIR R1WORKDIR OUT.json [SEED=2290]

WORKDIR = this round's lane-report work dir; R1WORKDIR = round 1's (every round-1 head claim, the population the refusals are drawn from).
SELECTION RULE (stated, seeded), to 12, Sean's round-1 AND round-2 places never shown again:
  1. every note LOST or GAINED OFF -> ON (`lost_notes.py`'s matching by place), at its ON head's whole claimed ink, else its box;
  2. then every UNISON the reader decides ON that it did not decide OFF (`Q.UNISON_VOICES` decided on a box of the head: two stems, two notes);
  3. then a seeded draw of the remaining REFUSALS (a round-1 head claim with no claim now on its ink), alternating the reasons `too_small` / `too_tall`
     (the round-3 cuts) / `other` (cut through one ink, or the claim moved), so each kind is shown.
Each pick: plate, page, box (page px, the WHOLE claimed/refused ink), staff_lines [top, bottom] of the staff that OWNS the head (the last decided
`glyph_owner` verdict; the cell's staff where there is none), kind, why.
"""
import json
import os
import pathlib
import random
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_picks as BP                                  # noqa: E402
import build_picks_r2 as B2                               # noqa: E402

SEEN = [json.loads((HERE / "answers" / "answers-2.290-build-r1.json").read_text())["tiles"]]
R2_KEY = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/out/print-from-worktrees/2.290-build-r2/key.json")


def owner_lines(rec_obs, glyph, staff):
    """Staff lines [top, bottom] of the staff owning `glyph`: the last decided glyph_owner verdict naming a staff, else the cell's own staff."""
    return None


def main():
    work, w1, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 2290
    rng = random.Random(seed)
    seen = {}
    for t in SEEN[0]:
        seen.setdefault((t["plate"], t["page"]), []).append(t["box"])
    for t in json.loads(R2_KEY.read_text()):
        seen.setdefault((t["plate"], t["page"]), []).append(t["box"])

    def seen_before(plate, page, box):
        return any(B2.overlap_share(box, b) > 0.3 for b in seen.get((plate, page), []))
    lost, unison, refused = [], [], []
    for plate in ("litolff", "brahms"):
        f_on = work / ("%s.on.gathered.record.json" % plate)
        if not f_on.exists():
            continue
        raw = json.loads(f_on.read_text())
        rec = raw.get("record", raw)
        owner = {}
        uni = {}
        for v in rec.get("verdicts") or []:
            if v.get("quantity") == "glyph_owner" and v.get("outcome") == "decided" and isinstance(v.get("value"), str) and v["value"].startswith("staff/"):
                owner[v["subject"]] = v["value"]
            elif v.get("quantity") == "unison_voices" and v.get("outcome") == "decided":
                uni[v["subject"]] = True
        off_raw = json.loads((work / ("%s.off.gathered.record.json" % plate)).read_text())
        off_uni = {v["subject"] for v in (off_raw.get("record", off_raw).get("verdicts") or []) if v.get("quantity") == "unison_voices" and v.get("outcome") == "decided"}
        del off_raw
        on = BP.index(rec["observations"])
        r1 = BP.index(BP.load(w1 / ("%s.on.gathered.record.json" % plate)))
        sp = 15.75 if plate == "litolff" else 32.0
        cb_on, cb_r1 = B2.claim_boxes(on), B2.claim_boxes(r1)

        def lines_of(glyph, staff_map):
            own = owner.get(glyph)
            if own and own in staff_map:
                v = staff_map[own]
                return [v[0], v[-1]], own
            return B2.staff_lines(staff_map, glyph), None
        txt = subprocess.run([sys.executable, str(HERE / "lost_notes.py"), str(work), plate], capture_output=True, text=True, cwd=str(HERE.parents[1]),
                             env=dict(os.environ, PYTHONPATH=".")).stdout
        for ln in txt.splitlines():
            if "glyph " not in ln or not (ln.startswith("LOST") or ln.startswith("GAINED")):
                continue
            g = ln.split("glyph ")[-1].strip()
            if g not in on[1]:
                continue
            it = BP.item(plate, g, on[0], on[1], on[3], on[4], "note")
            lines, own = lines_of(g, on[4])
            if lines:
                lost.append(dict(plate=plate, page=it["page"], box=it["box"], staff_lines=lines, kind="note_" + ("lost" if ln.startswith("LOST") else "gained"),
                                 why=ln.split("  glyph")[0], glyph=g, owner=own))
        for g in sorted(uni):
            if g not in on[1]:
                continue
            members = set((on[2].get(g) or (None, {}))[1].get("members") or [g]) | {g}
            if members & off_uni:
                continue                    # a unison the flag-off reader already decided: nothing changed there
            it = BP.item(plate, g, on[0], on[1], on[3], on[4], "unison")
            lines, own = lines_of(g, on[4])
            if lines:
                unison.append(dict(plate=plate, page=it["page"], box=it["box"], staff_lines=lines, kind="unison", why="a head the unison reader decides: two stems, two notes",
                                   glyph=g, owner=own))
        for c, box, sb in cb_r1:
            if any(B2.overlap_share(box, b2) >= 0.5 for _c2, b2, _s2 in cb_on if _c2["page"] == c["page"]):
                continue
            w, h = (box[2] - box[0]) / sp, (box[3] - box[1]) / sp
            reason = "too_small" if min(w, h) < 0.6 else ("too_tall" if h > 2.0 else "other")
            lines, own = lines_of(c.get("rep"), r1[4]) if c.get("rep") else (None, None)
            if lines:
                refused.append(dict(plate=plate, page=c["page"], box=[round(v, 1) for v in box], staff_lines=lines, kind="refused_" + reason,
                                    why="a round-1 claim now refused (%.2f x %.2f sp)" % (w, h), glyph=c.get("rep"), owner=own))
    keep = lambda L: [p for p in L if not seen_before(p["plate"], p["page"], p["box"])]
    lost, unison, refused = keep(lost), keep(unison), keep(refused)
    picks = sorted(lost, key=lambda p: (p["plate"], p["page"], p["box"][0]))[:12]
    seen_boxes = []
    for p in sorted(unison, key=lambda p: (p["plate"], p["page"], p["box"][0])):
        if len(picks) < 12 and not any(B2.overlap_share(p["box"], q["box"]) > 0.3 and p["page"] == q["page"] and p["plate"] == q["plate"] for q in picks):
            picks.append(p)
    by_reason = {}
    for p in refused:
        by_reason.setdefault(p["kind"], []).append(p)
    for v in by_reason.values():
        rng.shuffle(v)
    keys = sorted(by_reason)
    i = 0
    while len(picks) < 12 and any(by_reason.values()) and i < 2000:
        k = keys[i % len(keys)]
        if by_reason[k]:
            picks.append(by_reason[k].pop())
        i += 1
    pathlib.Path(out).write_text(json.dumps(picks, indent=1))
    print("lost/gained", len(lost), "unison", len(unison), "refused", len(refused), {k: len(v) for k, v in by_reason.items()}, "-> picks", len(picks))


if __name__ == "__main__":
    main()
