# -*- coding: utf-8 -*-
"""Read an external verifier's verdicts back into the content repo.

Pairs with tools/verify_packet.py. For each item the verifier worked blind,
this maps its answer back through the shuffle, compares it to the hidden key,
and applies the BLUEPRINT 3.7 rules:

    AGREE    verifier's answer matches the key, a supporting span was found,
             every number traces, answerable from the stem, not ambiguous,
             not copied from the source
    DISAGREE verifier chose a different option (or NONE)
    REJECT   answer matches, but some other check failed

Nothing is ever auto-resolved in the key's favour. A disagreement is shown to
you with the verifier's working; it is either a wrong key or an ambiguous
item, and both mean the item does not ship as written.

    python tools/ingest_verdicts.py v20260923-101500            # report only
    python tools/ingest_verdicts.py v20260923-101500 --apply    # record AGREEs
    python tools/ingest_verdicts.py v20260923-101500 --apply --promote
                                    # ...and move AGREEs from draft to field
"""
import argparse, io, json, os, sys

VERIFY_ROOT = os.path.join('content', '_verify')


def load(path):
    return json.load(io.open(path, encoding='utf8'))


def judge(v, key_letter_original, relabel):
    """Return (status, reasons, answer_as_original_option_id)."""
    ans = v.get('my_answer')
    original = relabel.get(ans) if ans in relabel else None
    if original != key_letter_original:
        return 'DISAGREE', ['verifier answered %s (= our %s), key is %s'
                            % (ans, original or 'NONE', key_letter_original)], original
    reasons = []
    if not (v.get('entailed_span') or '').strip():
        reasons.append('no supporting span on any page')
    if v.get('untraceable_numbers'):
        reasons.append('untraceable: %s' % '; '.join(v['untraceable_numbers'][:3]))
    if not v.get('answerable_from_stem', False):
        reasons.append('not answerable from the stem alone')
    if v.get('ambiguous'):
        reasons.append('more than one option defensible')
    if v.get('copies_source'):
        reasons.append('copies the source')
    return ('REJECT' if reasons else 'AGREE'), reasons, original


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('packet')
    ap.add_argument('--verifier', default='gemini/antigravity',
                    help='recorded as who verified')
    ap.add_argument('--apply', action='store_true', help='record AGREE verdicts')
    ap.add_argument('--promote', action='store_true',
                    help='with --apply, move AGREE items from draft to field')
    a = ap.parse_args()

    folder = os.path.join(VERIFY_ROOT, a.packet)
    mapping = load(os.path.join(VERIFY_ROOT, a.packet + '.key.json'))
    vpath = os.path.join(folder, 'verdicts.json')
    if not os.path.exists(vpath):
        raise SystemExit('no verdicts.json in %s yet' % folder)
    verdicts = load(vpath)
    if isinstance(verdicts, dict):          # tolerate {"verdicts": [...]}
        verdicts = verdicts.get('verdicts', [])

    by_id = dict((v.get('packet_id'), v) for v in verdicts)
    missing = [pid for pid in mapping if pid not in by_id]
    unknown = [pid for pid in by_id if pid not in mapping]

    results = []
    for pid, m in mapping.items():
        v = by_id.get(pid)
        if v is None:
            results.append((pid, m, 'MISSING', ['verifier returned nothing'], None, None))
            continue
        status, reasons, ans = judge(v, m['key'], m['relabel'])
        results.append((pid, m, status, reasons, ans, v))

    counts = {}
    print(u'%-26s %-9s %s' % ('item', 'verdict', 'detail'))
    for pid, m, status, reasons, ans, v in results:
        counts[status] = counts.get(status, 0) + 1
        print(u'%-26s %-9s %s' % (m['item_id'][:26], status, reasons[0] if reasons else
                                  (u'p%s: "%s"' % (v.get('span_page'), (v.get('entailed_span') or '')[:60]))))
        if status == 'DISAGREE' and v:
            print(u'%36s working: %s' % ('', (v.get('working') or '')[:160]))
        for r in reasons[1:]:
            print(u'%36s %s' % ('', r))

    total = len(results)
    agree = counts.get('AGREE', 0)
    print(u'\n%d items: %s' % (total, ', '.join('%s %d' % kv for kv in sorted(counts.items()))))
    print(u'verification yield: %d/%d (%.0f%%)' % (agree, total, 100.0 * agree / total if total else 0))
    if unknown:
        print(u'ignored %d verdict(s) with unknown packet_id' % len(unknown))
    if counts.get('DISAGREE'):
        print(u'\nDISAGREEMENTS are not resolved automatically. Each is a wrong key or an')
        print(u'ambiguous item; either way it does not ship as written.')

    if not a.apply:
        print(u'\n(report only - pass --apply to record the AGREE verdicts)')
        return 0

    by_file = {}
    for pid, m, status, reasons, ans, v in results:
        by_file.setdefault(m['file'], []).append((m, status, v))
    changed = 0
    for f, rows in by_file.items():
        items = load(f)
        idx = dict((it['item_id'], it) for it in items)
        for m, status, v in rows:
            it = idx.get(m['item_id'])
            if it is None:
                continue
            ver = it.setdefault('verification', {})
            if status == 'AGREE':
                ver['second_model_agrees'] = True
                ver['entailed_span'] = v['entailed_span']
                ver['verifier'] = {'model': a.verifier, 'packet': a.packet,
                                   'span_page': v.get('span_page')}
                if a.promote and it.get('lifecycle', {}).get('state') == 'draft':
                    it['lifecycle']['state'] = 'field'
                changed += 1
            else:
                # Record the failure so the item cannot drift back to looking
                # verified; leave it in draft.
                ver['second_model_agrees'] = False
                ver['verifier'] = {'model': a.verifier, 'packet': a.packet,
                                   'verdict': status}
        io.open(f, 'w', encoding='utf8').write(
            json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    print(u'\nrecorded %d AGREE verdict(s)%s. Run tools/validate.py next.'
          % (changed, ' and promoted them to field' if a.promote else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
