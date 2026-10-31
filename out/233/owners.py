import json, sys, collections
for f in sys.argv[1:]:
    d = json.load(open(f))
    c = collections.Counter(); w = collections.Counter(); n = 0
    for x in d['thcs']:
        for note in x['thc']['claims']:
            if note['converted']:
                n += 1
                w[note['gather_why']] += 1
                for fam in set(note['claims_ignored'] or ()):
                    c[fam] += 1
    print(f, 'converted tips', n, 'by GATHER word', dict(w), 'owner families ignored (heads counted once each)', dict(c))
