# -*- coding: utf-8 -*-
"""Export ABFM page images by unit, for image-native authoring.

The supplied PDF is a set of page captures with no text layer. It is worth
more than the text extraction for exactly one reason: formulas and tables are
still VISUALLY intact - stacked fractions, boxed definitions, table grids.
OCR would flatten all of that again (a stacked fraction becomes two lines), so
this tool deliberately does not OCR. It crops each page to the printed area
and hands the image itself to the authoring pipeline (tools/author.py
--images), where the drafter reads a fraction as a fraction.

Nothing about the proof obligations changes: every numeric key is still
recomputed by the arithmetic gate before an item can go live (BLUEPRINT 3.7).

Page mapping: pdf_index = book_page + 14, verified by the running headers on
book pages 176, 177, 411 and 560.

    python tools/pdf_pages.py --unit 8            # export unit 8
    python tools/pdf_pages.py --unit 8 --list     # show the page range only
"""
import argparse, os, sys

PDF = os.path.join('caiib', 'Advanced_Business_and_Financial_Management.pdf')
OFFSET = 14
OUT = os.path.join('content', '_pages')        # gitignored: licensed material

# Start page of each unit, from the book's own CONTENTS page. A unit ends
# where the next begins.
UNIT_START = {
    1: 3, 2: 29, 3: 53, 4: 89, 5: 121, 6: 143,
    7: 161, 8: 175, 9: 189, 10: 211, 11: 229, 12: 247,
    13: 269, 14: 295, 15: 311, 16: 333, 17: 363, 18: 409,
    19: 431, 20: 449, 21: 479, 22: 513, 23: 533, 24: 563, 25: 597,
}
LAST_PAGE = 611   # 626 pdf pages - 14 front-matter offset - trailing blank

# Units where the text extraction is sound and images add little. Exporting
# them anyway is allowed, but the default is the quantitative units, where
# the image is the only faithful source (BLUEPRINT 3.8).
QUANTITATIVE = set(range(7, 20))


def book_range(unit):
    start = UNIT_START[unit]
    end = UNIT_START.get(unit + 1, LAST_PAGE + 1) - 1
    return start, end


def export(unit, dpi=130):
    import fitz
    doc = fitz.open(PDF)
    start, end = book_range(unit)
    folder = os.path.join(OUT, 'u%02d' % unit)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    written = 0
    for book in range(start, end + 1):
        idx = book + OFFSET
        if idx >= doc.page_count:
            break
        page = doc[idx]
        r = page.rect
        # The capture is letterboxed: the printed page sits between ~17% and
        # ~83% of the frame height. Crop to it so no tokens are spent on black.
        clip = fitz.Rect(r.width * 0.05, r.height * 0.17, r.width * 0.95, r.height * 0.83)
        # JPEG, not PNG: these are base64'd into API requests, where a 1 MB PNG
        # per page adds up fast across a 50-page unit and buys no legibility.
        page.get_pixmap(dpi=dpi, clip=clip).save(
            os.path.join(folder, 'p%03d.jpg' % book), jpg_quality=82)
        written += 1
    return folder, start, end, written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--unit', type=int, required=True)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--dpi', type=int, default=130)
    a = ap.parse_args()
    if a.unit not in UNIT_START:
        raise SystemExit('unknown unit %d' % a.unit)
    start, end = book_range(a.unit)
    note = '' if a.unit in QUANTITATIVE else '  (prose unit - the text extraction is already sound)'
    print('unit %d: book pages %d-%d (%d pages)%s' % (a.unit, start, end, end - start + 1, note))
    if a.list:
        return 0
    folder, s, e, n = export(a.unit, a.dpi)
    print('exported %d page images -> %s' % (n, folder))
    return 0


if __name__ == '__main__':
    sys.exit(main())
