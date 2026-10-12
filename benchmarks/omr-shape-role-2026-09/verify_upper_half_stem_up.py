#!/usr/bin/env python3
"""Verify Sean's claim (2026-10-10): a notehead above the middle line whose stem
goes up is almost always another voice.  Measurement only, over orchestral
reference encodings in library/reference/.  See --help-less: just run it.

Classes for an ANOMALOUS note (above middle & stem up, or below middle & stem down):
  TWO_VOICES      another <voice> has a (non-rest, non-grace, non-cue) note in the
                  same part+staff+measure  (sub-flag: overlapping in time = strict)
  CHORD_FAR_NOTE  single voice; note is in a chord whose farthest note lies on the
                  OPPOSITE side of the middle line by more than the nearest-side
                  extreme of the chord
  BEAM_GROUP      single voice, not chord-explained; note is in a beam group (beam
                  number 1 begin..end, same part/staff/voice) holding a note on the
                  opposite side farther from the middle line than this note
  UNEXPLAINED     none of the above
"""
import os, sys, json, zipfile, random, re, collections
from lxml import etree

REF = "/Users/seanjohnson/Desktop/ReEngrave/library/reference"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "out", "2.12m", "upper-half-stem-up.json")
STEP = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}

# orchestral work directories (composer/work-slug); judgement from names + part lists
ORCH_DIRS = [
    "bach/brandenburg-concerto-3", "bach/brandenburg-concerto-4",
    "beach/symphony-in-e-minor",
    *["beethoven/symphony-%d" % i for i in range(1, 10)],
    "brahms/symphony-1", "brahms/symphony-2", "brahms/symphony-3", "brahms/symphony-4",
    "bruckner/symphony-5-in-b-flat-major",
    "dvorak/symphony-9", "dvorak/symphony-9-in-e-minor-op95",  # sym9 mvt4 (assets) dropped below as same movement as op95 mvt4
    "holst/the-planets",
    "mahler/5-rondo-finale", "mahler/adagietto", "mahler/symphony-5",
    "mozart/symphony-40-in-g-minor-k550", "mozart/symphony-41-in-c-major-jupiter",
    "tchaikovsky/1812-overture", "tchaikovsky/pizzicato-ostinato",
    "tchaikovsky/symphony-4", "tchaikovsky/symphony-6", "tchaikovsky/symphony-6-pathetique",
    "tchaikovsky/tchaikovsky-symphony-6-3-satz",
    "tchaikovsky/swan-lake", "tchaikovsky/dance-of-the-sugar-plum-fairy",
    "tchaikovsky/waltz-of-the-flowers",
    "ravel/bolero", "ravel/pavane", "ravel/bolero-study-reduction-340-bars",
    "rimsky-korsakov/flight-of-the-bumblebee",
]
# alternative encodings of a movement already used (kept one each); documented in the report
SAME_MOVEMENT_DROP = {
    ("dvorak/symphony-9", "symphony-9--mvt4"),                 # = dvorak/symphony-9-in-e-minor-op95 mvt4
    ("tchaikovsky/symphony-6", "symphony-6--mvt3"),             # = tchaikovsky-symphony-6-3-satz mvt3
}
# whole-movement duplicates of beethoven/symphony-9 mvt1 and mvt4 (dirs symphony-9-part-i,
# allegro-ma-non-troppo-un-poco-maestoso) are simply not in ORCH_DIRS.
MIN_PARTS = 3  # fewer parts => reduction/solo/piano arrangement, not an orchestral score


def local(tag):
    return tag.split('}')[-1] if isinstance(tag, str) else tag


def staff_pos(step, octave, clef):
    """Staff position in diatonic steps from the middle line (line 3) = 0."""
    sign, line, oc = clef
    ref = {"G": 4 * 7 + 4, "F": 3 * 7 + 3, "C": 4 * 7 + 0}[sign] + 7 * oc
    d = octave * 7 + STEP[step]
    return (d - ref) + 2 * (line - 3)


