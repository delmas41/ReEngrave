"""ROADMAP 2.120 round 2 -- the elimination table after Sean's answers (SEAN-ANSWERS-2026-10-14.md) and the
measured widening of the round-1 numbers that dropped true marks. DESIGN ONLY: nothing under tools/ reads this.

table.py (round 1) is kept untouched; this module copies it and applies CHANGES, so before/after is the diff.

New concepts
  PRIOR  -- 'normal' | 'rare' | 'very_rare'. A rare thing is KEPT in the candidate set and never eliminates; it is
            flagged so a consumer asks for stronger evidence before choosing it (Sean: "not standard / exceptions /
            very rare" = keep, low prior). Two ways to be rare: the whole symbol (arpeggiato), or one allowance
            (EXTRA) lifting a loc/zone rule only in some places (a dynamic on the staff; a word on the staff).
  EXTRA  -- per symbol: allowances that LIFT a loc or zone rule. {loc|zone|needs_left_edge: ..., prior, src}.
            A mark that survives only through a 'rare' allowance is reported in `rare`, and `common` omits it.
  KINDS  -- CONV (a convention / Sean ruling; may eliminate), CUT (a measured number; may only narrow),
            ASK (assumed, unanswered; treated as CUT).
"""
import copy
import table as T1

INF = float("inf")
EDGE_RULES = dict(T1.EDGE_RULES)
symbol_of = T1.symbol_of
MARGIN = 0.15  # measured widening: new bound = 1.15 x (or 0.85 x) the truth extreme, only where round 1 dropped a true mark


CHANGES = []   # (symbol, field, old, new, kind, why); filled by build()


def alt(S, name, a, kind, why):
    S[name].setdefault("alts", []).append(a)
    CHANGES.append((name, "alt envelope", "-", "w %.2f-%.2f h %.2f-%.2f fill %.2f-%.2f" % (a["env"] + a["fill"]), kind, why))


def chg(S, name, field, new, kind, why):
    s = S[name]
    if field.startswith("env"):
        i = int(field[3]); old = s["env"][i]; e = list(s["env"]); e[i] = new; s["env"] = tuple(e)
    elif field.startswith("fill"):
        i = int(field[4]); old = s["fill"][i]; f = list(s["fill"]); f[i] = new; s["fill"] = tuple(f)
    else:
        old = s[field]; s[field] = new
    CHANGES.append((name, field, old, new, kind, why))



def apply_sean(S):
    # ---- Sean's answers (SEAN-ANSWERS-2026-10-14.md) ------------------------------------------------------------
    # 5. hairpin never inside the staff: unchanged (locs NEAR/FAR) but now a Sean ruling, not the registry's reading.
    S["hairpin"]["src"] = "Sean 2026-10-14 Q5 'no' (hairpin never inside the staff); registry 'dynamics are not placed INSIDE the staff'"
    # 11. brace/bracket ONLY at the system's left edge: zone rule replaced by a left-edge rule (CONV, Sean).
    S["brace"]["zones"] = tuple(T1.ZONES)          # zone is no longer the test ...
    S["brace"]["needs_left_edge"] = True           # ... the left edge is
    S["brace"]["zone_kind"] = "CONV"
    S["brace"]["src"] = "Sean 2026-10-14 Q11 'only left that I know of' (brace/bracket only at the system's left edge)"
    CHANGES.append(("brace", "zones", "MARGIN/BARTAIL (ASK)", "left edge only (CONV, Sean Q11)", "CONV",
                    "BARTAIL removed: a brace at the right edge is eliminated; first-bar cell starts AT the brace so KEYSLOT must not eliminate it"))
    # 3. dynamics inside the five lines: not standard, exceptions exist -> allowed, RARE.
    S["dynamic_letter"]["extra"].append(dict(loc="IN", prior="rare", src="Sean Q3 'not standard' + 'there are exceptions'"))
    # 4. direction word on the staff lines: exceptions -> allowed, RARE. Margin labels (instrument names) stand level with
    #    their staff: normal (round 1 table bug, 10 true marks).
    S["text"]["extra"].append(dict(loc="IN", zone=("MARGIN",), prior="normal", src="margin instrument labels stand level with the staff (10 truth marks); round-1 bug"))
    S["text"]["extra"].append(dict(loc="IN", prior="rare", src="Sean Q4 'there are exceptions'"))
    # 10. arpeggio line: possible but very very rare -> keep, whole symbol very_rare.
    S["arpeggiato"]["prior"] = "very_rare"
    S["arpeggiato"]["src"] += "; Sean Q10 'possible but would be very very rare'"
    # 6/7. rests outside the staff, whole/half rest not pinned to its lines, a 2nd voice's hangs off the bottom: KEEP.
    for n in ("rest_block", "rest_quarter", "rest_hook"):
        S[n]["loc_kind"] = "CUT"      # no longer an ASK: Sean Q6 'yes' (outside the staff is real); the NEAR bound itself is a number
    S["rest_block"]["src"] += "; Sean Q6/Q7 'yes' (a second voice's rest can stand outside / hang off the bottom of the staff) -> no line pinning, NEAR kept"
    CHANGES.append(("rest_block/quarter/hook", "locs", "IN/NEAR (ASK)", "IN/NEAR (kept; Sean Q6,Q7)", "CUT",
                    "confirmed: rests outside the staff and a whole/half rest hanging off the bottom stay; the 8 sp NEAR bound is still a cut-off"))
    # 8. clef mid-bar: zones already NOT_MARGIN (KEEP). 9. courtesy accidental after clef+key: allow in KEYSLOT, RARE-looking
    #    but Sean said 'yes' -> normal allowance, but only counted as an accidental, never a key accidental.
    S["accidental"]["extra"].append(dict(zone=("KEYSLOT",), prior="normal", src="Sean Q9 'yes' (courtesy accidental after the clef and key, before the first note)"))
    S["accidental"]["zone_kind"] = "CONV"
    CHANGES.append(("accidental", "zones", "no KEYSLOT", "KEYSLOT allowed (Sean Q9)", "CONV", "courtesy accidental after the key"))
    CHANGES.append(("clef", "zones", "NOT_MARGIN", "unchanged (Sean Q8: mid-bar clef is real)", "CONV", "kept"))
    CHANGES.append(("hairpin", "locs", "NEAR/FAR", "unchanged (Sean Q5: eliminated inside the staff)", "CONV", "now a ruling"))
    CHANGES.append(("dynamic_letter", "locs", "NEAR/FAR", "+IN as RARE allowance (Sean Q3)", "CONV", "never eliminates"))
    CHANGES.append(("text", "locs", "NEAR/FAR", "+IN: normal in MARGIN, RARE elsewhere (Sean Q4)", "CONV", "never eliminates"))
    CHANGES.append(("arpeggiato", "prior", "normal", "very_rare (Sean Q10)", "CONV", "kept, flagged"))



