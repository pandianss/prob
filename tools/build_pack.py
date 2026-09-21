# -*- coding: utf-8 -*-
"""Build the Android content pack from the validated content repo.

The app loads the same JSON that tools/validate.py gates, so what ships on the
phone is what passed CI. There is no second content format to keep in step -
this only reshapes and filters.

Only `live` and `field` items are emitted: an item pulled to `review` because
its source changed must not sit in a pack waiting to be served (BLUEPRINT 3.5).

    python tools/build_pack.py
"""
import glob, io, json, os, sys

OUT = os.path.join('android', 'app', 'src', 'main', 'assets', 'content')
SERVABLE = ('live', 'field')


def load_all(pattern):
    rows = []
    for path in sorted(glob.glob(pattern)):
        doc = json.load(io.open(path, encoding='utf8'))
        rows.extend(doc if isinstance(doc, list) else [doc])
    return rows


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    concepts = []
    for path in sorted(glob.glob('content/concepts/*.json')):
        concepts.extend(json.load(io.open(path, encoding='utf8')).get('concepts', []))

    misconceptions = load_all('content/misconceptions/*.json')
    items = [i for i in load_all('content/items/*.json')
             if i.get('lifecycle', {}).get('state') in SERVABLE]

    # Flatten grounding to the one locator the learner actually sees. Internal
    # provenance (derived_from) is deliberately NOT shipped: it exists for
    # blast-radius queries and for defending derivation, not for display.
    packed_items = []
    for it in items:
        g = (it.get('grounding') or [{}])[0]
        packed_items.append({
            'item_id': it['item_id'],
            'syllabus_node': it['syllabus_node'],
            'concept': it['concept'],
            'stem': it['stem'],
            'given': it.get('given', []),
            'options': [{'id': o['id'], 'text': o['text'],
                         'key': bool(o.get('key')),
                         'misconception': o.get('misconception')}
                        for o in it['options']],
            'resolution': it.get('resolution', ''),
            'grounding': [{'source': g.get('source', ''), 'locator': g.get('locator', '')}],
            'psychometrics': {'a': (it.get('psychometrics') or {}).get('a'),
                              'b': (it.get('psychometrics') or {}).get('b')},
            'lifecycle': {'state': it['lifecycle']['state']},
        })

    packed_mis = []
    short = []
    for m in misconceptions:
        rungs = m.get('ladder') or [x for x in (m.get('canned_hint_l1'),
                                                m.get('canned_hint_l2')) if x]
        if len(rungs) < 4:
            short.append(m['id'])
        packed_mis.append({
            'id': m['id'], 'statement': m['statement'], 'concept': m['concept'],
            'remediation_strategy': m['remediation_strategy'],
            'status': m.get('status', 'proposed'),
            'prevalence': m.get('prevalence'),
            'ladder': rungs,
        })

    write(os.path.join(OUT, 'concepts.json'), concepts)
    write(os.path.join(OUT, 'misconceptions.json'), packed_mis)
    write(os.path.join(OUT, 'items.json'), packed_items)

    print(u'pack -> %s' % OUT)
    print(u'  concepts       %d' % len(concepts))
    print(u'  misconceptions %d' % len(packed_mis))
    print(u'  items          %d (servable only)' % len(packed_items))
    if short:
        print(u'\n  NOTE: %d misconception(s) have a ladder shorter than 4 rungs;'
              % len(short))
        print(u'  the ladder simply ends sooner. RESOLVE still fires either way.')
        for mid in short:
            print(u'    %s' % mid)
    return 0


def write(path, obj):
    io.open(path, 'w', encoding='utf8').write(
        json.dumps(obj, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())
