#!/bin/sh
# usage: pdfcheck.sh DIR TAG ARM  -- compile DIR/TAG.ARM.ly with lilypond; print page count, warning classes, errors
d="$1"; t="$2"; a="$3"
mkdir -p "$d/pdf"
lilypond -o "$d/pdf/$t.$a" "$d/$t.$a.ly" > "$d/pdf/$t.$a.log" 2>&1
echo "exit=$? tag=$t arm=$a"
python3 -c "
import fitz,sys
print('pages', fitz.open('$d/pdf/$t.$a.pdf').page_count)"
echo "warnings: $(grep -c 'warning' "$d/pdf/$t.$a.log")  errors: $(grep -ci 'error' "$d/pdf/$t.$a.log")"
grep -o "warning: [a-z -]*" "$d/pdf/$t.$a.log" | sort | uniq -c | sort -rn | head -8
tail -1 "$d/pdf/$t.$a.log"
