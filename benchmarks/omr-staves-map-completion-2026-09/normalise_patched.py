"""PROBE-ONLY patches to `page_normalise`, so the Mahler ceiling can be priced.

⚠️ THIS IS NOT THE FIX AND MUST NOT BECOME IT. `page_normalise.py` is owned by
the headline-validity workstream; these two patches exist so this benchmark can
answer "what would a Mahler map be worth" without editing that module. Both are
one-liners and both are reported in FINDINGS.md for its owner to take or refuse.

FAULT B — `_tokens` sorts a heterogeneous key.
    `out.append((off, dur, body))` where `body` is the STRING "R" for a rest and
    a TUPLE of pitch names otherwise, then `sorted(out)`. Two events sharing
    (offset, duration) and differing in kind therefore compare `str` against
    `tuple` and raise `TypeError`.
    ⚠️ It needs the two events to be in the SAME measure, which is why no
    already-mapped row reached it: it takes a source part whose bar already has
    two VOICES, one resting where the other sounds. Mahler's `Vier Trompeten in
    B.` writes exactly that (p3 mm 12 and 14, p4 mm 17-19).
    Patch: give a rest the tuple body `("R",)`, so every third element is a
    tuple of strings. Order changes for no bar that previously sorted, because
    a str and a tuple never compared successfully before.

FAULT A — `_voice_merge` inserts a deepcopy that still points at its old site.
    `v.insert(el.getOffsetInHierarchy(m), copy.deepcopy(el))`: the copy carries
    an `activeSite` reference music21's `sortTuple()` then looks up in the
    copy's own `sites` dict, and raises `KeyError: <id>` when it is not there.
    Fires on Mahler p3's `Sechs Hörner in F.` mm 15-16 (unaligned divisi, no
    nested voices), and NOT on p5 m31 which is the same shape — so it is a
    latent music21 usage fault, not a property of the map.
    Patch: clear `activeSite` on the copy before inserting it.
"""
from __future__ import annotations

import copy
from fractions import Fraction

from music21 import chord, note, stream

import page_normalise as pn

_ORIG_TOKENS = pn._tokens
_ORIG_VOICE_MERGE = pn._voice_merge


def _tokens(measure):
    out = []
    for el in measure.recurse().notesAndRests:
        off = Fraction(el.getOffsetInHierarchy(measure)).limit_denominator(10080)
        dur = Fraction(el.duration.quarterLength).limit_denominator(10080)
        if isinstance(el, note.Rest):
            body = ("R",)                       # FAULT B: was the bare str "R"
        elif isinstance(el, chord.Chord):
            body = tuple(sorted(p.nameWithOctave for p in el.pitches))
        elif isinstance(el, note.Note):
            body = (el.pitch.nameWithOctave,)
        else:
            # FAULT C: an `Unpitched` note (every one-line percussion part in
            # the Mahler reference) is neither Note, Rest nor Chord, and the
            # shipped branch reaches for `.pitch`.
            body = ("UNPITCHED",
                    str(getattr(el, "displayStep", "")),
                    str(getattr(el, "displayOctave", "")))
        out.append((off, dur, body))
    return tuple(sorted(out))


def _voice_merge(measures):
    sounding = [m for m in measures if not pn._is_silent(m)]
    base = copy.deepcopy(sounding[0])
    out = stream.Measure(number=base.number)
    for el in base:
        if isinstance(el, (note.Note, note.Rest, chord.Chord, stream.Voice)):
            continue
        out.insert(el.offset, copy.deepcopy(el))
    for i, m in enumerate(sounding):
        v = stream.Voice(id=str(i + 1))
        for el in m.recurse().notesAndRests:
            off = el.getOffsetInHierarchy(m)
            c = copy.deepcopy(el)
            c.activeSite = None                 # FAULT A
            v.insert(off, c)
        out.insert(0.0, v)
    return out


def apply() -> None:
    pn._tokens = _tokens
    pn._voice_merge = _voice_merge


def restore() -> None:
    pn._tokens = _ORIG_TOKENS
    pn._voice_merge = _ORIG_VOICE_MERGE
