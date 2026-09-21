# -*- coding: utf-8 -*-
"""Rebuild the computation tables the extraction flattened, and prove them.

Earlier assessment was too pessimistic. A table survives as a row-major stream:

    Years 2021 2022 2023 2024
    Earnings before tax and depreciation 45,000 30,000 25,000 35,000
    Less: Depreciation (25,000) (25,000) (25,000) (25,000)
    Earnings before tax 20,000 5,000 0 10,000

The grid is gone but each row is contiguous and ordered, so the table is
reconstructable as <label> + value vector. Better still, a financial statement
is internally redundant - one row is the sum or difference of others - so the
reconstruction can be PROVED rather than trusted (BLUEPRINT.md 3.7).

    python tools/recover_tables.py [caiib/abfm.txt]
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_abfm import parse

NUM = u'\\(?-?[0-9][0-9,]*(?:\\.[0-9]+)?\\)?'
ROW = re.compile(u'([A-Za-z][A-Za-z ,.:@%&/()\\-]{3,58}?)\\s+((?:' + NUM + u'\\s+){1,7}' + NUM + u')(?=\\s|$)')
TOK = re.compile(NUM)


def val(tok):
    neg = tok.startswith(u'(') and tok.endswith(u')')
    t = tok.strip(u'()').replace(u',', u'')
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def rows_in(text):
    out = []
    for m in ROW.finditer(text):
        label = u' '.join(m.group(1).split())
        vals = [val(t) for t in TOK.findall(m.group(2))]
        vals = [v for v in vals if v is not None]
        if len(vals) >= 2 and len(label) > 3:
            out.append({'label': label, 'values': vals})
    return out


def tables(rows, min_rows=3):
    """Group consecutive rows that share a column count."""
    groups, cur = [], []
    for r in rows:
        if cur and len(r['values']) == len(cur[-1]['values']):
            cur.append(r)
        else:
            if len(cur) >= min_rows:
                groups.append(cur)
            cur = [r]
    if len(cur) >= min_rows:
        groups.append(cur)
    return groups


def prove(tbl):
    """Find rows that are the column-wise sum or difference of earlier rows."""
    proofs, n = [], len(tbl[0]['values'])
    for k in range(2, len(tbl)):
        target = tbl[k]['values']
        for i in range(k):
            for j in range(i + 1, k):
                a, b = tbl[i]['values'], tbl[j]['values']
                if len(a) != n or len(b) != n:
                    continue
                for sym, fn in ((u'+', lambda x, y: x + y), (u'-', lambda x, y: x - y)):
                    if all(abs(fn(a[c], b[c]) - target[c]) <= max(abs(target[c]) * 0.005, 0.5)
                           for c in range(n)):
                        proofs.append({
                            'derived': tbl[k]['label'],
                            'from': [tbl[i]['label'], tbl[j]['label']],
                            'operator': sym,
                        })
                        break
                if proofs and proofs[-1]['derived'] == tbl[k]['label']:
                    break
            if proofs and proofs[-1]['derived'] == tbl[k]['label']:
                break
    return proofs


def main(src):
    raw = io.open(src, encoding='utf8', errors='replace').read().split(u'\n')
    out, n_tab, n_proved = [], 0, 0
    for u in parse(src):
        if u['module'] not in ('B', 'C'):
            continue
        seg = u'\n'.join(raw[u['line_start']:u['line_start'] + u['pages'] + 1])
        found = []
        for tbl in tables(rows_in(seg)):
            proofs = prove(tbl)
            n_tab += 1
            if proofs:
                n_proved += 1
            found.append({'rows': len(tbl), 'cols': len(tbl[0]['values']),
                          'labels': [r['label'][:44] for r in tbl],
                          'table': tbl, 'proofs': proofs})
        if found:
            out.append({'unit': u['unit'], 'module': u['module'], 'title': u['title'],
                        'tables': found})
    io.open('content/abfm_tables.json', 'w', encoding='utf8').write(
        json.dumps({'source': os.path.basename(src), 'tables': n_tab,
                    'internally_proved': n_proved, 'units': out},
                   indent=1, ensure_ascii=False))
    pct = (100.0 * n_proved / n_tab) if n_tab else 0.0
    print(u'candidate tables %d | internally proved %d (%.0f%%)' % (n_tab, n_proved, pct))
    for u in out:
        pv = sum(1 for t in u['tables'] if t['proofs'])
        print(u'  U%-2d %s  tables=%-3d proved=%-3d' % (u['unit'], u['module'],
                                                        len(u['tables']), pv))
    for u in out:
        for t in u['tables']:
            if t['proofs']:
                print(u'\n  U%d sample - %d rows x %d cols' % (u['unit'], t['rows'], t['cols']))
                for p in t['proofs'][:4]:
                    print(u'      %-32s = %-28s %s %s' % (p['derived'][:32], p['from'][0][:28],
                                                          p['operator'], p['from'][1][:24]))
                return


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'caiib/abfm.txt')
