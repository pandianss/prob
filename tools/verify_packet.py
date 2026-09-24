# -*- coding: utf-8 -*-
"""Build a blind verification packet for an external verifier (BLUEPRINT 3.7).

The verifier is meant to be independent of the drafter, so the packet carries
only what it needs to work each item from scratch:

    kept:     stem, given figures, option texts, the section locator,
              and the page images of that unit
    removed:  the key, option values, misconception labels, the arithmetic
              expression, the resolution, provenance, and our own quoted span

Option order is shuffled per item and relabelled. The drafts put the key at
A every time, and a verifier (or a learner) would read that pattern within a
few items. The mapping back to the real options is written OUTSIDE the packet
folder, so opening the folder in another tool cannot leak it.

    python tools/verify_packet.py                       # unverified drafts
    python tools/verify_packet.py --items content/items/abfm-u8-session.json

Then open ONLY the printed folder in the verifier, have it write
verdicts.json, and run tools/ingest_verdicts.py on it.
"""
import argparse, datetime, glob, io, json, os, random, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import statute_store  # noqa: E402

VERIFY_ROOT = os.path.join('content', '_verify')      # gitignored
PAGES_ROOT = os.path.join('content', '_pages')
LETTERS = 'ABCDE'

VERDICT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Verifier verdicts",
    "type": "array",
    "items": {
        "type": "object",
        "required": ["packet_id", "my_answer", "working", "entailed_span", "span_page",
                     "untraceable_numbers", "answerable_from_stem", "ambiguous",
                     "copies_source", "notes"],
        "additionalProperties": False,
        "properties": {
            "packet_id": {"type": "string"},
            "my_answer": {"type": "string", "enum": list(LETTERS) + ["NONE"],
                          "description": "Your own answer, worked from the pages. NONE if no option is correct."},
            "working": {"type": "string", "description": "Your computation or reasoning, briefly."},
            "entailed_span": {"type": ["string", "null"],
                              "description": "Verbatim text from a page that supports your answer, or null if none does."},
            "span_page": {"type": ["integer", "null"], "description": "Book page number of that span."},
            "untraceable_numbers": {"type": "array", "items": {"type": "string"},
                                    "description": "Any number in the item that neither the pages nor the item's own given figures account for."},
            "answerable_from_stem": {"type": "boolean"},
            "ambiguous": {"type": "boolean",
                          "description": "True if more than one option could reasonably be defended."},
            "copies_source": {"type": "boolean",
                              "description": "True if the item reproduces the pages' wording, figures or worked example."},
            "notes": {"type": "string"}
        }
    }
}

INSTRUCTIONS = u"""# Verification packet {packet}

You are checking exam items written by someone else. You did not write them
and have no stake in them. An item you cannot confirm will be discarded - that
is the intended outcome, not a failure.

## Material

- `items.json` - the items. Options are in random order.
- `pages/` - textbook pages, named by book page number (p177.jpg is page 177).
- `regulations/` - regulation text as published by the regulator, where present.
- `verdict.schema.json` - the exact shape your answer must take.

Each item's `check_against` says which source governs it. **An item pointing to
`regulations/` must be confirmed from that regulation text alone** - the
regulation is the authority; quote it exactly, and leave span_page null. Items
pointing to `pages/` are finance mathematics: confirm them from the definitions
on those pages.

Use nothing else. Do not search the web or rely on outside knowledge of the
subject: the question is whether THESE pages support each item.

## For each item, in this order

1. Work the question yourself from the pages and the item's given figures.
   Decide your answer before judging the options' wording.
2. Find the text on a page that supports your answer and quote it exactly, with
   its page number. Read formulas and tables as printed: a stacked fraction is a
   division. If no page supports the answer, use null.
3. List any number in the item that neither the pages nor the item's own given
   figures account for.
4. Say whether the item is answerable from its stem alone, whether more than one
   option could be defended, and whether it copies the pages' wording, figures
   or worked examples.

## Output

Write `verdicts.json` in this folder: a JSON array with one object per item,
matching `verdict.schema.json` exactly. JSON only - no commentary outside it.
"""


