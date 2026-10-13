p='tools/omr/staged/adjudicators/family_precision.py'
s=open(p).read()
a='''    box_row = _glyph_box_row(ev)
    if box_row is not None:
        dup = _duplicate_box_refusal(ev, box_row, detail)
        if dup is not None:
            return dup
        clipped = _rest_clipped_by_crop_refusal(ev, box_row, detail)'''
assert a in s
s=s.replace(a,'''    box_row = _glyph_box_row(ev)
    if box_row is not None:
        # ROADMAP 2.100, AFTER the human and BEFORE every rest rule: nothing
        # but a clef stands before a key signature's accidentals (Sean,
        # 2026-10-12), so a rest-named box in the signature's slots is the
        # signature's own ink boxed under a second name. Geometry of the
        # header, never the bar sum (`key_slots` module docstring).
        in_key = _key_slots.key_slot_occupant(ev, box_row)
        if in_key is not None:
            detail.update(in_key["detail"])
            return Ruling(value=True, reason="rest_in_a_key_signature_slot",
                          used=(box_row.id,) + in_key["used"], detail=detail)
        dup = _duplicate_box_refusal(ev, box_row, detail)
        if dup is not None:
            return dup
        clipped = _rest_clipped_by_crop_refusal(ev, box_row, detail)''',1)
b='''                                     "rest_is_a_duplicate_box",
                                     "rest_is_a_slashed_stem",'''
assert b in s
s=s.replace(b,'''                                     "rest_is_a_duplicate_box",
                                     "rest_in_a_key_signature_slot",
                                     "rest_is_a_slashed_stem",''',1)
c="from .notehead_precision import (HUMAN_OTHER_STAFF"
assert c in s
s=s.replace(c,"from . import key_slots as _key_slots\n"+c,1)
open(p,'w').write(s)
p='tools/omr/staged/adjudicators/notehead_precision.py'
s=open(p).read()
a='''    spacing = _cell_staff_space(ev)
    if spacing is None:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)

    detail: Dict[str, Any] = {"class": box_row.value[0]}
    used = [box_row.id]
'''
assert s.count(a)==1
s=s.replace(a,'''    # ROADMAP 2.100: nothing but a clef stands before a key signature's
    # accidentals (Sean, 2026-10-12). A notehead-named box in the signature's
    # slots is a flat's bowl boxed under a second name. It needs no unit of
    # its own beyond the cell's (`key_slots.key_slot_occupant` returns `None`
    # without one), so it sits before the guard like `is_a_clef`.
    in_key = _key_slots.key_slot_occupant(ev, box_row)
    if in_key is not None:
        return Ruling(value=True, reason="notehead_in_a_key_signature_slot",
                      used=(box_row.id,) + in_key["used"],
                      detail={"class": box_row.value[0], **in_key["detail"]})

'''+a,1)
b='''                                     "is_a_meter_digit",
                                     TIMESIG_DIGIT_DUPLICATE_REASON,'''
assert b in s
s=s.replace(b,'''                                     "is_a_meter_digit",
                                     "notehead_in_a_key_signature_slot",
                                     TIMESIG_DIGIT_DUPLICATE_REASON,''',1)
c="from . import ownership as _ledger"
assert c in s
s=s.replace(c,c+"\nfrom . import key_slots as _key_slots",1)
open(p,'w').write(s)
print('ok')
