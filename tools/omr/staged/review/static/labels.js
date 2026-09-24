/* ReEngrave stage review — the WORDS, and the two pure functions the screen
 * is built on. Loaded by `index.html` before `app.js`, and by `node` from
 * `tools/omr/tests/test_stage_review.py` — which is why nothing here touches
 * `document`, `window` or `fetch`.
 *
 * ⚠️ SEAN TYPES WHAT HE SEES ON THE PLATE, NOT WHAT THE MODEL CALLS IT. He
 * reads "alto clef" and "half head"; the record's vocabulary is
 * `clefCAlto` and `noteheadHalfOnLine`. So every canonical class carries a
 * FRIENDLY name here and the filter matches BOTH spellings — the saved
 * action still names the canonical class, because a sidecar naming a word
 * lane (A) has never heard of is refused after the work is done.
 *
 * ⚠️ THE TABLE IS DERIVED PER FAMILY, NOT TYPED OUT 157 TIMES. A class the
 * rules do not name falls back to its RAW name, so a vocabulary that grows
 * still answers every query — and `test_stage_review.py` asserts both halves
 * of what that costs: every canonical class has a name, and no two classes
 * share one (a collision would make one of the two unreachable by typing).
 */
'use strict';

// ── 1. the friendly names ───────────────────────────────────────────────

//: The irregular ones, where no rule would do.
const FRIENDLY_EXACT = {
  // clefs — what a musician calls them, with the letter kept in parentheses
  clefG: 'treble clef (G)',
  clefF: 'bass clef (F)',
  clefC: 'C clef (alto or tenor — unplaced)',
  clefCAlto: 'alto clef',
  clefCTenor: 'tenor clef',
  clefUnpitchedPercussion: 'percussion clef',
  clef8: 'octave mark on a clef (8)',
  clef15: 'octave mark on a clef (15)',

  // accidentals in the bar, and the same shapes in a key signature
  accidentalFlat: 'flat',
  accidentalSharp: 'sharp',
  accidentalNatural: 'natural',
  accidentalDoubleFlat: 'double flat',
  accidentalDoubleSharp: 'double sharp',
  accidentalFlatSmall: 'flat (small / cautionary)',
  accidentalSharpSmall: 'sharp (small / cautionary)',
  accidentalNaturalSmall: 'natural (small / cautionary)',
  keyFlat: 'flat (key signature)',
  keySharp: 'sharp (key signature)',
  keyNatural: 'natural (key signature)',

  // the rests whose names are not a duration word
  restHBar: 'multi-bar rest (the H bar)',
  restHNr: 'multi-bar rest number',

  // everything with a name of its own
  augmentationDot: 'dot',
  repeatDot: 'repeat dot',
  ledgerLine: 'ledger line',
  beam: 'beam',
  stem: 'stem',
  staff: 'staff line',
  slur: 'slur',
  tie: 'tie',
  brace: 'brace',
  caesura: 'caesura (railway tracks)',
  coda: 'coda',
  segno: 'segno',
  arpeggiato: 'arpeggio',
  ottavaBracket: '8va bracket',
  tupletBracket: 'tuplet bracket',
  keyboardPedalPed: 'pedal (Ped.)',
  keyboardPedalUp: 'pedal release',
  stringsDownBow: 'down bow',
  stringsUpBow: 'up bow',
  ornamentMordent: 'mordent',
  ornamentTrill: 'trill',
  ornamentTurn: 'turn',
  ornamentTurnInverted: 'inverted turn',
  fermataAbove: 'fermata (above)',
  fermataBelow: 'fermata (below)',
  dynamicCrescendoHairpin: 'hairpin (crescendo)',
  dynamicDiminuendoHairpin: 'hairpin (diminuendo)',
  timeSigCommon: 'common time (C)',
  timeSigCutCommon: 'cut common (¢)',
  tremoloMark: 'tremolo mark',
  graceNoteAcciaccatura: 'grace note (acciaccatura)',
  graceNoteAcciaccaturaStemUp: 'grace note, slashed (stem up)',
  graceNoteAcciaccaturaStemDown: 'grace note, slashed (stem down)',
  graceNoteAppoggiaturaStemUp: 'grace note, unslashed (stem up)',
  graceNoteAppoggiaturaStemDown: 'grace note, unslashed (stem down)',
  articulationAccent: 'accent',
  articulationStaccato: 'staccato dot',
  articulationTenuto: 'tenuto',
  // ⚠️ THE COARSE PAIR. CLAUDE.md §9: `numeral*` and `tuple*` are COARSER
  // than the fine names and are NOT synonyms for them, so they are named as
  // the coarse boxes they are rather than as a digit.
  numeral: 'a numeral (class unspecified)',
  tuple: 'a tuplet digit (class unspecified)',
};

