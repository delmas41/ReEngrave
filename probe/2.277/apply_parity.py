"""one-off (2.277 hold fix): a claim refusal changes the NAME of the first cause, not what its consumers see; a bar that loses a false gap keeps its blue."""
import pathlib
R = pathlib.Path(__file__).resolve().parents[2] / "tools" / "omr" / "staged"


def sub(p, old, new, count=1):
    s = p.read_text()
    assert old in s, (p.name, old[:60])
    p.write_text(s.replace(old, new, count))


# 1. claim_final: the equivalence constant
sub(R / "claim_final.py", "MARK_ONLY = frozenset(", '''#: a box refused BY the barline claim is, to every reader keyed on the SHAPE reason it would have got (`too_narrow`: the meter-column "not a note mark", the
#: dot-shaped box at a head's dot step, the narrow-box eighth-rest look), the same box: the claim renames the first cause, it must not change what those
#: readers do (the 2.277 hold: the sliver's duration fed a bar sum, a neighbour was confirmed by it). Only a layer's OWN ink is "not a note" (page_claim).
SHAPE_EQUIVALENT_REASONS = ("claimed_by:barline",)
MARK_ONLY = frozenset(''')

# 2. rhythm: barline is shape-equivalent; a later layer's ink has no duration
p = R / "adjudicators" / "rhythm.py"
sub(p, '''NOT_A_NOTE_REFUSALS = ("tremolo_slash_crosses_stem", "on_a_dynamic_letter", "claimed_by:barline", "claimed_by:page_claim")''',
    '''NOT_A_NOTE_REFUSALS = ("tremolo_slash_crosses_stem", "on_a_dynamic_letter", "claimed_by:page_claim")''')
sub(p, '''#: ROADMAP 2.277: a box refused BY a barline's (or a later layer's) claimed ink is that mark's ink, never a note: no duration (a Brahms sliver on a barline
#: otherwise got `head_and_marks` quarter once its reason was not the old `too_narrow` in a meter column).''',
    '''#: ROADMAP 2.277: a box refused BY a later layer's claimed ink (a tremolo slash) is that mark's ink, never a note: no duration. A box refused by the BARLINE claim
#: is treated exactly as its `too_narrow` was (`claim_final.SHAPE_EQUIVALENT_REASONS`, below): its duration verdict feeds the same readers as before.''')
sub(p, '''    if refusal.reason != "too_narrow":
        return None''', '''    from .. import claim_final as _CF
    if refusal.reason != "too_narrow" and refusal.reason not in _CF.SHAPE_EQUIVALENT_REASONS:
        return None''')

# 3. aug_dot_join, narrow_rest: the same equivalence
sub(R / "adjudicators" / "aug_dot_join.py", 'DOT_SHAPED_REFUSALS = ("too_narrow", "is_a_dot")', 'DOT_SHAPED_REFUSALS = ("too_narrow", "is_a_dot", "claimed_by:barline")      # 2.277: claim_final.SHAPE_EQUIVALENT_REASONS')
sub(R / "adjudicators" / "narrow_rest.py", '''or refusal.value is not True or refusal.reason != "too_narrow"):''',
    '''or refusal.value is not True or refusal.reason not in ("too_narrow", "claimed_by:barline")):     # 2.277: claim_final.SHAPE_EQUIVALENT_REASONS''')

# 4. export: remember the claim-refused slivers of a bar; a red bar that lost such a gap keeps its blue
p = R / "export.py"
sub(p, '''    unplaced: List[Dict[str, Any]] = field(default_factory=list)


def _clef_changes_by_bar''', '''    unplaced: List[Dict[str, Any]] = field(default_factory=list)
    #: ROADMAP 2.277 (flag `OMR_CLAIM_FINAL`): glyphs of THIS bar refused BY a barline's / a layer's claimed ink (`_CLAIM_GAP_REASONS`): not a gap (the ink is
    #: another mark's), but a bar that stops adding up when the false gap goes keeps what the gap gave it -- its notes stay GUESSED (`_mark_claimed_gap_events`).
    claimed_slivers: List[Dict[str, Any]] = field(default_factory=list)


def _clef_changes_by_bar''')
sub(p, '''    boxes = {o["subject"]: o["value"] for o in rec.obs_of(Q.GLYPH_BOX)}
    for sub, reason in fates.items():
        if reason in ("written", "written_relocated") \\
                or reason in _NOT_A_GAP_REASONS:
            continue''', '''    boxes = {o["subject"]: o["value"] for o in rec.obs_of(Q.GLYPH_BOX)}
    for sub, reason in fates.items():
        if reason in _CLAIM_GAP_REASONS:
            v = boxes.get(sub)
            s = _parse_subject(sub)
            run = runs.get(_staff_key(s["page"] or 0, s["system"] or 0, s["staff"] or 0))
            cell = run.cells.get(s["cell"] or 0) if run is not None else None
            if cell is not None and v and len(v) == 5:
                cell.claimed_slivers.append({"sub": sub, "reason": reason, "x": float(v[1]) + float(v[3]) / 2.0})
            continue
        if reason in ("written", "written_relocated") \\
                or reason in _NOT_A_GAP_REASONS:
            continue''')
sub(p, '''def _attach_unplaced(rec: Record,''', '''#: ROADMAP 2.277: the fates of a box refused BY a barline's / a later layer's claimed ink (in `_NOT_A_GAP_REASONS`: no unread gap)
_CLAIM_GAP_REASONS = frozenset({
    "not_a_notehead:claimed_by:barline", "not_a_rest:claimed_by:barline",
    "not_a_notehead:claimed_by:page_claim", "not_a_rest:claimed_by:page_claim"})


def _mark_claimed_gap_events(events: List[Dict[str, Any]]) -> int:
    """ROADMAP 2.277 (the hold, Brahms p8 m47: a dotted half read as a half): a false unread gap used to put a bar's kept notes in blue
    (`_mark_kept_onsets`); refusing the sliver by its claim removes the gap, and a bar that then does NOT add up would write the same notes
    plain READ. A claim may remove a gap, never promote a neighbour from GUESSED to READ: every event of such a bar without a guess of its own is
    GUESSED, the rule named apart so the report counts it. Returns how many events it marked."""
    n = 0
    g = {"stage": "EXPORT", "rule": "bar_sum_wrong_after_claimed_gap", "quantity": "onset", "candidates": [], "chosen": {}}
    for ev in events:
        if ev.get("kind") == "rest":
            det = ev.get("rest")
            if isinstance(det, dict) and not det.get("guess"):
                det["guess"] = dict(g)
                n += 1
            continue
        for h in ev.get("noteheads") or ():
            if not h.get("guess"):
                h["guess"] = dict(g)
                n += 1
    return n


def _attach_unplaced(rec: Record,''')
sub(p, '''                if red:
                    # ⚠️⚠️ ROADMAP 2.173. WRITTEN WITH EXACTLY WHAT WAS READ:''', '''                if red and cell_here is not None and cell_here.claimed_slivers:
                    counters["claimed_gap_events_kept_blue"] = counters.get("claimed_gap_events_kept_blue", 0) + _mark_claimed_gap_events(events)
                if red:
                    # ⚠️⚠️ ROADMAP 2.173. WRITTEN WITH EXACTLY WHAT WAS READ:''')
print("ok")