def apply_widen(S):
    # ---- the round-1 numbers that eliminated a TRUE mark, widened from the truth distribution (derive.py) ---------
    # new = 1.15 x truth max (upper) / 0.85 x truth min (lower), never tighter than before. Every one is a CUT: narrows only.
    chg(S, "dynamic_letter", "env1", 14.29, "CUT", "truth 1.94-12.43 sp (n17): Sean boxes a dynamic WORD as one dynamicF/P box (q159 q299 q922)")
    # tie / beam: a GLOBAL widening would let ~320 / ~65 / ~42 other marks into the set for 3 / 1 / 1 recovered true marks
    # (measure2/onebyone.py), so each is an ALTERNATIVE envelope that applies only to the shape that was measured.
    alt(S, "tie", dict(env=(0.9, 1.6, 0.3, 0.6), fill=(0.03, 0.83)), "CUT",
        "SHORT tie end (truth: w 1.13-1.36, h 0.38-0.52, fill 0.60-0.72 = 1.15 x 0.72): arrives at a barline / lies on a staff line, reads thick (q648 q660 q710)")
    alt(S, "tie", dict(env=(8.0, INF, 0.12, 2.75), fill=S["tie"]["fill"]), "CUT",
        "LONG tie (w >= 8 sp): arcs higher, truth h 2.39 (b4010) x 1.15 = 2.75")
    chg(S, "barline", "fill0", 0.11, "CUT", "truth 0.13-0.82 (n31): a long thin box over a tilted barline is mostly paper (b4161 q405)")
    chg(S, "barline", "env2", 1.22, "CUT", "truth h 1.43-15.68 (n31 incl. q880, Sean: 'only barline'): a boxed barline FRAGMENT")
    chg(S, "flag", "env1", 2.37, "CUT", "truth w 0.92-2.06 (n42): a real wide flag (q399)")
    alt(S, "beam", dict(env=(3.8, INF, 0.20, INF), fill=S["beam"]["fill"]), "CUT",
        "WIDE flat beam piece (w >= 3.8 sp, wider than any ledger 3.6): truth h 0.23 (q871) x 0.85 = 0.20; ledger/beam by height stays at 0.25 for short boxes")




def apply_detector(S):
    """DETECTOR-box widening (measure2/detector.py): the unit is a detector box + its ink, and the detector's boxes are
    PARTIAL where Sean's are tight. Measured on the same Brahms p0 page as the evaluation, so NOT out of sample."""
    chg(S, "meter_digit", "env2", 0.87, "CUT", "detector boxes on 8/6 time-signature digits are 1.02-1.08 sp tall (truth digits are taller): 0.85 x 1.02 (3 correct detections + 2 refused whole-note boxes were eliminated)")
    chg(S, "rest_hook", "env1", 2.38, "CUT", "detector box on an eighth rest 2.07 sp wide (q818, IoU 0.65): 1.15 x 2.07")


