# -*- coding: utf-8 -*-
"""Autonomous item authoring: draft, verify independently, gate, report yield.

Implements BLUEPRINT.md 3.7. The whole design rests on one rule:

    The verifier never sees the drafter's reasoning.

It gets the finished item and the source passage, nothing else - separate call,
separate system prompt, no shared context. Sharing the drafting rationale turns
an independent check into an agreement machine.

Rejects are the product here as much as the survivors: the reject log is the
only diagnostic available for grounding coverage, and the yield it reports is
what sets both cost and coverage (BLUEPRINT.md 3.3).

    python tools/author.py --unit 8 --n 12            # draft and verify
    python tools/author.py --unit 8 --n 12 --dry-run  # prompts + cost, no calls
    python tools/author.py --unit 8 --n 12 --batch    # Batches API, 50% cost
"""
import argparse, io, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_abfm import parse

DRAFT_MODEL = os.environ.get('PROBANKER_DRAFT_MODEL', 'claude-opus-5')
VERIFY_MODEL = os.environ.get('PROBANKER_VERIFY_MODEL', 'claude-opus-5')

# --------------------------------------------------------------------------
# Prompts. Draft and verify share no text on purpose.
# --------------------------------------------------------------------------

DRAFT_SYSTEM = """\
You author diagnostic exam items for Indian banking certifications (IIBF CAIIB).

Rules, all hard:
- Every wrong option encodes ONE named misconception from the supplied catalogue.
  A distractor that is merely wrong, or wrong at random, is a defect.
- No "none of the above", "all of the above", or "both A and B".
- Exactly one correct option.
- Numeric items: the key must follow from the given figures by a stated
  computation. Supply that computation as a Python expression over the `given`
  labels, lowercased with non-alphanumerics as underscores.
- Write the item in your own words. Do not reproduce the source passage's
  sentences, worked examples, or question wording.
- State every figure the item needs. An item the reader cannot answer from the
  stem alone is a defect.
- If the passage does not support an item on a misconception, return fewer
  items. Never invent a figure, a rule, or a threshold to fill the quota."""

VERIFY_SYSTEM = """\
You verify exam items against a source passage. You did not write these items \
and you have no stake in them.

Work in this order, independently:
1. Answer the question yourself from the passage and the given figures, before
   looking at which option is marked correct.
2. Locate the span of the passage that entails your answer. Quote it exactly.
   If no span entails it, say so.
3. Check every number in the item traces to the passage or to the item's own
   given figures. Flag any that does not.
4. Judge each distractor: does it plausibly arise from the misconception it
   claims, and is it clearly wrong?
5. Judge whether the item copies the passage's wording or its worked example.

Report what you find. Do not repair the item, and do not give it the benefit of
the doubt: an item you cannot confirm is one the system will discard, which is
the intended outcome."""

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "stem": {"type": "string"},
                    "concept": {"type": "string"},
                    "syllabus_ref": {"type": "string"},
                    "given": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "number"},
                                "unit": {"type": "string"},
                            },
                            "required": ["label", "value", "unit"],
                            "additionalProperties": False,
                        },
                    },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string"},
                                "value": {"type": ["number", "null"]},
                                "key": {"type": "boolean"},
                                "misconception": {"type": ["string", "null"]},
                            },
                            "required": ["id", "text", "value", "key", "misconception"],
                            "additionalProperties": False,
                        },
                    },
                    "arithmetic_expression": {"type": ["string", "null"]},
                    "expected_value": {"type": ["number", "null"]},
                },
                "required": ["stem", "concept", "syllabus_ref", "given", "options",
                             "arithmetic_expression", "expected_value"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "my_answer": {"type": "string"},
        "agrees_with_key": {"type": "boolean"},
        "entailed_span": {"type": ["string", "null"]},
        "untraceable_numbers": {"type": "array", "items": {"type": "string"}},
        "bad_distractors": {"type": "array", "items": {"type": "string"}},
        "copies_source": {"type": "boolean"},
        "answerable_from_stem": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["my_answer", "agrees_with_key", "entailed_span", "untraceable_numbers",
                 "bad_distractors", "copies_source", "answerable_from_stem", "reason"],
    "additionalProperties": False,
}


# --------------------------------------------------------------------------
# Deterministic gates - no model, no network
# --------------------------------------------------------------------------

BANNED = re.compile(u'none of the above|all of the above|both [a-d] and', re.I)


def slug(label):
    return re.sub(u'[^a-z0-9]+', u'_', label.lower()).strip(u'_')


def gate_structural(item):
    bad = []
    opts = item.get('options') or []
    keys = [o for o in opts if o.get('key')]
    if len(keys) != 1:
        bad.append(u'expected one key, found %d' % len(keys))
    if len(opts) < 3:
        bad.append(u'only %d options' % len(opts))
    for o in opts:
        if BANNED.search(o.get('text') or u''):
            bad.append(u'filler option %s' % o.get('id'))
        if not o.get('key') and not o.get('misconception'):
            bad.append(u'distractor %s has no misconception' % o.get('id'))
    return bad


