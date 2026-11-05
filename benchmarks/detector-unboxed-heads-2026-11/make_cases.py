"""Build cases.json: the confirmed unboxed dyad heads. NAMED = from the lanes' tiles (position read off the crop and refined to the head's hole);
CENSUS = census2 candidates that a crop look confirmed (indices below; the others were rejected by eye: digits, a stem gap, an ornament loop)."""
import json

named = [
    dict(id='N1', source='named 2.264 litolff_02 family / 2.252 r1 tile 12 (stop dyad, lower head)', doc='litolff', page=3, cx=1377, cy=1046),
    dict(id='N2', source='named 2.252 r1 tile 2 (right dyad, lower head)', doc='litolff', page=2, cx=2360, cy=2282),
    dict(id='N3', source='named 2.260b r2 tile 2 (upper head of the left dyad)', doc='litolff', page=10, cx=1917, cy=2692),
    dict(id='N4', source='named 2.260b r2 tile 9 (upper head of the left dyad)', doc='litolff', page=10, cx=1757, cy=2823),
]
CONFIRMED = [0, 1, 2, 6, 9, 11, 12, 13, 14, 15, 16]
cen = json.load(open('benchmarks/detector-unboxed-heads-2026-11/census2-litolff.json'))
cases = list(named)
for i in CONFIRMED:
    c = cen[i]
    cases.append(dict(id='C%d' % i, source='census (hollow, same column, no box of any reader)', doc=c['doc'], page=c['page'], cx=c['cx'], cy=c['cy']))
bra = json.load(open('benchmarks/detector-unboxed-heads-2026-11/census2-brahms.json'))
cases.append(dict(id='B0', source='census (hollow, same column, no box of any reader; Brahms; crop-confirmed, B1 rejected: a slur gap)', doc='brahms',
                  page=bra[0]['page'], cx=bra[0]['cx'], cy=bra[0]['cy']))
json.dump(cases, open('benchmarks/detector-unboxed-heads-2026-11/cases.json', 'w'), indent=1)
print(len(cases), 'cases')
