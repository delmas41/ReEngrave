"""ROADMAP 2.120 -- the elimination table, as data. DESIGN ONLY: nothing under tools/ reads this.

One mark (a box on the PAGE raster, never a raw ink component) is described by four coarse
descriptors (descriptors.py). Each SYMBOL below says which values of each descriptor it can take.
The candidate set of a mark = every symbol none of whose rules excludes it.

Every rule carries a KIND:
  CONV  -- rests on an engraving convention (docs/page-facts.md, tools/omr/conventions.py registry,
           a Sean ruling). May DECIDE (eliminate on its own).
  CUT   -- rests on a number (an envelope in staff spaces, an ink-fill bin). May only NARROW.
  ASK   -- ASSUMED by the designer, not in any doc. Treated as CUT; a question for Sean in TABLE.md.

The numbers are NOT tuned on Brahms 317803 pdf 0 (the measuring page). They are the dossier /
convention figures widened by roughly a third, written before any measurement. A failure on the
truth page is a bug in this table and is reported, not tuned away.

Units: sp = the local staff space measured at the subject's x (page-facts §3 'measure locally').
(Rebuilt verbatim 2026-10-14 after the /private/tmp wipe.)
"""

INF = float("inf")

LOCS = ("IN", "NEAR", "FAR")
ZONES = ("MARGIN", "KEYSLOT", "HEADER", "BARHEAD", "BARTAIL", "BODY")
NOT_MARGIN = ("KEYSLOT", "HEADER", "BARHEAD", "BARTAIL", "BODY")
MUSIC_NO_KEYSLOT = ("HEADER", "BARHEAD", "BARTAIL", "BODY")

S = {}


def sym(name, *, env, fill, locs, zones, loc_kind, zone_kind, src, words):
    S[name] = dict(env=env, fill=fill, locs=tuple(locs), zones=tuple(zones),
                   loc_kind=loc_kind, zone_kind=zone_kind, src=src, words=words)


sym("head_black", env=(0.9, 2.4, 0.3, 1.6), fill=(0.45, 1.0), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV",
    src="noteheads dossier §1 (h 0.61-1.12, w p5-p95 1.26-1.78, partial boxes to 0.34 h); too_narrow 1.0 sp "
        "0/103 cost; 'no far note without a ledger'; 'only a clef stands before the key accidentals'",
    words="filled notehead")
sym("head_half", env=(0.9, 2.4, 0.3, 1.6), fill=(0.15, 0.85), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="noteheads dossier; Litolff hole is a sliver (page-facts §3)",
    words="half-note head (hollow, stemmed)")
sym("head_whole", env=(1.2, 3.0, 0.3, 1.6), fill=(0.15, 0.85), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A whole notehead is wider than a black one'",
    words="whole-note head (hollow, no stem)")
sym("rest_block", env=(0.7, 2.4, 0.2, 1.0), fill=(0.45, 1.0), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="ASK", zone_kind="CONV", src="registry 'A whole rest HANGS under the 4th line; a half rest SITS'",
    words="whole / half rest (the block)")
sym("dot", env=(0.12, 0.8, 0.12, 0.8), fill=(0.3, 1.0), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="DOT_SIZED_MAX_SPACES 0.75 (2.59); confusables doc DOT row",
    words="dot (augmentation or staccato)")
sym("stem", env=(0.02, 0.6, 1.5, INF), fill=(0.15, 1.0), locs=LOCS, zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A stem is never shorter than 2.5 staff spaces' (widened)",
    words="stem")
sym("barline", env=(0.02, 0.9, 3.0, INF), fill=(0.15, 1.0), locs=("IN", "NEAR"), zones=ZONES,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A barline runs the FULL HEIGHT of its system'; edge required",
    words="barline")
sym("ledger", env=(0.9, 3.6, 0.02, 0.7), fill=(0.15, 1.0), locs=("NEAR",), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A ledger line is only ever OUTSIDE the staff'",
    words="ledger line")