def self_test():
    T = (("G", 2, 0), ("F", 4, 0), ("C", 3, 0), ("C", 4, 0), ("G", 2, -1))
    cases = [
        ("treble G4", ("G", 4), T[0], -2), ("treble B4 middle", ("B", 4), T[0], 0),
        ("treble F5 top line", ("F", 5), T[0], 4), ("treble E4 bottom line", ("E", 4), T[0], -4),
        ("treble C4 ledger", ("C", 4), T[0], -6),
        ("bass D3 middle", ("D", 3), T[1], 0), ("bass F3 line4", ("F", 3), T[1], 2),
        ("bass G2 bottom line", ("G", 2), T[1], -4),
        ("alto C4 middle", ("C", 4), T[2], 0), ("tenor C4 line4", ("C", 4), T[3], 2),
        ("treble8vb G3", ("G", 3), T[4], -2),
    ]
    ok = True
    for name, (s, o), clef, want in cases:
        got = staff_pos(s, o, clef)
        print("  %-22s got %+d want %+d %s" % (name, got, want, "OK" if got == want else "FAIL"))
        ok &= got == want
    return ok


def load_xml(path):
    if path.endswith(".mxl"):
        z = zipfile.ZipFile(path)
        root = None
        try:
            c = etree.fromstring(z.read("META-INF/container.xml"))
            for rf in c.iter():
                if local(rf.tag) == "rootfile":
                    root = rf.get("full-path"); break
        except KeyError:
            pass
        if not root:
            root = [n for n in z.namelist() if n.endswith((".xml", ".musicxml")) and not n.startswith("META-INF")][0]
        data = z.read(root)
    else:
        data = open(path, "rb").read()
    return etree.fromstring(data, etree.XMLParser(huge_tree=True, recover=False, resolve_entities=False, load_dtd=False, no_network=True))


def text(e, tag, default=None):
    for ch in e:
        if local(ch.tag) == tag:
            return (ch.text or "").strip()
    return default


def child(e, tag):
    for ch in e:
        if local(ch.tag) == tag:
            return ch
    return None


