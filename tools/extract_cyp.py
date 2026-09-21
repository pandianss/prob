# -*- coding: utf-8 -*-
"""Extract the book's own Check Your Progress sets as a gold corpus.

Each unit ends with CHECK YOUR PROGRESS <numbered MCQs> SOLUTIONS <answer key>.
These are authored questions with known keys, so they serve two jobs
(BLUEPRINT.md 3.7, 5):

  * an anchor set for E1-style factual checking, and
  * a register reference - do our drafted items read like exam questions?

They are NOT redistributed: the corpus stays internal, the same rule as
`derived_from` in 3.6.
"""
import io, json, re, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_abfm import parse

CYP = re.compile(u'CHECK\\s+YOUR\\s+PROGRESS(.{80,20000}?)SOLUTIONS(.{5,900}?)(?:$|LET US|KEYWORDS|U\\s*N\\s*I\\s*T)', re.S | re.I)
QSPLIT = re.compile(u'(?:^|\\s)(\\d{1,2})\\.\\s+(?=\\S)')
OPT = re.compile(u'\\(([a-d])\\)\\s*(.*?)(?=\\s*\\([a-d]\\)|$)', re.S)
KEY = re.compile(u'(\\d{1,2})\\.\\s*\\(([a-d])\\)')


def questions(block):
    parts = QSPLIT.split(block)
    out = []
    for i in range(1, len(parts) - 1, 2):
        num, chunk = parts[i], parts[i + 1]
        cut = chunk.find(u'(a)')
        if cut < 1:
            continue
        stem = u' '.join(chunk[:cut].split())
        opts = [{'id': m.group(1), 'text': u' '.join(m.group(2).split())}
                for m in OPT.finditer(chunk[cut:])]
        opts = [o for o in opts if o['text']]
        if len(opts) >= 3 and len(stem) > 12:
            out.append({'n': int(num), 'stem': stem, 'options': opts})
    return out


def main(src):
    units, gold, stats = parse(src), [], {'q': 0, 'keyed': 0, 'units': 0}
    for u in units:
        body = u'\n'.join(u.get('_body', [])) if u.get('_body') else None
        raw = io.open(src, encoding='utf8', errors='replace').read().split(u'\n')
        seg = u'\n'.join(raw[u['line_start']:u['line_start'] + u['pages'] + 1])
        m = CYP.search(seg)
        if not m:
            continue
        qs = questions(m.group(1))
        keys = dict((int(a), b) for a, b in KEY.findall(m.group(2)))
        for q in qs:
            q['key'] = keys.get(q['n'])
            stats['q'] += 1
            if q['key']:
                stats['keyed'] += 1
        if qs:
            stats['units'] += 1
            gold.append({'unit': u['unit'], 'module': u['module'],
                         'title': u['title'], 'questions': qs})
    out = {'source': os.path.basename(src), 'note': 'internal gold corpus - not for redistribution',
           'units_with_cyp': stats['units'], 'questions': stats['q'],
           'with_key': stats['keyed'], 'sets': gold}
    if not os.path.isdir('content/gold'):
        os.makedirs('content/gold')
    io.open('content/gold/abfm_cyp.json', 'w', encoding='utf8').write(
        json.dumps(out, indent=1, ensure_ascii=False))
    print(u'units with CYP %d/25 | questions %d | keyed %d'
          % (stats['units'], stats['q'], stats['keyed']))
    for g in gold:
        keyed = sum(1 for q in g['questions'] if q['key'])
        print(u'  %-2d %s  q=%-3d keyed=%-3d' % (g['unit'], g['module'], len(g['questions']), keyed))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'caiib/abfm.txt')
