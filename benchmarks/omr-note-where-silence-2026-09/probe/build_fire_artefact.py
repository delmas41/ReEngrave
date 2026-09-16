"""Build the 25-fire artefact: the population the SHIPPED RULE acts on.

Everything except the VERDICT column is computed -- the fire set from the same
cuts the decision ships, the part/measure from the exporter's own system map,
and the already-unwritten reconciliation from the record's own verdicts. The
verdict column is this session's hand adjudication of the crops in
crops/every-fire-*.png.
"""
import json
import collections

SP = ('/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-'
      'worktrees-overnight-manager-handoff-08261d/'
      'fc13d9c7-4153-4a84-b9e0-e6f3aa096cc6/scratchpad/out')
BENCH = ('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/'
         'agent-ab4e6b975a59959c5/benchmarks/omr-note-where-silence-2026-09')

# ── the hand verdicts, read off crops/every-fire-A|B|C.png ──────────────────
VERDICT = {
    "glyph/1/0/0/15/1": ("whole_rest", ""),
    "glyph/1/0/2/15/5": ("whole_rest", ""),
    "glyph/1/0/5/4/1": ("whole_rest", "a fermata is printed over it"),
    "glyph/2/0/0/10/2": ("whole_rest", ""),
    "glyph/2/0/0/15/3": ("whole_rest", ""),
    "glyph/2/0/2/11/3": ("whole_rest", ""),
    "glyph/2/0/3/10/1": ("whole_rest", "= P4 m27; strip p2s0st3 shows the tacet run"),
    "glyph/2/1/0/5/7": ("whole_rest", ""),
    "glyph/2/1/4/3/2": ("whole_rest", ""),
    "glyph/3/0/0/10/2": ("whole_rest", ""),
    "glyph/3/0/5/13/4": ("whole_rest", "= P6 m61; strip p3s0st5 shows m62/m63 printing the same mark"),
    "glyph/3/0/6/13/1": ("whole_rest", ""),
    "glyph/3/0/9/1/3": ("whole_rest", ""),
    "glyph/3/1/0/8/4": ("whole_rest", ""),
    "glyph/4/0/0/3/1": ("whole_rest", "= P1 m85; the neighbouring-bar witness catches it, the slot does not"),
    "glyph/4/0/0/4/3": ("whole_rest", "P1 m86 -- ALREADY unwritten before this rule"),
    "glyph/4/0/0/6/2": ("whole_rest", "= P1 m88"),
    "glyph/4/0/0/7/4": ("whole_rest", "= P1 m89"),
    "glyph/4/0/1/1/9": ("whole_rest", ""),
    "glyph/4/0/5/1/3": ("whole_rest", ""),
    "glyph/4/0/5/10/5": ("whole_rest", ""),
    "glyph/4/0/5/6/10": ("whole_rest", ""),
    "glyph/4/1/5/2/1": ("whole_rest", ""),
    "glyph/4/1/5/3/3": ("whole_rest", ""),
    "glyph/4/1/6/14/1": ("whole_rest", ""),
}


def _k(s, n):
    return tuple(int(x) for x in s.split("/")[1:1 + n])


c = json.load(open(SP + "/cache.json"))
box, cls, rest, conf, lines, spacing = {}, {}, {}, {}, {}, {}
for o in c["observations"]:
    q, s = o["quantity"], o["subject"]
    if q == "glyph_box":
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if pb:
            box[s] = pb
    elif q == "notehead_class":
        cls[s] = o["value"]
    elif q == "rest":
        rest[s] = o["value"]
    elif q == "glyph_conf":
        conf[s] = o.get("score")
    elif q == "staff_lines":
        lines[_k(s, 3)] = o["value"]
    elif q == "staff_spacing":
        spacing[_k(s, 3)] = o["value"]
pitch, dur = {}, {}
for v in c["verdicts"]:
    if v["quantity"] == "pitch":
        pitch[v["subject"]] = v
    elif v["quantity"] == "duration":
        dur[v["subject"]] = v


def geom(sub):
    pb, k = box.get(sub), _k(sub, 3)
    ly, sp = lines.get(k), spacing.get(k)
    if not pb or not ly or not sp:
        return None
    h, w = (pb[3] - pb[1]) / sp, (pb[2] - pb[0]) / sp
    if h <= 0:
        return None
    return h, w / h, (max(ly) - (pb[1] + pb[3]) / 2.0) / (sp / 2.0)


# ── the fire set, from the SHIPPED constants ────────────────────────────────
HMAX, AMIN, AMAX, SLOT, NBB, NBS = 0.84, 1.63, 3.09, 1.0, 2, 1.5
wr_by_staff = collections.defaultdict(list)
for s in rest:
    if s in box and str(rest[s]).lower().startswith("restwhole"):
        g = geom(s)
        if g:
            wr_by_staff[_k(s, 3)].append((int(s.split("/")[4]), g[2]))

fires = []
for s in cls:
    g = geom(s)
    if not g:
        continue
    h, asp, step = g
    if not (h <= HMAX and AMIN <= asp <= AMAX):
        continue
    witness = None
    if abs(step - 5.5) <= SLOT:
        witness = "slot"
    else:
        cell = int(s.split("/")[4])
        for c2, st2 in wr_by_staff.get(_k(s, 3), ()):
            if abs(c2 - cell) <= NBB and abs(st2 - step) <= NBS:
                witness = "neighbouring_bar"
                break
    if witness:
        fires.append((s, h, asp, step, witness))
