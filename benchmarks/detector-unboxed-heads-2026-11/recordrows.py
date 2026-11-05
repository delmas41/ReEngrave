"""Rows of the 20261103-night record for one page (glyph_box + glyph_conf), streamed from the full record bytes (no full JSON load).
Cached as small json under $RR_CACHE (default out/2.267-rows, gitignored)."""
import json
import os
import re
from pathlib import Path

REC = {
    'litolff': '/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/beethoven5-litolff-mvt1-whole-20261103-night.record.json',
    'brahms': '/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-mvt1-whole-20261103-night.record.json',
}
CACHE = Path(os.environ.get('RR_CACHE', 'out/2.267-rows'))


def rows(doc, page, quantities=('glyph_box',), subject_prefix=None):
    """Observation dicts for glyph subjects on `page` with the given quantity (and subject prefix)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / ('%s-p%d.json' % (doc, page))
    if f.exists():
        allrows = json.load(open(f))
    else:
        data = open(REC[doc], 'rb').read()
        pat = re.compile(rb'"subject":"glyph/%d/' % page)
        allrows = []
        for m in pat.finditer(data):
            s = data.rfind(b'{"id"', 0, m.start())
            e = data.find(b'},{"id"', m.start())
            if e < 0:
                continue
            try:
                o = json.loads(data[s:e + 1])
            except Exception:
                continue
            if o.get('quantity') in ('glyph_box', 'glyph_conf'):
                allrows.append(o)
        del data
        json.dump(allrows, open(f, 'w'))
    return [o for o in allrows if o['quantity'] in quantities and (subject_prefix is None or o['subject'].startswith(subject_prefix))]
