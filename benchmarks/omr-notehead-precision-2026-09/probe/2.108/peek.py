import json
d = json.load(open('data/hand-truth/pages/imslp317803/0.json'))
print({k: (len(v) if hasattr(v, '__len__') else v) for k, v in d.items()})
print(d['boxes'][0])
print(d['queue'][:1])
print(d['staves'][:2])
