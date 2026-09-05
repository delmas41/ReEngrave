"""Print the beam sequence per measure for one part of a MusicXML file."""
import sys
import xml.etree.ElementTree as ET

path, partname = sys.argv[1], sys.argv[2]
tree = ET.parse(path)
root = tree.getroot()
ids = {sp.get('id'): sp.findtext('part-name')
       for sp in root.iter('score-part')}
for part in root.iter('part'):
    if partname.lower() not in (ids.get(part.get('id')) or '').lower():
        continue
    print('part', part.get('id'), ids.get(part.get('id')))
    for m in part.iter('measure'):
        seq = []
        for n in m.iter('note'):
            b = [f"{be.get('number')}:{be.text}" for be in n.findall('beam')]
            step = n.findtext('pitch/step') or 'R'
            seq.append(step + (('[' + ','.join(b) + ']') if b else ''))
        print(' m', m.get('number'), ' '.join(seq))