def gate_arithmetic(item):
    """Recompute the key. The strongest gate available, and it needs no model."""
    expr = item.get('arithmetic_expression')
    if not expr:
        numeric = any(o.get('value') is not None for o in item.get('options') or [])
        return [u'numeric item with no arithmetic expression'] if numeric else []
    env = dict((slug(g['label']), g['value']) for g in item.get('given') or [])
    try:
        got = eval(expr, {'__builtins__': {}}, env)  # noqa: S307
    except Exception as e:
        return [u'expression failed: %s (have: %s)' % (e, u', '.join(sorted(env)) or u'nothing')]
    exp = item.get('expected_value')
    if exp is None:
        return [u'no expected_value to check against']
    if abs(got - exp) > max(abs(exp) * 0.005, 0.005):
        return [u'expression gives %.4f, expected %.4f' % (got, exp)]
    key = next((o for o in item['options'] if o.get('key')), None)
    if key and key.get('value') is not None and abs(key['value'] - exp) > max(abs(exp) * 0.005, 0.005):
        return [u'key option %.4f does not match computed %.4f' % (key['value'], exp)]
    return []


def gate_verdict(v):
    bad = []
    if not v.get('agrees_with_key'):
        bad.append(u'verifier disagrees with the key (said %s)' % v.get('my_answer'))
    if not v.get('entailed_span'):
        bad.append(u'no entailing span in the source')
    if v.get('untraceable_numbers'):
        bad.append(u'untraceable numbers: %s' % u'; '.join(v['untraceable_numbers'][:3]))
    if v.get('copies_source'):
        bad.append(u'copies the source passage too closely')
    if not v.get('answerable_from_stem', True):
        bad.append(u'not answerable from the stem alone')
    if v.get('bad_distractors'):
        bad.append(u'weak distractors: %s' % u'; '.join(v['bad_distractors'][:3]))
    return bad


# --------------------------------------------------------------------------
# Source + catalogue
# --------------------------------------------------------------------------

def passage_for(src, unit):
    raw = io.open(src, encoding='utf8', errors='replace').read().split(u'\n')
    u = [x for x in parse(src) if x['unit'] == unit]
    if not u:
        raise SystemExit(u'unit %d not found' % unit)
    u = u[0]
    text = u'\n'.join(raw[u['line_start']:u['line_start'] + u['pages'] + 1])
    return u, re.sub(u'\\s+', u' ', text).strip()


def catalogue():
    out = []
    d = os.path.join('content', 'misconceptions')
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.json'):
                doc = json.load(io.open(os.path.join(d, fn), encoding='utf8'))
                out.extend(doc if isinstance(doc, list) else [doc])
    return out


