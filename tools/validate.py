# -*- coding: utf-8 -*-
"""CI gate for the content repo.

Implements the hard invariants in BLUEPRINT.md 3.1, plus the structural rules
added by 2.5 (dual structure), 3.6 (provenance vs grounding) and 3.7
(autonomous verification). Exits non-zero on any error.

    python tools/validate.py
"""
import io, json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANNED_OPTION = re.compile(u'none of the above|all of the above|both a and b',
                           re.I)

errors, warnings = [], []


def err(where, msg):
    errors.append(u'%s: %s' % (where, msg))


def warn(where, msg):
    warnings.append(u'%s: %s' % (where, msg))


def load(pattern):
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
        try:
            data = json.load(io.open(path, encoding='utf8'))
        except ValueError as e:
            err(os.path.relpath(path, ROOT), u'not valid JSON - %s' % e)
            continue
        out.append((os.path.relpath(path, ROOT), data))
    return out


def check_arithmetic(where, item):
    """Recompute the key. The strongest gate available for numeric items."""
    arith = item.get('verification', {}).get('arithmetic')
    if not arith:
        return None
    env = {}
    for g in item.get('given', []):
        name = re.sub(u'[^a-z0-9]+', u'_', g['label'].lower()).strip(u'_')
        env[name] = g['value']
    try:
        got = eval(arith['expression'], {'__builtins__': {}}, dict(env))  # noqa: S307
    except Exception as e:
        err(where, u'arithmetic expression failed: %s (names available: %s)'
            % (e, u', '.join(sorted(env)) or u'none'))
        return False
    tol = arith.get('tolerance', 0.005)
    if abs(got - arith['expected']) > tol:
        err(where, u'arithmetic mismatch: expression gives %s, expected %s'
            % (got, arith['expected']))
        return False
    keyed = [o for o in item['options'] if o.get('key')]
    if keyed and keyed[0].get('value') is not None:
        if abs(keyed[0]['value'] - arith['expected']) > tol:
            err(where, u'key option value %s does not match verified result %s'
                % (keyed[0]['value'], arith['expected']))
            return False
    return True


