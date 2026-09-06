import sys, fitz
d = fitz.open(sys.argv[1])
print("pages", d.page_count, "text layer:", any(d[i].get_text().strip() for i in range(min(5, d.page_count))))
toc = d.get_toc()
print("outline entries:", len(toc))
for t in toc[:40]:
    print("  ", t)
