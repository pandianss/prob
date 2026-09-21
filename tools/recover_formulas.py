# -*- coding: utf-8 -*-
"""Recover formulas the text extraction flattened, and verify each by arithmetic.

The extraction loses the fraction bar, so `EBIT / EBT` arrives as `EBIT EBT`.
But the worked examples keep their numbers:

    Degree of Financial Leverage = EBIT EBT = 2,00,000 1,00,000 = 2

So the operator is not guessed - it is *recovered and proved*. We hypothesise
each operator, test it against the numeric instance, and accept only the one
that reproduces the stated result. A relation with no numeric instance is not
recovered, and under BLUEPRINT.md 3.7 that means it is not authored.

    python tools/recover_formulas.py [caiib/abfm.txt]
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_abfm import parse

# "= 2,00,000 1,00,000 = 2" / "= 16,18,200 11,74,200 = 1.38"
INSTANCE = re.compile(
    u'([A-Za-z][A-Za-z ()/ΕΒΙΤ-]{3,70}?)'          # name
    u'\\s*=\\s*'
    u'([A-Za-z][A-Za-z ()ΕΒΙΤ-]{2,60}?)'           # symbolic operands
    u'\\s*=\\s*'
    u'([0-9][0-9,]*(?:\\.[0-9]+)?)\\s+([0-9][0-9,]*(?:\\.[0-9]+)?)'    # two numbers
    u'\\s*=\\s*'
    u'([0-9]+(?:\\.[0-9]+)?)')                                          # result

OPS = [
    (u'/', lambda a, b: a / b if b else None),
    (u'*', lambda a, b: a * b),
    (u'-', lambda a, b: a - b),
    (u'+', lambda a, b: a + b),
]


def num(s):
    """Indian grouping: 2,00,000 -> 200000."""
    try:
        return float(s.replace(u',', u''))
    except ValueError:
        return None


def recover(text):
    out = []
    for m in INSTANCE.finditer(text):
        name = u' '.join(m.group(1).split())
        operands = u' '.join(m.group(2).split())
        a, b, res = num(m.group(3)), num(m.group(4)), num(m.group(5))
        if a is None or b is None or res is None:
            continue
        # accept an operator only if it reproduces the printed result
        matched = []
        for sym, fn in OPS:
            try:
                got = fn(a, b)
            except ZeroDivisionError:
                continue
            if got is None:
                continue
            tol = max(abs(res) * 0.01, 0.005)   # printed results are rounded
            if abs(got - res) <= tol:
                matched.append(sym)
        if len(matched) == 1:
            parts = operands.split()
            out.append({
                'name': name[-60:],
                'operands': operands,
                'operator': matched[0],
                'relation': (u'%s %s %s' % (parts[0], matched[0], u' '.join(parts[1:]))
                             if len(parts) >= 2 else operands),
                'proof': {'a': a, 'b': b, 'result': res},
                'verified': True,
            })
        else:
            out.append({'name': name[-60:], 'operands': operands,
                        'operator': None, 'candidates': matched,
                        'proof': {'a': a, 'b': b, 'result': res},
                        'verified': False})
    return out


def main(src):
    raw = io.open(src, encoding='utf8', errors='replace').read().split(u'\n')
    units, report, tot, ver = parse(src), [], 0, 0
    for u in units:
        seg = u'\n'.join(raw[u['line_start']:u['line_start'] + u['pages'] + 1])
        found = recover(seg)
        if not found:
            continue
        v = sum(1 for f in found if f['verified'])
        tot += len(found)
        ver += v
        report.append({'unit': u['unit'], 'module': u['module'], 'title': u['title'],
                       'instances': len(found), 'verified': v, 'relations': found})
    io.open('content/abfm_formulas.json', 'w', encoding='utf8').write(
        json.dumps({'source': os.path.basename(src), 'instances': tot,
                    'verified': ver, 'units': report}, indent=1, ensure_ascii=False))
    pct = (100.0 * ver / tot) if tot else 0.0
    print(u'numeric instances %d | operator recovered and proved %d (%.0f%%)' % (tot, ver, pct))
    for r in report:
        print(u'  U%-2d %s  instances=%-3d verified=%-3d' % (r['unit'], r['module'],
                                                             r['instances'], r['verified']))
        seen = set()
        for f in r['relations']:
            if f['verified'] and f['relation'] not in seen:
                seen.add(f['relation'])
                print(u'        %-34s  [%g %s %g = %g]' % (
                    f['relation'][:34], f['proof']['a'], f['operator'],
                    f['proof']['b'], f['proof']['result']))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'caiib/abfm.txt')
