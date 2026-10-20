import json,sys
for plate in ('litolff','brahms'):
    for m in json.load(open(f'/private/tmp/claude-501/s173/out/print/2.173/manifest.{plate}.json')):
        print(plate,m['n'],m['file'],'want',m['want'],'counted',m['counted'],m['measure'])
        for r in m['rows']: print('   ',r)
