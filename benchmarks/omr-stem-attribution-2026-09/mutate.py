"""Mutation battery over this lane's three instruments.

⚠️ THE INSTRUMENTS ARE THE ONLY THING THIS LANE SHIPS. Nothing under `tools/`
changes, so there is no unit suite to be the judge; the judge is each
instrument's own HEADLINE, which must MOVE. An arm that leaves it unchanged is
a SURVIVOR and a real gap.

⚠️ ONE RED ARM IS NOT A BATTERY, and the baseline must be GREEN before any arm
is read, or every arm is red for free.

⚠️ A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT — WHICH IS NOT THE
SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS NEITHER. A
BYTE snapshot on disk, an in-flight SENTINEL, a VERIFIED restore by md5, and a
refusal to start on a dirty tree without `--force`.

⚠️ THE PROBE IS RUN ON THE SMALLER RECORD ONLY. Litolff is 132 MB and reads in
~25 s; Breitkopf is 443 MB. An arm that has to be run 15 times pays that each
time, and every arm here is a claim about the RULE rather than about a plate.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
SENTINEL = OUT / ".mutate-in-flight"

PROBE = HERE / "probe_where_along_the_stem.py"
PREREG = HERE / "preregister.py"
CROP = HERE / "crop_strips.py"
TARGETS = {"probe": PROBE, "prereg": PREREG, "crop": CROP}

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
RECORD = LIB / "_shared-records" / "beethoven5-p1-p4.record.json"
PDF = (LIB / "editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
       "imslp984073.pdf")

#: (target, name, find, replace, what it must break)
ARMS = [
    # ── THE PROBE: the two frames, and the quantity it reports ─────────────
    ("probe", "the page box is dropped again (the fault this lane hit)",
     '                bp = (o.get("detail") or {}).get("bbox_page_px")',
     '                bp = None',
     "the crop stage must lose every mark -- the canonical/page frame error"),

    ("probe", "the end gap is measured to the FAR end, not the nearer",
     "                        min(abs(hcy - sb[1]), abs(hcy - (sb[1] + sb[3])))",
     "                        max(abs(hcy - sb[1]), abs(hcy - (sb[1] + sb[3])))",
     "the whole convention is *the head is at an END*; measuring to the far "
     "one inverts every band in the table"),

    ("probe", "the end gap is in PIXELS, not notehead heights",
     '                        / max(1.0, hb[3]), 3),',
     '                        / 1.0, 3),',
     "a pixel figure is a property of one render of one plate and cannot be "
     "compared between two publishers whose spacing differs 2x"),

    ("probe", "`interior_chord_member` needs a mate on ONE side only",
     '                    "interior_chord_member": bool(above and below),',
     '                    "interior_chord_member": bool(above or below),',
     "a chord INTERIOR is flanked on BOTH sides; either-side admits every "
     "outer head and empties the stratum the print is asked about"),

    ("probe", "the head/stroke test ignores x, so every head claims every stroke",
     "                if not boxes_overlap(hb, sb):",
     "                if False:",
     "the pair count must explode -- attribution is an OVERLAP question"),

    ("probe", "boxes_overlap treats touching boxes as overlapping",
     "    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]\n"
     "                or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])",
     "    return not (a[0] + a[2] < b[0] or b[0] + b[2] < a[0]\n"
     "                or a[1] + a[3] < b[1] or b[1] + b[3] < a[1])",
     "the SHIPPED `_stems_on` uses strict inequality and this probe measures "
     "what that decision sees; a looser test measures something else"),

    ("probe", "DEAD at zero reach becomes a clean exit",
     '        print("⚠️ DEAD: this record carries no head/stem pair to measure.",\n'
     '              file=sys.stderr)\n'
     '        Path(a.json).parent.mkdir(parents=True, exist_ok=True)\n'
     '        json.dump(out, open(a.json, "w"), indent=1)\n'
     '        return 2',
     '        pass',
     "a dead instrument must not read as a clean result"),

    # ── THE PRE-REGISTRATION: the thing that makes the sample honest ───────
    ("prereg", "the sample is drawn from an UNSORTED population",
     '        pop = sorted(pop, key=lambda r: (r["subject"], r["stem"]))',
     '        pop = list(pop)',
     "a seeded sample over an unordered population is the silent kind of "
     "irreproducible -- it still prints a seed"),

    ("prereg", "the strata are sampled in PROPORTION",
     "        take = pop if len(pop) <= PER_STRATUM else rng.sample(pop, PER_STRATUM)",
     "        n = max(1, int(PER_STRATUM * len(pop) / 300.0))\n"
     "        take = pop if len(pop) <= n else rng.sample(pop, n)",
     "the question is whether the LABELS are right, not how common each is; "
     "a proportional draw spends the human on the larger stratum"),

    ("prereg", "the seed moves with the run",
     "SEED = 20260920",
     "SEED = __import__('time').time_ns() % 100000",
     "a sample that cannot be reproduced cannot be checked against what was "
     "adjudicated"),

    ("prereg", "the FAR stratum drops its better-claimant condition",
     '                and any(o["end_gap_heads"] <= AT_AN_END_HEADS for o in mates)):',
     '                and True):',
     "the stratum is *the stroke demonstrably has a head at its end*; without "
     "it the population is every far head, including the 9 whose owner was "
     "never detected"),

    # ── THE CROP STAGE: the controls ───────────────────────────────────────
    ("crop", "the frame control is asked of the STRIP again",
     "        ok, d = _frame_ok(arr, lines, sp)",
     "        ok, d = _frame_ok(crop, [y - y0 for y in lines], sp)",
     "this is the fault this lane already paid for: 38 of 40 refused for a "
     "reason that has nothing to do with the geometry"),

    ("crop", "the frame control cannot refuse",
     "        if not ok:",
     "        if False:",
     "a crop pass whose frame is wrong produces confident verdicts about the "
     "wrong ink -- one Litolff strip is genuinely refused and must stay so"),

    ("crop", "the mark is drawn from the CANONICAL head box",
     "        hx = int(((hp[0] + hp[2]) / 2.0 - x0) * (PX_PER_SPACE / sp))",
     '        hx = int((r["head_box"][0] - x0) * (PX_PER_SPACE / sp))',
     "the canonical/page frame error, restored: every mark lands outside its "
     "own bar"),

    ("crop", "the tick is drawn ACROSS the staff instead of in the margin",
     "            img[0:band, max(0, hx - tw):hx + tw] = [255, 0, 0]\n"
     "            img[h - band:h, max(0, hx - tw):hx + tw] = [255, 0, 0]",
     "            img[:, max(0, hx - tw):hx + tw] = [255, 0, 0]",
     "an annotation over the ink is an annotation over the evidence, and this "
     "pass exists because a box was in the wrong place"),

    ("crop", "the strip is not upscaled",
     "        scale = PX_PER_SPACE / sp",
     "        scale = 1.0",
     "at the plate's native 16 px per staff space a stem cannot be traced by "
     "eye, which is what the strips are for"),

    ("crop", "the manifest carries the stratum into the image name",
     '        tid = hashlib.sha1(\n'
     '            f"{sample[\'seed\']}|{r[\'subject\']}|{r[\'stem\']}".encode()\n'
     '        ).hexdigest()[:10]',
     '        tid = r["stratum"][:4] + hashlib.sha1(\n'
     '            f"{sample[\'seed\']}|{r[\'subject\']}|{r[\'stem\']}".encode()\n'
     '        ).hexdigest()[:6]',
     "the adjudication must be BLIND -- a stratum visible in the filename "
     "puts the answer in the question"),
]


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()[:12]


def _run(args: list, cwd=ROOT) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-u", *args], cwd=str(cwd), env=env,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def headline() -> tuple[int, str]:
    """Probe -> pre-register -> crop, and the numbers each prints."""
    tmp = OUT / ".mutate"
    tmp.mkdir(parents=True, exist_ok=True)
    rc1, o1 = _run([str(PROBE), "--record", str(RECORD), "--label", "M",
                    "--json", str(tmp / "probe.json")])
    if rc1 != 0:
        return rc1, o1
    rc2, o2 = _run([str(PREREG), "--probe", str(tmp / "probe.json"),
                    "--label", "M", "--out", str(tmp / "sample.json")])
    if rc2 != 0:
        return 10 + rc2, o1 + o2
    rc3, o3 = _run([str(CROP), "--sample", str(tmp / "sample.json"),
                    "--record", str(RECORD), "--pdf", str(PDF),
                    "--out-dir", str(tmp / "strips"),
                    "--manifest", str(tmp / "manifest.json")])
    keep = []
    for line in (o1 + o2 + o3).splitlines():
        s = line.strip()
        if any(t in s for t in ("pairs", "available ->", "notehead boxes",
                                "wrote", "refused", "claim ONE", "DEAD",
                                "0-0.5")):
            keep.append(s)
    # ⚠️ THE IMAGE NAMES ARE PART OF THE HEADLINE, because the blindness arm
    # changes nothing a printed count can see.
    if (tmp / "strips").is_dir():
        keep.append("names:" + ",".join(
            sorted(p.name for p in (tmp / "strips").glob("*.png"))[:6]))
    return 20 + rc3 if rc3 else 0, "\n".join(keep)


def main() -> int:
    force = "--force" in sys.argv
    if SENTINEL.exists():
        print("REFUSED: an in-flight sentinel exists -- a previous battery "
              "was interrupted and the tree may still carry a mutation.")
        print(SENTINEL.read_text())
        return 3
    rel = [str(p.relative_to(ROOT)) for p in TARGETS.values()]
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *rel],
                           cwd=str(ROOT), capture_output=True,
                           text=True).stdout.strip()
    if dirty and not force:
        print(f"REFUSED: a target is dirty:\n{dirty}\nCommit, or --force.")
        return 3

    OUT.mkdir(parents=True, exist_ok=True)
    snap = {k: v.read_bytes() for k, v in TARGETS.items()}
    SENTINEL.write_text("\n".join(
        f"{k}={TARGETS[k]} md5={md5b(v)}" for k, v in snap.items()) + "\n")

    print("=" * 78)
    print("BASELINE (the positive control -- every arm is free if this is not "
          "green)")
    print("=" * 78)
    b_rc, b_out = headline()
    print(f"  exit {b_rc}")
    print("  " + b_out.replace("\n", "\n  "))
    if b_rc != 0:
        print("\n⚠️ BASELINE IS NOT GREEN. The battery measures nothing.")
        for k, v in snap.items():
            TARGETS[k].write_bytes(v)
        SENTINEL.unlink(missing_ok=True)
        return 4

    red, survived, bad = [], [], []
    for target, name, find, repl, why in ARMS:
        src = snap[target].decode("utf-8")
        if src.count(find) != 1:
            bad.append((name, f"{src.count(find)} occurrences in {target}"))
            print(f"\n{'-' * 78}\nARM [{target}]: {name}\n  ⚠️ BAD ANCHOR "
                  f"({src.count(find)} occurrences) -- REPORTED AS AN ERROR")
            continue
        TARGETS[target].write_text(src.replace(find, repl), encoding="utf-8")
        rc, out = headline()
        TARGETS[target].write_bytes(snap[target])
        moved = (rc != b_rc) or (out != b_out)
        (red if moved else survived).append((target, name, why))
        print(f"\n{'-' * 78}\nARM [{target}]: {name}")
        print(f"  expected: {why}")
        print(f"  exit {rc}  -> {'RED' if moved else 'SURVIVED'}")
        if not moved:
            print("  ⚠️ SURVIVOR -- a real gap, not a pass.")

    ok = True
    for k, v in snap.items():
        TARGETS[k].write_bytes(v)
        if md5b(TARGETS[k].read_bytes()) != md5b(v):
            print(f"\n⚠️⚠️ RESTORE FAILED for {k}")
            ok = False
    if ok:
        SENTINEL.unlink(missing_ok=True)

    print("\n" + "=" * 78)
    print(f"RED {len(red)}   SURVIVED {len(survived)}   BAD ANCHORS {len(bad)}")
    print(f"restore VERIFIED by md5: {ok}")
    for t, n, _ in survived:
        print(f"  SURVIVOR [{t}] {n}")
    for n, m in bad:
        print(f"  BAD ANCHOR {n}: {m}")
    return 0 if (ok and not survived and not bad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