//: `noteheadBlack` -> the words a reader uses for that head.
const HEAD_WORDS = {
  Black: 'quarter/eighth head (black)',
  Half: 'half head (hollow, stemmed)',
  Whole: 'whole head (hollow, no stem)',
  DoubleWhole: 'breve head',
  Full: 'filled head',
};
const DURATION_WORDS = {
  DoubleWhole: 'breve', Whole: 'whole', Half: 'half', Quarter: 'quarter',
  '8th': 'eighth', '16th': 'sixteenth', '32nd': 'thirty-second',
  '64th': 'sixty-fourth', '128th': 'hundred-and-twenty-eighth',
};

function _headName(n) {
  const m = /^notehead(DoubleWhole|Black|Half|Whole|Full)(OnLine|InSpace)?(Small)?$/
    .exec(n);
  if (!m) return null;
  const parts = [HEAD_WORDS[m[1]] || m[1].toLowerCase() + ' head'];
  if (m[2]) parts.push(m[2] === 'OnLine' ? 'on a line' : 'in a space');
  if (m[3]) parts.push('small');
  return parts[0] + (parts.length > 1 ? ' — ' + parts.slice(1).join(', ') : '');
}

function _ruleName(n) {
  let m = _headName(n);
  if (m) return m;
  if ((m = /^rest(DoubleWhole|Whole|Half|Quarter|8th|16th|32nd|64th|128th)$/.exec(n)))
    return (DURATION_WORDS[m[1]] || m[1]) + ' rest';
  if ((m = /^flag(8th|16th|32nd|64th|128th)(Up|Down)(Small)?$/.exec(n)))
    return (DURATION_WORDS[m[1]] || m[1]) + ' flag (' + m[2].toLowerCase()
      + (m[3] ? ', small' : '') + ')';
  if ((m = /^timeSig(\d)$/.exec(n))) return m[1] + ' (time signature)';
  if ((m = /^tuplet(\d)$/.exec(n))) return m[1] + ' (tuplet digit)';
  if ((m = /^numeral(\d)$/.exec(n))) return m[1] + ' (numeral)';
  if ((m = /^fingering(\d)$/.exec(n))) return 'fingering ' + m[1];
  if ((m = /^tremolo(\d)$/.exec(n)))
    return 'tremolo (' + m[1] + (m[1] === '1' ? ' stroke)' : ' strokes)');
  if ((m = /^dynamic([FMPRSZ])$/.exec(n)))
    return m[1].toLowerCase() + ' (dynamic letter)';
  if ((m = /^artic(Accent|Marcato|Staccatissimo|Staccato|Tenuto)(Above|Below)$/
    .exec(n)))
    return m[1].toLowerCase() + ' (' + m[2].toLowerCase() + ')';
  return null;
}

/** The words for one canonical class. ⚠️ NEVER EMPTY: a class no rule names
 *  keeps its RAW name, so the list can always be typed at. */
function friendlyName(cls) {
  return FRIENDLY_EXACT[cls] || _ruleName(cls) || cls;
}

/** {class: words} over a whole vocabulary — what the test walks. */
function friendlyTable(names) {
  const out = {};
  for (const n of names) out[n] = friendlyName(n);
  return out;
}

// ── 2. the five human answers, as plain words ───────────────────────────
// ⚠️ THE KINDS COME FROM `/api/labels`, WHICH SERVES LANE (A)'s OWN TABLE.
// This maps a kind to the ONE WORD Sean types; a kind with no word here is
// still offered, under its label from the server. The *etc.* in his ask is
// still one row in one Python table.
const ANSWER_WORDS = {
  delete_box: {word: 'nothing', hint: 'not a symbol — there is no ink here'},
  own_box: {word: 'above', hint: 'belongs to the staff above'},
  own_box_below: {word: 'below', hint: 'belongs to the staff below'},
  dup_box: {word: 'duplicate', hint: 'the same ink as another box — pick it'},
  unsure_box: {word: 'unsure', hint: "I can't tell from the print"},
  confirm_box: {word: 'agree', hint: 'the machine had it right'},
};

/**
 * Everything the popover can offer for ONE box, in one list.
 *
 *   classes  — every canonical name under its friendly words
 *   answers  — the human verbs, as plain words, with the part name on the
 *              two that need one
 *
 * ⚠️ `above` / `below` are ABSENT where the system has no staff that way —
 * never present-and-lying. The top staff of a system has no staff above it.
 */