def item_unit(it):
    m = re.match(r'^[A-Z]+\.[A-D]\.(\d+)', it['syllabus_node'])
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--items', nargs='*', default=None,
                    help='item files (default: every file under content/items)')
    ap.add_argument('--all', action='store_true',
                    help='include items already verified')
    ap.add_argument('--seed', type=int, default=None)
    a = ap.parse_args()

    files = a.items or sorted(glob.glob(os.path.join('content', 'items', '*.json')))
    chosen = []
    for f in files:
        if os.path.basename(f).startswith('_'):
            continue
        for it in json.load(io.open(f, encoding='utf8')):
            v = it.get('verification') or {}
            if a.all or not v.get('second_model_agrees'):
                chosen.append((f, it))
    if not chosen:
        print('nothing to verify')
        return 0

    packet = datetime.datetime.now().strftime('v%Y%m%d-%H%M%S')
    folder = os.path.join(VERIFY_ROOT, packet)
    os.makedirs(os.path.join(folder, 'pages'))
    rng = random.Random(a.seed)

    blind, mapping, units = [], {}, set()
    statute_texts = {}
    for n, (f, it) in enumerate(chosen, 1):
        pid = '%s-%02d' % (packet, n)
        opts = list(it['options'])
        rng.shuffle(opts)
        relabel = {}
        shown = []
        for i, o in enumerate(opts):
            relabel[LETTERS[i]] = o['id']
            shown.append({"id": LETTERS[i], "text": o['text']})
        g = (it.get('grounding') or [{}])[0]
        reg_file = None
        if g.get('kind') == 'statute' and g.get('statute') and g.get('clause'):
            # A statutory item is checked against the REGULATION, never the
            # textbook - so the packet carries the clause as fetched from the
            # issuer, and the verifier is told to use it.
            clauses = statute_store.load_clauses(g['statute']) or {}
            c = clauses.get(g['clause'])
            if c:
                reg_file = '%s_%s.txt' % (g['statute'], g['clause'])
                statute_texts[reg_file] = u'%s\n%s - %s\n\n%s\n' % (
                    g.get('source', ''), g['clause'], c.get('heading', ''), c['text'])
        blind.append({
            "packet_id": pid,
            # Only WHERE to look, never the locator itself: "Regulation 3(4)(b)"
            # names the answer (clause (b) is Category II), and a definition's
            # locator is its formula, which hands over the method.
            "section": (('%s, %s' % (g.get('source', ''), g['clause'])) if reg_file
                        else 'Unit %s' % item_unit(it)),
            "check_against": ("regulations/" + reg_file) if reg_file else "pages/",
            "stem": it['stem'],
            "given": [{"label": x['label'], "value": x['value'], "unit": x.get('unit', '')}
                      for x in it.get('given', [])],
            "options": shown,
        })
        key = next(o['id'] for o in it['options'] if o.get('key'))
        mapping[pid] = {"file": f.replace('\\', '/'), "item_id": it['item_id'],
                        "relabel": relabel, "key": key}
        u = item_unit(it)
        if u and not reg_file:
            units.add(u)

    copied = 0
    for u in sorted(units):
        src = os.path.join(PAGES_ROOT, 'u%02d' % u)
        pages = sorted(glob.glob(os.path.join(src, '*.jpg')))
        if not pages:
            print('WARNING: no page images for unit %d - run tools/pdf_pages.py --unit %d' % (u, u))
        for p in pages:
            shutil.copy(p, os.path.join(folder, 'pages', os.path.basename(p)))
            copied += 1

    def dump(path, obj):
        io.open(path, 'w', encoding='utf8').write(json.dumps(obj, indent=1, ensure_ascii=False))

    if statute_texts:
        os.makedirs(os.path.join(folder, 'regulations'))
        for name, text in statute_texts.items():
            io.open(os.path.join(folder, 'regulations', name), 'w', encoding='utf8').write(text)

    dump(os.path.join(folder, 'items.json'), blind)
    dump(os.path.join(folder, 'verdict.schema.json'), VERDICT_SCHEMA)
    io.open(os.path.join(folder, 'INSTRUCTIONS.md'), 'w', encoding='utf8').write(
        INSTRUCTIONS.format(packet=packet))
    # The answer key lives beside the packet, never inside it.
    dump(os.path.join(VERIFY_ROOT, packet + '.key.json'), mapping)

    print('packet %s' % packet)
    print('  items  %d' % len(blind))
    print('  pages  %d (units %s)' % (copied, ', '.join(str(u) for u in sorted(units)) or '-'))
    print('  regulation texts  %d' % len(statute_texts))
    print('\nOpen ONLY this folder in the verifier:')
    print('  %s' % os.path.abspath(folder))
    print('\nAsk it to follow INSTRUCTIONS.md and write verdicts.json there. Then:')
    print('  python tools/ingest_verdicts.py %s' % packet)
    return 0


if __name__ == '__main__':
    sys.exit(main())