def page_images(unit):
    """Page images for a unit, as API image blocks (tools/pdf_pages.py).

    The last block carries cache_control so every draft and every verify call
    after the first reads the pages from cache instead of paying for them again
    - on a 14-page unit that is most of the input tokens.
    """
    import base64, glob
    files = sorted(glob.glob(os.path.join('content', '_pages', 'u%02d' % unit, '*.jpg')))
    if not files:
        raise SystemExit('no page images for unit %d - run: python tools/pdf_pages.py --unit %d'
                         % (unit, unit))
    blocks = []
    for f in files:
        data = base64.standard_b64encode(io.open(f, 'rb').read()).decode('ascii')
        blocks.append({"type": "image",
                       "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
    blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return blocks, len(files)


def as_content(source, text):
    """Text source -> one string. Image source -> the page blocks, then the ask."""
    if isinstance(source, list):
        return source + [{"type": "text", "text": text}]
    return text


def draft_prompt(unit, passage, cat, n):
    lines = [u'%s\n    %s' % (m['id'], m['statement']) for m in cat]
    if passage is None:
        return (u'SOURCE: the page images above are Unit %d - %s, in order. Read '
                u'formulas and tables exactly as printed; a stacked fraction is a '
                u'division.\n\nMISCONCEPTION CATALOGUE:\n%s\n\nAuthor %d items grounded '
                u'in these pages. Fewer is correct if the pages do not support %d.'
                % (unit['unit'], unit['title'], u'\n'.join(lines), n, n))
    return (u'SOURCE PASSAGE (Unit %d - %s):\n"""\n%s\n"""\n\n'
            u'MISCONCEPTION CATALOGUE:\n%s\n\n'
            u'Author %d items grounded in this passage. Fewer is correct if the '
            u'passage does not support %d.'
            % (unit['unit'], unit['title'], passage, u'\n'.join(lines), n, n))


def verify_prompt(item, passage):
    shown = dict(item)
    shown.pop('arithmetic_expression', None)   # never show the drafter's working
    shown.pop('expected_value', None)
    item_json = json.dumps(shown, indent=1, ensure_ascii=False)
    if passage is None:
        return (u'SOURCE: the page images above. Quote the entailing span as it '
                u'appears on the page.\n\nITEM:\n%s' % item_json)
    return (u'SOURCE PASSAGE:\n"""\n%s\n"""\n\nITEM:\n%s' % (passage, item_json))


# --------------------------------------------------------------------------

def report(results, unit, elapsed, usage):
    total = len(results)
    passed = [r for r in results if not r['rejects']]
    print(u'\n' + u'=' * 66)
    print(u'YIELD  unit %d  %s' % (unit['unit'], unit['title']))
    print(u'=' * 66)
    print(u'  drafted   %d' % total)
    print(u'  survived  %d  (%.0f%%)' % (len(passed), 100.0 * len(passed) / total if total else 0))
    reasons = {}
    for r in results:
        for b in r['rejects']:
            k = b.split(u':')[0].split(u'(')[0].strip()[:46]
            reasons[k] = reasons.get(k, 0) + 1
    if reasons:
        print(u'\n  rejected by:')
        for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(u'    %-48s %d' % (k, v))
    if usage:
        print(u'\n  tokens in/out  %d / %d' % (usage['in'], usage['out']))
        cost = usage['in'] / 1e6 * 5.0 + usage['out'] / 1e6 * 25.0
        print(u'  cost           $%.4f   ($%.4f per surviving item)'
              % (cost, cost / len(passed) if passed else 0))
    print(u'  elapsed        %.1fs' % elapsed)
    print(u'\n  Rejects are the diagnostic: a gate that dominates points at the')
    print(u'  drafting prompt; thin entailment points at the source (3.3).')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--unit', type=int, default=8)
    ap.add_argument('--n', type=int, default=10)
    ap.add_argument('--src', default='caiib/abfm.txt')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', default='content/items/_authored.json')
    ap.add_argument('--images', action='store_true',
                    help='author from page images (tools/pdf_pages.py) instead of the '
                         'text extraction - use for units whose formulas and tables '
                         'the extraction flattened (BLUEPRINT 3.8)')
    args = ap.parse_args()

    unit, passage = passage_for(args.src, args.unit)
    source = passage
    if args.images:
        source, n_pages = page_images(args.unit)
        passage = None
        print(u'source: %d page images for unit %d' % (n_pages, args.unit))
    cat = catalogue()
    if not cat:
        raise SystemExit('no misconception catalogue in content/misconceptions/')
    dp = draft_prompt(unit, passage, cat, args.n)

    if args.dry_run:
        approx = (len(DRAFT_SYSTEM) + len(dp)) / 3.6
        print(u'DRAFT SYSTEM\n%s\n' % DRAFT_SYSTEM)
        print(u'DRAFT PROMPT (%d chars, ~%d tokens)\n%s...\n'
              % (len(dp), approx, dp[:1200]))
        print(u'VERIFY SYSTEM\n%s\n' % VERIFY_SYSTEM)
        print(u'source %s | catalogue %d | requested %d items'
              % ('%d page images' % len(source) if isinstance(source, list)
                 else '%d chars of text' % len(passage), len(cat), args.n))
        print(u'\nverifier sees: the item (minus the drafter working) + the passage. '
              u'Nothing else.')
        return 0

    try:
        import anthropic
    except ImportError:
        raise SystemExit('pip install anthropic')

    client = anthropic.Anthropic()
    usage = {'in': 0, 'out': 0}
    t0 = time.time()

    print(u'drafting %d items from unit %d (%s)...' % (args.n, args.unit, DRAFT_MODEL))
    r = client.messages.create(
        model=DRAFT_MODEL, max_tokens=16000,
        system=[{"type": "text", "text": DRAFT_SYSTEM,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": as_content(source, dp)}],
        output_config={"format": {"type": "json_schema", "schema": ITEM_SCHEMA},
                       "effort": "high"},
    )
    usage['in'] += r.usage.input_tokens
    usage['out'] += r.usage.output_tokens
    drafted = json.loads(next(b.text for b in r.content if b.type == 'text'))['items']
    print(u'  drafted %d' % len(drafted))

    results = []
    for i, item in enumerate(drafted, 1):
        rejects = gate_structural(item) + gate_arithmetic(item)
        verdict = None
        if not rejects:                       # don't pay to verify a broken item
            vr = client.messages.create(
                model=VERIFY_MODEL, max_tokens=8000,
                system=[{"type": "text", "text": VERIFY_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": as_content(source, verify_prompt(item, passage))}],
                output_config={"format": {"type": "json_schema", "schema": VERDICT_SCHEMA},
                               "effort": "high"},
            )
            usage['in'] += vr.usage.input_tokens
            usage['out'] += vr.usage.output_tokens
            verdict = json.loads(next(b.text for b in vr.content if b.type == 'text'))
            rejects = gate_verdict(verdict)
        results.append({'item': item, 'verdict': verdict, 'rejects': rejects})
        print(u'  %2d. %s  %s' % (i, u'PASS' if not rejects else u'DROP',
                                  u'' if not rejects else rejects[0][:72]))

    io.open(args.out, 'w', encoding='utf8').write(
        json.dumps({'unit': args.unit, 'model': DRAFT_MODEL, 'results': results},
                   indent=1, ensure_ascii=False))
    report(results, unit, time.time() - t0, usage)
    print(u'\n  full log -> %s' % args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
