import json, collections, sys
r = json.load(open(sys.argv[1]))
print(sorted(collections.Counter(o['quantity'] for o in r['verdicts']).items(), key=lambda x:-x[1])[:60])
print(sorted(collections.Counter(o['quantity'] for o in r['observations']).items(), key=lambda x:-x[1])[:60])
print(collections.Counter(type(o['value']).__name__ for o in r['verdicts'] if o['quantity']=='tie_pair'))
for o in r['verdicts']:
    if o['quantity']=='tie_pair' and o['value'] is not None:
        print(o['subject'], o['value'], str(o['detail'])[:600]); break
