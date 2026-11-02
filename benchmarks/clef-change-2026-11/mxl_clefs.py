import sys, zipfile, xml.etree.ElementTree as ET


def load(p):
    z = zipfile.ZipFile(p)
    names = [n for n in z.namelist() if n.endswith('.xml') and not n.startswith('META')]
    return ET.fromstring(z.read(names[0]))


root = load(sys.argv[1])
names = {sp.get('id'): (sp.findtext('part-name') or '') for sp in root.iter('score-part')}
for part in root.iter('part'):
    pid = part.get('id')
    out = []
    for m in part.iter('measure'):
        for att in m.iter('attributes'):
            for c in att.findall('clef'):
                s = c.findtext('sign')
                l = c.findtext('line')
                oc = c.findtext('clef-octave-change')
                out.append((m.get('number'), c.get('number'), s + (l or '') + (('/' + oc) if oc else '')))
    print(pid, names[pid].strip()[:20], out[:1], 'changes:', out[1:])