def apply_litolff(S):
    """Second publisher: Sean's Litolff 984073 idx 1 hollow TEST heads (49 clean) have ink fill 0.64-0.88 (the hole is a sliver,
    page-facts s3) -- the Breitkopf-derived 0.85 cap dropped 3/49. 1.15 x 0.88 = 1.01 -> capped at 1.0. Measured on the SAME cells it is
    then scored on, so NOT out of sample; and at 1.0 the fill axis no longer separates head_half from head_black at all on this plate."""
    chg(S, "head_half", "fill1", 1.0, "CUT", "Litolff hollow heads fill 0.64-0.88 (n49): 1.15 x 0.88 = 1.01 -> 1.0; centre-40% fill 0.16-1.00, so fill cannot split hollow from black on this plate")


def build(sean=True, widen=True, detector=True, litolff=True):
    """A fresh symbol dict: round-1 table + (Sean's answers) + (measured widening). Fills CHANGES on the full build."""
    S = copy.deepcopy(T1.S)
    for s in S.values():
        s.setdefault("prior", "normal"); s.setdefault("extra", []); s.setdefault("needs_left_edge", False)
    del CHANGES[:]
    if sean: apply_sean(S)
    if widen: apply_widen(S)
    if detector: apply_detector(S)
    if litolff: apply_litolff(S)
    return S


SYMBOLS = build()
S = SYMBOLS

def _lift(d, name, s, why):
    """Which extras lift the loc rule / the zone rule for this mark; returns (loc_ok, zone_ok, priors_used)."""
    loc_ok = d.get("loc") in s["locs"]
    zone_ok = d.get("zone") in s["zones"]
    prior = []
    for e in s["extra"]:
        if "loc" in e and not loc_ok and d.get("loc") == e["loc"] and ("zone" not in e or d.get("zone") in e["zone"]):
            loc_ok = True; prior.append(e["prior"])
        if "zone" in e and "loc" not in e and not zone_ok and d.get("zone") in e["zone"]:
            zone_ok = True; prior.append(e["prior"])
    return loc_ok, zone_ok, prior


def candidates(d, SYMBOLS=None):
    SYMBOLS = SYMBOLS or globals()['SYMBOLS']
    """-> ({'conv','all','common','rare'}, trace). conv = convention rules only; all = + cuts (incl. rare allowances);
    common = all minus symbols that survive only through a RARE allowance or are rare symbols; rare = all - common."""
    trace, rare_via = {}, {}
    for name, s in SYMBOLS.items():
        why = []
        w0, w1, h0, h1 = s["env"]
        if d.get("w") is not None and not (w0 <= d["w"] <= w1):
            why.append(("CUT", "width %.2f not in %.2f-%.2f" % (d["w"], w0, w1)))
        if d.get("h") is not None and not (h0 <= d["h"] <= h1):
            why.append(("CUT", "height %.2f not in %.2f-%.2f" % (d["h"], h0, h1)))
        f0, f1 = s["fill"]
        if d.get("fill") is not None and not (f0 <= d["fill"] <= f1):
            why.append(("CUT", "fill %.2f not in %.2f-%.2f" % (d["fill"], f0, f1)))
        if why and d.get("w") is not None:
            for a in s.get("alts", []):
                e0, e1, e2, e3 = a["env"]
                if e0 <= d["w"] <= e1 and e2 <= d["h"] <= e3 and a["fill"][0] <= d["fill"] <= a["fill"][1]:
                    why = []
                    break
        loc_ok, zone_ok, pri = _lift(d, name, s, why)
        if d.get("loc") and not loc_ok:
            lattice_only = (d["loc"] == "IN") or (s["locs"] == ("IN",))
            why.append((s["loc_kind"] + ("" if lattice_only else "+CUT"), "loc %s not in %s" % (d["loc"], "/".join(s["locs"]))))
        if d.get("zone") and not zone_ok and not s["needs_left_edge"]:
            why.append((s["zone_kind"] + "+CUT", "zone %s not in %s" % (d["zone"], "/".join(s["zones"]))))
        if s["needs_left_edge"] and d.get("left_edge") is False:
            why.append((s["zone_kind"], "not at the system's left edge (xs %.1f sp)" % d.get("xs", 0)))
        if EDGE_RULES.get(name) and d.get("edge") is False:
            why.append(("CONV+CUT", "not at a bar boundary"))
        trace[name] = why
        rare_via[name] = ("rare" in pri) or s["prior"] != "normal"
    conv = {n for n, w in trace.items() if not any(k == "CONV" for k, _ in w)}
    allr = {n for n, w in trace.items() if not w}
    rare = {n for n in allr if rare_via[n]}
    return {"conv": conv, "all": allr, "common": allr - rare, "rare": rare}, trace