sym("tenuto", env=(0.7, 2.2, 0.02, 0.6), fill=(0.2, 1.0), locs=LOCS, zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="confusables doc HORIZONTAL STROKE", words="tenuto dash")
sym("beam", env=(0.6, INF, 0.25, INF), fill=(0.2, 1.0), locs=LOCS, zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'Stacked beams are set 0.75 sp centre to centre'",
    words="beam")
sym("tremolo", env=(0.5, 2.6, 0.25, 2.6), fill=(0.2, 1.0), locs=LOCS, zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A TREMOLO rides the stem'", words="tremolo slash")
sym("arpeggiato", env=(0.25, 1.4, 2.0, INF), fill=(0.1, 0.8), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="ASK", zone_kind="CONV", src="articulations dossier arpeggiato", words="arpeggio wavy line")
sym("brace", env=(0.2, 3.5, 3.0, INF), fill=(0.1, 1.0), locs=LOCS, zones=("MARGIN", "BARTAIL"),
    loc_kind="CONV", zone_kind="ASK", src="structure dossier brace/bracket", words="brace / bracket")
sym("tie", env=(0.7, INF, 0.12, 2.2), fill=(0.03, 0.6), locs=LOCS, zones=NOT_MARGIN,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A TIE is drawn shallow and close to its two heads'",
    words="tie")
sym("slur", env=(0.7, INF, 0.12, INF), fill=(0.02, 0.6), locs=LOCS, zones=NOT_MARGIN,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A slur is drawn OVER its notes'", words="slur")
sym("hairpin", env=(1.5, INF, 0.3, 3.5), fill=(0.02, 0.35), locs=("NEAR", "FAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'dynamics are not placed INSIDE the staff'",
    words="hairpin (cresc./dim. wedge)")
sym("accent", env=(0.7, 2.4, 0.35, 1.5), fill=(0.08, 0.6), locs=LOCS, zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'An ACCENT is note-anchored'", words="accent / marcato")
sym("fermata", env=(1.3, 3.8, 0.7, 2.4), fill=(0.08, 0.6), locs=LOCS, zones=NOT_MARGIN,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A FERMATA hangs over whatever sounds beneath it'",
    words="fermata")
sym("accidental", env=(0.3, 1.7, 1.4, 4.2), fill=(0.1, 0.8), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="ASK", src="registry 'An accidental stands BEFORE its note'",
    words="accidental (sharp/flat/natural)")
sym("key_accidental", env=(0.3, 1.7, 1.4, 4.2), fill=(0.1, 0.8), locs=("IN", "NEAR"),
    zones=("KEYSLOT", "HEADER", "BARHEAD", "BARTAIL"), loc_kind="CONV", zone_kind="CONV",
    src="registry 'A key signature stands BETWEEN the clef and the meter'", words="key-signature accidental")
sym("clef", env=(1.0, 4.5, 2.2, 9.0), fill=(0.08, 0.7), locs=("IN", "NEAR"), zones=NOT_MARGIN,
    loc_kind="CONV", zone_kind="ASK", src="clefs dossier", words="clef")
sym("meter_digit", env=(0.7, 3.2, 1.2, 4.6), fill=(0.15, 0.8), locs=("IN",),
    zones=("KEYSLOT", "HEADER", "BARHEAD", "BARTAIL"), loc_kind="CONV", zone_kind="CONV",
    src="registry 'A TIME-SIGNATURE digit stands INSIDE'; 'mid-staff meter CHANGE at the bar head'",
    words="time-signature digit")
sym("flag", env=(0.4, 1.9, 1.2, 5.0), fill=(0.1, 0.8), locs=LOCS, zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A FLAG ... hangs on the STEM'", words="flag")
sym("rest_quarter", env=(0.5, 1.7, 1.8, 4.0), fill=(0.15, 0.85), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="ASK", zone_kind="CONV", src="registry 'A rest is centred on or about the middle of the staff'",
    words="quarter rest")
sym("rest_hook", env=(0.5, 1.9, 1.0, 5.0), fill=(0.1, 0.85), locs=("IN", "NEAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="ASK", zone_kind="CONV", src="rests dossier", words="eighth / sixteenth rest")
sym("rest_multibar", env=(2.5, INF, 0.5, 2.6), fill=(0.3, 1.0), locs=("IN",),
    zones=("BODY", "BARHEAD", "BARTAIL", "HEADER"), loc_kind="CONV", zone_kind="CONV",
    src="registry 'A multi-bar rest is an H-bar'", words="multi-bar rest")
sym("dynamic_letter", env=(0.5, 3.6, 0.7, 4.2), fill=(0.08, 0.8), locs=("NEAR", "FAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A dynamic LETTER stands ... below the bottom line'",
    words="dynamic letter (f, p, m, s, z)")
sym("tuplet_digit", env=(0.4, 1.8, 0.7, 2.2), fill=(0.1, 0.8), locs=("NEAR", "FAR"), zones=MUSIC_NO_KEYSLOT,
    loc_kind="CONV", zone_kind="CONV", src="registry 'A TUPLET digit stands OUTSIDE the staff'",
    words="tuplet number")
sym("text", env=(0.3, INF, 0.4, INF), fill=(0.03, 0.8), locs=("NEAR", "FAR"), zones=ZONES,
    loc_kind="ASK", zone_kind="CONV", src="registry 'Direction words are printed INSIDE the system'",
    words="text (word, label, direction)")

SYMBOLS = S
EDGE_RULES = {"barline": True}

_PREFIX = [
    ("noteheadBlack", "head_black"), ("noteheadHalf", "head_half"), ("noteheadWhole", "head_whole"),
    ("noteheadDoubleWhole", "head_whole"), ("augmentationDot", "dot"), ("articStaccat", "dot"),
    ("stem", "stem"), ("barline", "barline"), ("ledgerLine", "ledger"), ("beam", "beam"),
    ("flag", "flag"), ("tie", "tie"), ("slur", "slur"), ("dynamicCrescendo", "hairpin"),
    ("dynamicDiminuendo", "hairpin"), ("dynamic", "dynamic_letter"), ("accidental", "accidental"),
    ("key", "key_accidental"), ("clef", "clef"), ("timeSig", "meter_digit"),
    ("restWhole", "rest_block"), ("restHalf", "rest_block"), ("restDoubleWhole", "rest_block"),
    ("restQuarter", "rest_quarter"), ("restHBar", "rest_multibar"), ("restHNr", "rest_multibar"),
    ("rest", "rest_hook"), ("tremolo", "tremolo"), ("brace", "brace"), ("bracket", "brace"),
    ("arpeggiato", "arpeggiato"), ("articTenuto", "tenuto"), ("articAccent", "accent"),
    ("articMarcato", "accent"), ("fermata", "fermata"), ("tuplet", "tuplet_digit"),
    ("fingering", "tuplet_digit"), ("text", "text"), ("graceNote", "head_black"),
]


def symbol_of(cls):
    if not cls:
        return None
    for p, s in _PREFIX:
        if cls.startswith(p):
            return s
    return None


def candidates(d):
    trace = {}
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
        if d.get("loc") and d["loc"] not in s["locs"]:
            lattice_only = (d["loc"] == "IN") or (s["locs"] == ("IN",))
            kind = s["loc_kind"] + ("" if lattice_only else "+CUT")
            why.append((kind, "loc %s not in %s" % (d["loc"], "/".join(s["locs"]))))
        if d.get("zone") and d["zone"] not in s["zones"]:
            why.append((s["zone_kind"] + "+CUT", "zone %s not in %s" % (d["zone"], "/".join(s["zones"]))))
        if EDGE_RULES.get(name) and d.get("edge") is False:
            why.append(("CONV+CUT", "not at a bar boundary"))
        trace[name] = why
    conv = {n for n, w in trace.items() if not any(k == "CONV" for k, _ in w)}
    allr = {n for n, w in trace.items() if not w}
    return {"conv": conv, "all": allr}, trace