fires.sort()
print("fires:", len(fires))

# ── part / measure, from the exporter's own system map ──────────────────────
smap = {}
for sysrow in json.load(open(SP + "/system-map-base.json"))["systems"]:
    for st in sysrow["staves"]:
        smap[(sysrow["page"], sysrow["system"], st["staff"])] = st

# ── the 26-bar artefact, for the overlap ────────────────────────────────────
a26 = json.load(open(BENCH + "/adjudicated-26.json"))["rows"]
by_sub26 = {r["subject"]: r for r in a26}

rows, already = [], []
for s, h, asp, step, witness in fires:
    p, sy, stf, cell, _ = (int(x) for x in s.split("/")[1:])
    st = smap.get((p, sy, stf))
    verdict, note = VERDICT.get(s, ("NOT_ADJUDICATED", ""))
    pv, dv = pitch.get(s), dur.get(s)
    written = (pv is not None and pv["outcome"] == "decided"
               and dv is not None and dv["outcome"] == "decided")
    if not written:
        already.append((s, "no_pitch" if (pv is None or pv["outcome"] != "decided")
                        else "duration_" + dv["outcome"]))
    rows.append({
        "subject": s,
        "part": st["part_id"] if st else None,
        "measure": (st["first_measure"] + cell) if st else None,
        "printed_at": f"pdf p{p} / system {sy} / staff {stf} / bar {cell}",
        "height_spaces": round(h, 3), "aspect": round(asp, 3),
        "staff_step": round(step, 2), "detector_conf": round(conf.get(s, 0), 3),
        "detector_class": cls[s],
        "witness": witness,
        "verdict": verdict,
        "note": note,
        "in_the_26": by_sub26[s]["verdict"] if s in by_sub26 else None,
        "already_unwritten_before_this_rule": None if written else already[-1][1],
    })

overlap = [r for r in rows if r["in_the_26"]]
newrows = [r for r in rows if not r["in_the_26"]]
print("overlap with the 26:", len(overlap),
      collections.Counter(r["in_the_26"] for r in overlap))
print("new (outside Sean's observed population):", len(newrows))
notehead_fires = [r for r in rows if r["in_the_26"] == "notehead"]
junk_fires = [r for r in rows if r["in_the_26"] == "junk"]
print("⚠️ fires on a row the 26 adjudicated as a REAL NOTE:", len(notehead_fires))
print("   fires on a row the 26 adjudicated as junk:", len(junk_fires))
print("verdicts:", collections.Counter(r["verdict"] for r in rows))
print("already unwritten:", already)

payload = {
    "_README": "THE HAND VERDICT ON EVERY CELL THE SHIPPED RULE FIRES ON. `adjudicated-26.json` is the adjudication of SEAN'S OBSERVED POPULATION; this is the adjudication of the population the rule ACTS ON, and they are different overlapping sets. This is the artefact that licenses deleting notes from a file, so it is committed rather than reported. Each row was looked at on a contact sheet at 34 px per staff space (crops/every-fire-A.png, -B, -C), against the same restWhole and notehead controls the 26 were read against.",
    "_how_the_population_was_derived": "the SHIPPED constants, recomputed offline from the record: height <= 0.84 staff spaces, 1.63 <= aspect <= 3.09, and position established either by |staff_step - 5.5| <= 1.0 or by a restWhole on the same staff within 2 bars and 1.5 staff steps. The arm (`arm.py`) reaches the identical 25 through the real decision, by an independent path: slot 20, neighbouring_bar 5.",
    "_verdicts": {
        "whole_rest": "the page prints a WHOLE REST here and the detector called it a notehead -- the fault the rule exists for",
        "notehead": "the page prints a real note. A fire on one of these is the rule DELETING REAL MUSIC and would change the recommendation.",
        "junk": "the page prints neither -- a spurious detection on other ink",
    },
    "_what_is_NOT_established": [
        "n = 1 document, 1 publisher, 4 pages of ~16, on the low-res bitonal end of the corpus.",
        "The adjudication is one reader's (this session's), against the print, not Sean's.",
        "That the bar is otherwise correct -- only that this glyph is a whole rest.",
    ],
    "record": "library/_shared-records/beethoven5-p1-p4.record.json",
    "record_md5": "d3620ba9cb70fc93f6b7ee91b6cbe40a",
    "summary": {
        "fires": len(rows),
        "verdicts": dict(collections.Counter(r["verdict"] for r in rows)),
        "also_in_adjudicated_26": len(overlap),
        "new_outside_the_26": len(newrows),
        "fires_on_a_row_the_26_called_a_real_note": len(notehead_fires),
        "fires_on_a_row_the_26_called_junk": len(junk_fires),
        "already_unwritten_before_this_rule": len(already),
        "notes_actually_removed_from_the_file": len(rows) - len(already),
    },
    "rows": rows,
}
json.dump(payload, open(SP + "/adjudicated-25-fires.json", "w"), indent=1)
print("\nwrote", SP + "/adjudicated-25-fires.json")