def parse_score(path):
    """Returns (notes, skipped, nparts, partnames) ; notes is list of dict."""
    root = load_xml(path)
    if local(root.tag) != "score-partwise":
        return None, {"not_partwise": 1}, 0, []
    names = {}
    pl = child(root, "part-list")
    if pl is not None:
        for sp in pl:
            if local(sp.tag) == "score-part":
                names[sp.get("id")] = text(sp, "part-name", sp.get("id")) or sp.get("id")
    skipped = collections.Counter()
    notes = []
    parts = [p for p in root if local(p.tag) == "part"]
    for part in parts:
        pid = part.get("id"); pname = names.get(pid, pid)
        clefs = {}  # staff -> (sign,line,oc)
        divisions = 1
        mi = -1; multi = set(); part_start = len(notes)
        for meas in part:
            if local(meas.tag) != "measure":
                continue
            mi += 1
            mnum = meas.get("number")
            cursor = 0; last_on = 0; last_dur = 0
            mnotes = []  # all note dicts this measure
            allvoices = []  # (staff, voice, on, off, is_rest)
            for el in meas:
                t = local(el.tag)
                if t == "attributes":
                    dv = text(el, "divisions")
                    if dv: divisions = int(float(dv))
                    for cl in el:
                        if local(cl.tag) == "clef":
                            n = int(cl.get("number") or 1)
                            s = text(cl, "sign"); ln = text(cl, "line"); oc = text(cl, "clef-octave-change")
                            if s in ("G", "F", "C"):
                                line = int(ln) if ln else {"G": 2, "F": 4, "C": 3}[s]
                                clefs[n] = (s, line, int(oc) if oc else 0)
                            else:
                                clefs[n] = None
                elif t == "backup":
                    cursor -= int(float(text(el, "duration", "0")))
                elif t == "forward":
                    cursor += int(float(text(el, "duration", "0")))
                elif t == "note":
                    is_chord = child(el, "chord") is not None
                    is_grace = child(el, "grace") is not None
                    is_cue = child(el, "cue") is not None
                    is_rest = child(el, "rest") is not None
                    dur = int(float(text(el, "duration", "0") or 0))
                    staff = int(text(el, "staff", "1") or 1)
                    voice = text(el, "voice", "1") or "1"
                    if is_chord:
                        on = last_on; dur_eff = last_dur
                    else:
                        on = cursor; dur_eff = dur
                        if not is_grace:
                            last_on = cursor; last_dur = dur
                            cursor += dur
                        else:
                            last_on = cursor; last_dur = 0
                    if is_grace or is_cue:
                        if not is_rest:
                            skipped["grace" if is_grace else "cue"] += 1
                        continue
                    allvoices.append((staff, voice, on, on + dur_eff, is_rest))
                    if is_rest:
                        continue
                    pit = child(el, "pitch")
                    if pit is None:
                        skipped["unpitched"] += 1
                        continue
                    stem = text(el, "stem")
                    beams = {}
                    for b in el:
                        if local(b.tag) == "beam":
                            beams[int(b.get("number") or 1)] = (b.text or "").strip()
                    clef = clefs.get(staff)
                    if clef is None:
                        skipped["no_pitched_clef(perc/tab/none)"] += 1
                        continue
                    pos = staff_pos(text(pit, "step"), int(text(pit, "octave")), clef)
                    mnotes.append(dict(pid=pid, part=pname, m=mnum, staff=staff, voice=voice, on=on, off=on + dur_eff,
                                       chord=is_chord, pos=pos, stem=stem, beams=beams,
                                       pitch="%s%s%s" % (text(pit, "step"), {"-1": "b", "1": "#", "": "", None: ""}.get((text(pit, "alter") or "").split('.')[0], ""), text(pit, "octave")),
                                       clef="%s%d%s" % (clef[0], clef[1], ("%+d" % clef[2]) if clef[2] else "")))
            # per-measure annotate
            by_staff_voice = collections.defaultdict(lambda: collections.defaultdict(list))
            for (st, vo, a, b, r) in allvoices:
                by_staff_voice[st][vo].append((a, b, r))
            for st_, sv_ in by_staff_voice.items():
                if sum(1 for lst in sv_.values() if any(not x[2] for x in lst)) >= 2:
                    multi.add((st_, mi))
            for n in mnotes:
                n["mi"] = mi
                sv = by_staff_voice[n["staff"]]
                other_note = False; other_overlap = False; other_rest_only = False
                for vo, lst in sv.items():
                    if vo == n["voice"]:
                        continue
                    nonrest = [x for x in lst if not x[2]]
                    if nonrest:
                        other_note = True
                        if any(a < n["off"] and b > n["on"] for a, b, _ in nonrest):
                            other_overlap = True
                    elif lst:
                        other_rest_only = True
                n["other_voice"] = other_note; n["other_overlap"] = other_overlap
                n["other_rest_only"] = (not other_note) and other_rest_only
            # chords: group by (staff, voice, on)
            grp = collections.defaultdict(list)
            for n in mnotes:
                grp[(n["staff"], n["voice"], n["on"])].append(n)
            for g in grp.values():
                ps = [x["pos"] for x in g]
                for x in g:
                    x["chord_pos"] = ps if len(g) > 1 else None
            # beam groups (beam level 1) per staff/voice
            open_g = {}
            for n in mnotes:
                k = (n["staff"], n["voice"])
                b = n["beams"].get(1)
                if b == "begin":
                    open_g[k] = [n]; n["bg"] = open_g[k]
                elif b in ("continue", "end") and k in open_g:
                    open_g[k].append(n); n["bg"] = open_g[k]
                    if b == "end":
                        del open_g[k]
                elif b is not None and 1 not in n["beams"]:
                    pass
            open_g.clear()
            notes.extend(mnotes)
        for n in notes[part_start:]:
            n["near_two_voice"] = ((n["staff"], n["mi"] - 1) in multi) or ((n["staff"], n["mi"] + 1) in multi)
    for n in notes:
        if "bg" in n:
            n["bg_pos"] = [x["pos"] for x in n["bg"]]
            n["bg_pos_dummy"] = None
    for n in notes:
        n.pop("bg", None)
    return notes, dict(skipped), len(parts), sorted(set(names.values()))


