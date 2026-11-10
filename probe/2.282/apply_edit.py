"""One-off: apply the 2.282 flag edits (OMR_CLAIM_ORDER) to the two stroke-owner modules. Idempotent (asserts each anchor occurs once)."""
import sys


def sub(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:70])
    return s.replace(old, new)


p = "tools/omr/staged/stroke_owner.py"
s = open(p).read()
if "ENV_ORDER" not in s:
    s = sub(s, '''CONSUMERS = ("stem", "beam", "flag")
AREA_OWNERS = TIERS[0]''', '''CONSUMERS = ("stem", "beam", "flag")
AREA_OWNERS = TIERS[0]

# ROADMAP 2.282 (flag `OMR_CLAIM_ORDER`, default OFF = today's behaviour exactly): which of heads / accidentals claims first, and what a stroke BOTH fit does.
#: TODAY (flag unset): heads stand before accidentals in the order, but the order never PICKS -- two families that both fit a stroke and no one clear
#: fit leave it CONTESTED (abstained, both candidates kept), so the order acts only through the ATTACHED strokes and the yields.
#: `heads_first` / `accidentals_first`: the order DECIDES -- among the families that fit a stroke, the first in the claim order owns it (a stroke only
#: one family fits, or only one CLEARLY fits, is unchanged). `accidentals_first` also moves the accidental tier before the head/ledger tier, and
#: (adjudicators/stroke_owner._claim_final) lets a decided accidental claim hold a head box's ink like any earlier claim. A MICRO TEST, never a default.
ENV_ORDER = "OMR_CLAIM_ORDER"
ORDER_MODES = ("heads_first", "accidentals_first")


def claim_order_mode() -> str:
    """`OMR_CLAIM_ORDER`: "" (off, today), "heads_first" or "accidentals_first"; anything else is off."""
    import os
    v = os.environ.get(ENV_ORDER, "").strip().lower()
    return v if v in ORDER_MODES else ""


def tiers_for_order(tiers: Sequence[Sequence[str]], mode: str) -> Tuple[Tuple[str, ...], ...]:
    """`tiers` with the accidental tier moved in front of the head / ledger tier under `accidentals_first`; unchanged otherwise."""
    out = [tuple(t) for t in tiers]
    if mode != "accidentals_first":
        return tuple(out)
    a = [i for i, t in enumerate(out) if "accidental" in t]
    h = [i for i, t in enumerate(out) if "head" in t]
    if not a or not h or a[0] < h[0]:
        return tuple(out)
    acc = out.pop(a[0])
    out.insert(h[0], acc)
    return tuple(out)''')
    s = sub(s, "def _settle(o: int, cand: Dict[int, List[Dict[str, object]]], tier_index: Dict[str, int]) -> Ownership:",
            "def _settle(o: int, cand: Dict[int, List[Dict[str, object]]], tier_index: Dict[str, int], resolve: bool = False) -> Ownership:")
    s = sub(s, '''        pick = clear[0] if len(clear) == 1 else None
    if pick is None:
        return Ownership(o, "contested", candidates=tuple(cs), row_ids=rows)''', '''        pick = clear[0] if len(clear) == 1 else None
    if pick is None and resolve:
        # 2.282 (`OMR_CLAIM_ORDER`): the claim ORDER decides -- the first family (candidates are listed in claim order) that fits owns the stroke
        pick = fams[0]
        keys = tuple(dict.fromkeys(str(c["key"]) for c in fits if c["family"] == pick))
        return Ownership(o, "merged" if len(keys) > 1 else "decided", pick, keys, tuple(cs), "order", rows)
    if pick is None:
        return Ownership(o, "contested", candidates=tuple(cs), row_ids=rows)''')
    s = sub(s, "acc_bar_clear_of_note: bool = False, vetoes: Optional[Dict[str, Veto]] = None) -> Dict[int, Ownership]:",
            "acc_bar_clear_of_note: bool = False, vetoes: Optional[Dict[str, Veto]] = None, resolve: bool = False) -> Dict[int, Ownership]:")
    s = sub(s, 'head_owned = {o for o in by_ord if _settle(o, cand, tier_index).family == "head"}',
            'head_owned = {o for o in by_ord if _settle(o, cand, tier_index, resolve).family == "head"}')
    s = sub(s, "out: Dict[int, Ownership] = {o: _settle(o, cand, tier_index) for o in by_ord}",
            "out: Dict[int, Ownership] = {o: _settle(o, cand, tier_index, resolve) for o in by_ord}")
    open(p, "w").write(s)

p = "tools/omr/staged/adjudicators/stroke_owner.py"
s = open(p).read()
if "order_mode" not in s:
    s = sub(s, '''    owned = SO.own_strokes(inks, claims, tiers=tiers, acc_bar_clear_of_note=beams_from_strokes_enabled(),   # 2.202f
                           vetoes=vetoes)''', '''    order_mode = SO.claim_order_mode()                  # ROADMAP 2.282 (flag OMR_CLAIM_ORDER, default OFF): "" = today
    tiers = SO.tiers_for_order(tiers, order_mode)
    owned = SO.own_strokes(inks, claims, tiers=tiers, acc_bar_clear_of_note=beams_from_strokes_enabled(),   # 2.202f
                           vetoes=vetoes, resolve=bool(order_mode))''')
    s = sub(s, '''    held = CF.held_boxes(boxes, claim_families)
    keys = {c.key''', '''    held = CF.held_boxes(boxes, claim_families)
    if SO.claim_order_mode() == "accidentals_first":
        # ROADMAP 2.282: a decided ACCIDENTAL claim holds a HEAD box's ink like any earlier claim (heads only: a rest or a dot over a sign stays 2.192's)
        acc = CF.held_boxes([b for b in boxes if b[1] == "head"], ["accidental"])
        for k, e in acc.items():
            if k not in held or e["share"] > held[k]["share"]:
                held[k] = e
        claim_families = sorted(set(claim_families) | {"accidental"})
    keys = {c.key''')
    open(p, "w").write(s)
print("edits applied")