def main():
    miscon = {}
    for path, m in load('content/misconceptions/*.json'):
        for entry in (m if isinstance(m, list) else [m]):
            mid = entry.get('id')
            if not mid:
                err(path, u'misconception without an id')
                continue
            if mid in miscon:
                err(path, u'duplicate misconception id %s' % mid)
            miscon[mid] = entry
            if entry.get('status') == 'proposed' and entry.get('prevalence') is not None:
                err(path, u'%s is proposed but carries a prevalence - a guess '
                          u'must not be stored as a measurement (3.7)' % mid)
            rungs = entry.get('ladder') or [x for x in (entry.get('canned_hint_l1'),
                                                        entry.get('canned_hint_l2')) if x]
            if len(rungs) < 2:
                err(path, u'%s has fewer than 2 authored ladder rungs - the tutor '
                          u'IS the ladder, there is no model to fall back on (2.3)' % mid)

    # 2.5 - the concept graph is a first-class artefact, not inferred
    concepts, graph = set(), {}
    for path, doc in load('content/concepts/*.json'):
        for c in doc.get('concepts', []):
            cid = c.get('id')
            if not cid:
                err(path, u'concept without an id')
                continue
            if cid in graph:
                err(path, u'duplicate concept %s' % cid)
            graph[cid] = c
            concepts.add(cid)
    for cid, c in graph.items():
        for p in c.get('prereqs', []):
            if p not in graph:
                err('content/concepts', u'%s declares unknown prereq %s' % (cid, p))
    # no cycles: a prerequisite loop would deadlock the scheduler
    def cyclic(node, seen):
        if node in seen:
            return True
        for p in graph.get(node, {}).get('prereqs', []):
            if cyclic(p, seen | {node}):
                return True
        return False
    for cid in graph:
        if cyclic(cid, set()):
            err('content/concepts', u'prerequisite cycle through %s' % cid)

    for e in miscon.values():
        c = e.get('concept')
        if c and concepts and c not in concepts:
            err('content/misconceptions', u'%s cites unknown concept %s' % (e['id'], c))

    items, live = 0, 0

    for path, doc in load('content/items/*.json'):
        for item in (doc if isinstance(doc, list) else [doc]):
            items += 1
            where = u'%s[%s]' % (path, item.get('item_id', '?'))
            opts = item.get('options', [])

            keys = [o for o in opts if o.get('key')]
            if len(keys) != 1:
                err(where, u'expected exactly one key, found %d' % len(keys))

            for o in opts:
                if o.get('key'):
                    continue
                if BANNED_OPTION.search(o.get('text', '')):
                    err(where, u'option %s is a filler distractor - every '
                               u'distractor must encode a misconception (3.1)' % o['id'])
                mid = o.get('misconception')
                if not mid:
                    err(where, u'distractor %s has no misconception (3.1)' % o['id'])
                elif mid not in miscon:
                    err(where, u'distractor %s cites unknown misconception %s' % (o['id'], mid))
                elif miscon[mid].get('status') == 'demoted':
                    err(where, u'distractor %s cites demoted misconception %s' % (o['id'], mid))

            # 3.6 - the learner-facing source is never the textbook. Authority is
            # a statute, a notified standard, or - for pure finance maths - the
            # definition together with the recomputed working. The book lives
            # only in derived_from, as internal provenance.
            regime = item.get('grounding_regime')
            kinds = set()
            for g in item.get('grounding', []):
                k = g.get('kind')
                kinds.add(k)
                if k not in ('statute', 'standard', 'definition'):
                    err(where, u'grounding kind "%s" - the learner-facing source must be a '
                               u'statute, a standard or a definition, never the textbook (3.6)' % k)
                if k in ('statute', 'standard') and not g.get('version'):
                    err(where, u'%s grounding with no version/date - a citation to a '
                               u'regulation must say which issue of it (13.4)' % k)
            if regime == 'statutory' and not kinds & {'statute', 'standard'}:
                err(where, u'statutory item with no statute or standard cited (3.6)')
            if 'definition' in kinds and kinds <= {'definition'}:
                numeric = any(o.get('value') is not None for o in item.get('options', []))
                if numeric and not (item.get('verification') or {}).get('arithmetic'):
                    err(where, u'grounded only on a definition, with no arithmetic proof - '
                               u'for finance maths the working IS the authority (3.6)')
            if not item.get('grounding'):
                err(where, u'no grounding')
            if item.get('derived_from') is None and regime == 'doctrinal':
                warn(where, u'doctrinal item with no derived_from - an edition change '
                            u'cannot compute its blast radius (3.6)')

            # 2.5 - both structures present
            if not item.get('concept'):
                err(where, u'no concept - the scheduler has nothing to sequence on (2.5)')
            for p in item.get('prereqs', []):
                if concepts and p not in concepts:
                    warn(where, u'prereq "%s" matches no known concept' % p)

            # 3.7 - verification gauntlet
            v = item.get('verification') or {}
            state = item.get('lifecycle', {}).get('state')
            if state in ('live', 'field'):
                live += 1
                if not v.get('second_model_agrees'):
                    err(where, u'state=%s without independent second-model '
                               u'agreement (3.7)' % state)
                if not v.get('entailed_span'):
                    err(where, u'state=%s without an entailing span (3.7)' % state)
                if v.get('derivation_overlap', 0) > 0.35:
                    err(where, u'derivation overlap %.2f - too close to the source '
                               u'passage (3.6)' % v['derivation_overlap'])
                numeric = any(o.get('value') is not None for o in opts)
                if numeric and not v.get('arithmetic'):
                    err(where, u'numeric item is live with no arithmetic check - '
                               u'recomputation is the strongest gate we have (3.7)')

            check_arithmetic(where, item)

            ps = item.get('psychometrics') or {}
            if ps.get('a') is not None and ps['a'] < 0 and ps.get('n_responses', 0) >= 200:
                if state != 'retired':
                    err(where, u'discrimination a=%.2f at n=%d - negative '
                               u'discrimination must auto-retire (3.7)'
                        % (ps['a'], ps['n_responses']))

    # Key-position skew: if the key sits at one letter most of the time, a
    # learner (or a verifier) reads the pattern instead of the question. The
    # first drafts had it at A every time.
    positions = []
    for path, doc in load('content/items/*.json'):
        for item in (doc if isinstance(doc, list) else [doc]):
            k = [o.get('id') for o in item.get('options', []) if o.get('key')]
            if k:
                positions.append(k[0])
    if len(positions) >= 6:
        top = max(set(positions), key=positions.count)
        share = positions.count(top) / float(len(positions))
        if share > 0.5:
            err('content/items', u'key is at %s in %d of %d items - shuffle option order'
                % (top, positions.count(top), len(positions)))

    print(u'misconceptions %d | items %d (%d live/field) | concepts %d'
          % (len(miscon), items, live, len(concepts)))
    for w in warnings:
        print(u'  WARN  %s' % w)
    for e in errors:
        print(u'  ERROR %s' % e)
    if errors:
        print(u'\nFAILED - %d error(s)' % len(errors))
        return 1
    print(u'\nOK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
