"""usage: bar_xml.py FILE.musicxml PART MEASURE -- print that measure's XML (compact)"""
import re, sys
x = open(sys.argv[1]).read()
part, meas = sys.argv[2], sys.argv[3]
m = re.search(r'<part id="%s">(.*?)</part>' % re.escape(part), x, re.S)
body = m.group(1)
mm = re.search(r'<measure number="%s"[^>]*>(.*?)</measure>' % re.escape(meas), body, re.S)
print(mm.group(0)[:6000] if mm else "no measure")