def classify(n):
    """n anomalous: returns class string."""
    s = 1 if n["pos"] > 0 else -1
    p = abs(n["pos"])
    if n["other_voice"]:
        return "TWO_VOICES_STRICT" if n["other_overlap"] else "TWO_VOICES_NONOVERLAP"
    if n.get("chord_pos"):
        same = max([q * s for q in n["chord_pos"]])
        opp = max([-q * s for q in n["chord_pos"]])
        if opp > same:
            return "CHORD_FAR_NOTE"
    if n.get("bg_pos"):
        opp = max([-q * s for q in n["bg_pos"]])
        if opp > p:
            return "BEAM_GROUP"
    return "UNEXPLAINED"


def pick_files():
    """Select orchestral files; de-duplicate movements."""
    chosen = []
    notes_ = []
    for d in ORCH_DIRS:
        dp = os.path.join(REF, d)
        if not os.path.isdir(dp):
            notes_.append("missing dir " + d); continue
        files = [f for f in os.listdir(dp) if f.endswith((".mxl", ".musicxml", ".xml"))]
        bymv = collections.defaultdict(list)
        for f in files:
            m = re.search(r"--([^-].*?)--gradus(-assets(-\d+)?)?\.(mxl|musicxml)$", f)
            tag = m.group(1) if m else f
            bymv[tag].append(f)
        for tag, fs in bymv.items():
            # prefer curated 'gradus' .mxl, then 'gradus' .musicxml, then gradus-assets
            def rank(f):
                return (0 if "--gradus." in f else 1, 0 if f.endswith(".mxl") else 1, f)
            fs.sort(key=rank)
            chosen.append((d, tag, os.path.join(dp, fs[0]), fs[1:]))
    return chosen, notes_