function buildAnswers(opts) {
  const classes = opts.classes || [];
  const labels = opts.labels || [];
  const staves = opts.staves || [];
  const cur = opts.current || null;
  const isNew = !!opts.isNew;
  const out = [];
  if (!isNew) {
    const i = staves.findIndex(r => r.is_this_one);
    const near = {
      own_box: i > 0 ? staves[i - 1] : null,
      own_box_below: (i >= 0 && i < staves.length - 1) ? staves[i + 1] : null,
    };
    for (const entry of labels) {
      const kinds = entry.kind === 'own_box'
        ? ['own_box', 'own_box_below'] : [entry.kind];
      for (const k of kinds) {
        const w = ANSWER_WORDS[k];
        if (!w) continue;                    // a verb with no word: see above
        if (k === 'own_box' || k === 'own_box_below') {
          const t = near[k];
          if (!t) continue;                  // ABSENT, not disabled
          out.push({group: 'answer', kind: 'own_box', text: w.word,
                    sub: t.part_name || t.staff, staff: t.staff,
                    hint: w.hint + ' (' + (t.part_name || t.staff) + ')',
                    match: [w.word, t.part_name || '', t.staff]});
          continue;
        }
        out.push({group: 'answer', kind: k, text: w.word, sub: '',
                  hint: w.hint, match: [w.word, entry.label || '']});
      }
    }
  }
  for (const n of classes) {
    const f = friendlyName(n);
    out.push({group: 'class', kind: 'class', text: f, sub: n, cls: n,
              current: n === cur, match: [f, n]});
  }
  return out;
}

// ── 3. the filter ───────────────────────────────────────────────────────
// ⚠️ SUBSEQUENCE, BUT RANKED BY HOW LITERAL THE HIT IS. "alto" must reach
// "alto clef" before it reaches `clefCAlto`, and "no" must reach "nothing"
// before it reaches a notehead — otherwise the fastest answer on the page is
// the one hardest to type.

function _rank(hay, q) {
  const h = hay.toLowerCase();
  if (!q) return [9, 0, h.length];
  if (h === q) return [0, 0, h.length];
  if (h.startsWith(q)) return [1, 0, h.length];
  const w = h.search(new RegExp('(^|[^a-z0-9])' + q.replace(
    /[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'));
  if (w >= 0) return [2, w, h.length];
  const at = h.indexOf(q);
  if (at >= 0) return [3, at, h.length];
  // subsequence: every letter of the query, in order, anywhere
  let i = 0, span = 0;
  for (let k = 0; k < h.length && i < q.length; k++) {
    if (h[k] === q[i]) { if (i === 0) span = k; i++; }
  }
  return i === q.length ? [4, span, h.length] : null;
}

function _cmp(a, b) {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}

/**
 * The items that match `query`, best first.
 *
 * ⚠️ A HUMAN ANSWER OUTRANKS A CLASS AT THE SAME LITERALNESS. There are five
 * of them, he types them constantly, and a tie broken the other way would
 * bury "nothing" under 20 noteheads.
 */
function filterAnswers(items, query) {
  const q = String(query || '').trim().toLowerCase();
  const scored = [];
  for (const it of items) {
    let best = null;
    for (const hay of (it.match || [it.text])) {
      if (!hay) continue;
      const r = _rank(hay, q);
      if (r && (!best || _cmp(r, best) < 0)) best = r;
    }
    if (!best) continue;
    scored.push({it, key: [best[0], it.group === 'answer' ? 0 : 1,
                           it.current ? 0 : 1, best[1], best[2]]});
  }
  scored.sort((a, b) => {
    for (let i = 0; i < a.key.length; i++) {
      if (a.key[i] !== b.key[i]) return a.key[i] - b.key[i];
    }
    return String(a.it.text).localeCompare(String(b.it.text));
  });
  return scored.map(s => s.it);
}

// ── 4. the frame, both ways ─────────────────────────────────────────────
// ⚠️⚠️ THE EXACT INVERSE OF THE SERVER'S `CropFrame.to_crop` / `to_page`,
// and the ONE place the browser's pixels become the record's. `crop` is the
// `crop` object `/api/gather` serves: `{page_px:[x0,y0,x1,y1], zoom}`.
function cropToPage(crop, cx, cy) {
  return [cx / crop.zoom + crop.page_px[0], cy / crop.zoom + crop.page_px[1]];
}
function pageToCrop(crop, x, y) {
  return [(x - crop.page_px[0]) * crop.zoom, (y - crop.page_px[1]) * crop.zoom];
}
function boxToPage(crop, b) {
  const a = cropToPage(crop, b[0], b[1]), c = cropToPage(crop, b[2], b[3]);
  return [a[0], a[1], c[0], c[1]];
}
function boxToCrop(crop, b) {
  const a = pageToCrop(crop, b[0], b[1]), c = pageToCrop(crop, b[2], b[3]);
  return [a[0], a[1], c[0], c[1]];
}

// ⚠️ NODE READS THIS FILE TOO — the friendly-name table and the filter are
// tested by `test_stage_review.py` through `node`, because a table only the
// browser can see is a table nothing checks.
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {friendlyName, friendlyTable, buildAnswers, filterAnswers,
                    cropToPage, pageToCrop, boxToPage, boxToCrop,
                    ANSWER_WORDS, FRIENDLY_EXACT};
}
