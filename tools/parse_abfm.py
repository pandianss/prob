# -*- coding: utf-8 -*-
"""Parse the ABFM extraction into a structural map.

One source line == one printed page. Emits units, their section headings and
per-unit signals used by the content pipeline (BLUEPRINT.md 3.2 / 3.7).
"""
import io, json, re, sys, os

UNIT = re.compile(u'U\\s*N\\s*I\\s*T\\s*[–-]?\\s*(\\d+)')
# "8.3 DEGREE OF FINANCIAL LEVERAGE" - numbered section headings, upper case
SECTION = re.compile(u'(?<![\\d.])(\\d{1,2})\\.(\\d{1,2})\\s+([A-Z][A-Z &–\'(),/-]{4,80})')
RUNHEAD = re.compile(u'\\s*\\|\\s*\\d+\\s*$')
OBJ = re.compile(u'(?<![0-9.])(\\d{1,2})\\.0\\s+OBJECTIVES')
PAGENUM = re.compile(u'^\\s*\\d+\\s*\\|\\s*')

MARKERS = [u'STRUCTURE', u'OBJECTIVES', u'Let Us Sum Up', u'Keywords',
           u'Check Your Progress', u'Solution']

TITLES = {
    1: u'Basics of Management', 2: u'Planning', 3: u'Organising', 4: u'Staffing',
    5: u'Directing', 6: u'Controlling', 7: u'Sources of Finance and Financial Strategies',
    8: u'Financial and Operating Leverages', 9: u'Capital Investment Decisions',
    10: u'Capital Budgeting for International Project Investment Decisions',
    11: u'Adjustment of Risk and Uncertainty in Capital Budgeting Decision',
    12: u'Decision Making', 13: u'Corporate Valuation', 14: u'Discounted Cash Flow Valuation',
    15: u'Other Non-DCF Valuation Models', 16: u'Special Cases of Valuation',
    17: u'Merger, Acquisition & Restructuring', 18: u'Deal Structuring and Financial Strategies',
    19: u'Hybrid Finance', 20: u'Startup Finance', 21: u'Private Equity and Venture Capital',
    22: u'Artificial Intelligence', 23: u'Business Analytics as Management Tool',
    24: u'Green and Sustainable Financing', 25: u'Special Purpose Acquisition Companies',
}
MODULE = {u'A': (1, 6, u'The Management Process'),
          u'B': (7, 12, u'Advanced Concepts of Financial Management'),
          u'C': (13, 18, u'Valuation, Mergers & Acquisitions'),
          u'D': (19, 25, u'Emerging Business Solutions')}


def module_of(n):
    for k, (lo, hi, name) in MODULE.items():
        if lo <= n <= hi:
            return k, name
    return None, None


def clean(line):
    line = PAGENUM.sub(u'', line)
    return RUNHEAD.sub(u'', line).strip()


def parse(path):
    lines = io.open(path, encoding='utf8', errors='replace').read().split(u'\n')
    # locate unit starts; body begins after the front matter (TOC pages)
    starts = []
    for i, ln in enumerate(lines):
        for m in UNIT.finditer(ln):
            starts.append((i, int(m.group(1)), m.start()))
    # Four Module D units lost their "U N I T n" heading in extraction; every
    # unit keeps its "<n>.0 OBJECTIVES" anchor, so fall back to that.
    have = set(n for _, n, _ in starts)
    for i, ln in enumerate(lines):
        for m in OBJ.finditer(ln):
            n = int(m.group(1))
            if n not in have and 1 <= n <= 25:
                have.add(n)
                starts.append((i, n, max(0, m.start() - 90)))
    starts.sort()
    # keep the first occurrence of each unit number, in ascending page order
    seen, ordered = set(), []
    for i, n, off in starts:
        if n not in seen and 1 <= n <= 25:
            seen.add(n); ordered.append((i, n, off))

    units = []
    for idx, (start, n, off) in enumerate(ordered):
        nxt = ordered[idx + 1] if idx + 1 < len(ordered) else None
        end = nxt[0] if nxt else len(lines)
        # a printed page can carry the tail of one unit and the head of the next,
        # so trim the boundary pages at the heading offsets
        seg = list(lines[start:end + 1]) if nxt else list(lines[start:end])
        if seg:
            seg[0] = seg[0][off:]
            if nxt:
                seg[-1] = seg[-1][:nxt[2]]
        body = u'\n'.join(clean(l) for l in seg)
        mod, modname = module_of(n)
        secs = []
        for sm in SECTION.finditer(body):
            if int(sm.group(1)) == n:
                t = u' '.join(sm.group(3).split())
                t = re.sub(u' [A-Z]$', u'', t).title()   # drop the next word's initial
                ref = u'%s.%s' % (sm.group(1), sm.group(2))
                if not any(s['ref'] == ref for s in secs):
                    secs.append({'ref': ref, 'title': t})
        units.append({
            'unit': n, 'title': TITLES.get(n, u'?'), 'module': mod, 'module_title': modname,
            'pages': end - start, 'chars': len(body),
            'sections': secs,
            'markers': dict((mk, body.count(mk)) for mk in MARKERS),
            'math': {'eq': body.count(u'='), 'pct': body.count(u'%'),
                     'delta': body.count(u'∆'), 'times': body.count(u'×')},
            'line_start': start,
        })
    return units


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'caiib/abfm.txt'
    units = parse(src)
    out = {'source': os.path.basename(src), 'units': units,
           'found': len(units), 'expected': 25,
           'missing': sorted(set(range(1, 26)) - set(u['unit'] for u in units))}
    io.open('content/abfm_structure.json', 'w', encoding='utf8').write(
        json.dumps(out, indent=1, ensure_ascii=False))
    print(u'units %d/25  missing=%s' % (out['found'], out['missing']))
    for u_ in units:
        print(u'  %-2d %-1s %-52s pages=%-4d secs=%-3d eq=%-4d %s' % (
            u_['unit'], u_['module'], u_['title'][:52], u_['pages'], len(u_['sections']),
            u_['math']['eq'], u_['markers']['Check Your Progress'] and u'CYP' or u'-'))