def main():
    print("positions self-test:")
    if not self_test():
        print("SELF-TEST FAILED"); sys.exit(2)
    chosen, miss = pick_files()
    results = {}; files_info = []; skipped_files = []
    seen_fp = {}
    random.seed(20261010)
    stem_cells = collections.defaultdict(lambda: collections.Counter())  # work -> counter
    unexplained = []
    ctrl = collections.Counter()
    pos_hist_unexp = collections.Counter()
    for d, tag, path, dups in chosen:
        base = os.path.basename(path)
        if (d, tag) in SAME_MOVEMENT_DROP:
            skipped_files.append((base, "alternative encoding of a movement already counted")); continue
        if tag in ("full", "sym9-full", "sym41-full", "sym6-full") or tag.endswith("-full"):
            skipped_files.append((base, "duplicate: whole-work file overlaps per-movement files")); continue
        try:
            notes, skipped, nparts, pnames = parse_score(path)
        except Exception as e:
            skipped_files.append((base, "parse error %s" % e)); continue
        if notes is None:
            skipped_files.append((base, "not score-partwise")); continue
        if nparts < MIN_PARTS:
            skipped_files.append((base, "only %d part(s): reduction/solo, not orchestral" % nparts)); continue
        fp = (len(notes), sum(n["pos"] for n in notes), nparts)
        if fp in seen_fp:
            skipped_files.append((base, "identical to %s (fingerprint)" % seen_fp[fp])); continue
        seen_fp[fp] = base
        C = stem_cells[d]
        C["files"] += 1
        for k, v in skipped.items():
            C["skip:" + k] += v
        for n in notes:
            if n["stem"] not in ("up", "down"):
                C["skip:stem_missing_none_double"] += 1; continue
            C["notes"] += 1
            pos = n["pos"]
            if pos == 0:
                side = "mid"
            else:
                side = "above" if pos > 0 else "below"
            cell = "%s_%s" % (side, n["stem"])
            C[cell] += 1
            single = not n["other_voice"]
            # plain single-voice / not-chord / not-beam control
            plain = single and not n.get("chord_pos") and not n.get("bg_pos")
            if plain:
                C[cell + "|plain"] += 1
            if side == "mid":
                C[cell + "|" + ("single" if single else "multi")] += 1
                continue
            anomalous = (side == "above" and n["stem"] == "up") or (side == "below" and n["stem"] == "down")
            if anomalous:
                cl = classify(n)
                C[cell + "|" + cl] += 1
                if n["other_rest_only"] and cl == "UNEXPLAINED":
                    C[cell + "|UNEXPLAINED_with_other_voice_rest_only"] += 1
                if cl == "UNEXPLAINED" and n["near_two_voice"]:
                    C[cell + "|UNEXPLAINED_adjacent_measure_has_two_voices"] += 1
                if cl == "UNEXPLAINED" and not n["near_two_voice"] and not n["other_rest_only"]:
                    C[cell + "|UNEXPLAINED_residual"] += 1
                if cl == "UNEXPLAINED":
                    pos_hist_unexp[(side, pos)] += 1
                    unexplained.append(dict(side=side, file=base, work=d, part=n["part"], measure=n["m"], staff=n["staff"],
                                            voice=n["voice"], pitch=n["pitch"], clef=n["clef"], pos=pos, chord=n["chord"],
                                            beamed=bool(n["beams"])))
            else:
                C[cell + "|" + ("single" if single else "multi")] += 1
        files_info.append(dict(work=d, file=base, parts=nparts, notes_used=len(notes), also_present_as=dups))
        print("%-45s parts=%2d notes=%7d  %s" % (d + "/" + tag, nparts, len(notes), base[-40:]), flush=True)

    def pool(keys, works=None):
        T = collections.Counter()
        for w, C in stem_cells.items():
            if works and w not in works: continue
            for k, v in C.items():
                T[k] += v
        return T

    def summarize(T):
        out = {"files": T["files"], "notes_with_stem": T["notes"], "skipped": {k[5:]: v for k, v in T.items() if k.startswith("skip:")}}
        for side, stem in (("above", "up"), ("above", "down"), ("below", "down"), ("below", "up"), ("mid", "up"), ("mid", "down")):
            cell = "%s_%s" % (side, stem)
            tot = T[cell]
            row = {"total": tot}
            for k, v in T.items():
                if k.startswith(cell + "|"):
                    row[k.split("|", 1)[1]] = v
            out[cell] = row
        return out

    pooled = summarize(pool(None))
    perwork = {w: summarize(C) for w, C in stem_cells.items() if C["notes"]}
    # unexplained sample (balanced between above/below)
    ua = [u for u in unexplained if u["side"] == "above"]
    ub = [u for u in unexplained if u["side"] == "below"]
    sample_above = random.sample(ua, min(15, len(ua)))
    sample_below = random.sample(ub, min(8, len(ub)))
    hist = collections.defaultdict(dict)
    for (side, pos), v in sorted(pos_hist_unexp.items()):
        hist[side][str(pos)] = v
    # control
    P = pool(None)
    ctrl = {
        "positions_selftest": "passed",
        "plain_single_voice_unbeamed_nonchord": {
            "above_middle_stem_down": P["above_down|plain"], "above_middle_stem_up": P["above_up|plain"],
            "below_middle_stem_up": P["below_up|plain"], "below_middle_stem_down": P["below_down|plain"],
        },
    }
    a_d, a_u = P["above_down|plain"], P["above_up|plain"]
    b_u, b_d = P["below_up|plain"], P["below_down|plain"]
    ctrl["rule_holds_above_pct"] = round(100.0 * a_d / max(1, a_d + a_u), 2)
    ctrl["rule_holds_below_pct"] = round(100.0 * b_u / max(1, b_u + b_d), 2)
    out = dict(method=__doc__, files_total=len(files_info), works_total=len(perwork), filter=dict(
        orchestral_dirs=ORCH_DIRS, min_parts=MIN_PARTS,
        dedupe="per (work dir, movement tag): prefer '--gradus.mxl' over '--gradus.musicxml' over gradus-assets; *-full* whole-work files dropped; (notes,sum pos,parts) fingerprint dedupe"),
        files=files_info, skipped_files=skipped_files, pooled=pooled, per_work=perwork, control=ctrl,
        unexplained_position_hist=hist, unexplained_sample_above=sample_above, unexplained_sample_below=sample_below)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
