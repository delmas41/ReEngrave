"""usage: vq.py WORKDIR PLATE SUBJECT... -> each arm's mini-record verdicts (all quantities) for the subject"""
import json, sys
wd, plate = sys.argv[1], sys.argv[2]
for arm in ('off', 'on'):
    r = json.load(open('%s/%s.%s.mini-record.json' % (wd, plate, arm)))
    print(arm, list(r.keys())[:8])
    for v in r.get('verdicts', []):
        if v['subject'] in sys.argv[3:]:
            print(arm, v['subject'], v['quantity'], v['outcome'], v['reason'], str(v.get('value'))[:120])
