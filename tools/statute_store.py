# -*- coding: utf-8 -*-
"""The statute store: regulations fetched from the issuer, split into clauses.

BLUEPRINT 3.6 / 4.2 / 13. An item may cite a regulation only by quoting it, and
the quote must appear verbatim in the text fetched from the issuer. This tool
fetches, records exactly what was fetched and when, and splits the text into
addressable clauses; tools/validate.py checks every statutory quote against it.

Sources are listed in content/statutes/sources.json. Each fetch writes:

    content/statutes/<id>/meta.json     issuer, title, url, version, sha256, fetched_at
    content/statutes/<id>/clauses.json  [{clause, number, heading, text}]

The downloaded PDF itself is not committed (it is reproducible from url + sha256).

    python tools/statute_store.py fetch sebi-aif-2012
    python tools/statute_store.py fetch companies-act-2013 --file downloaded.pdf
    python tools/statute_store.py show sebi-aif-2012 reg-3

--file is for issuers whose sites refuse automated access (India Code, MCA's
e-book). Download the CURRENT consolidated text in a browser and pass it here;
the registry still records the official URL, and the version is read from the
document itself, so a stale copy is caught rather than silently stored.
"""
import datetime, hashlib, io, json, os, re, sys

ROOT = os.path.join('content', 'statutes')
UA = {'User-Agent': 'Mozilla/5.0 (ProBanker statute store)'}


def sources():
    return json.load(io.open(os.path.join(ROOT, 'sources.json'), encoding='utf8'))


def fetch_pdf(url):
    """Fetch the issuer's file. Regulator sites are uneven about TLS clients:
    SEBI's times out Python's handshake while answering curl, so fall back."""
    import urllib.request, subprocess, tempfile
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except Exception as e:
        print('urllib failed (%s) - retrying with curl' % str(e)[:60])
    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
    subprocess.check_call(['curl', '-sSL', '--max-time', '240', '-A', UA['User-Agent'],
                           '-o', tmp, url])
    data = open(tmp, 'rb').read()
    os.remove(tmp)
    if not data.startswith(b'%PDF'):
        raise SystemExit('issuer did not return a PDF from %s' % url)
    return data


# Amendment footnotes in SEBI's consolidated texts sit at the foot of each page:
# "1 Substituted by the Securities and Exchange Board of India (...) ... w.e.f. ..."
FOOTNOTE = re.compile(
    r'(?m)^\s*\d{1,3}\s*(Substituted|Inserted|Omitted|Deleted|Renumbered|Amended|'
    r'The words|Words|Prior to|Sub-regulation|Clause|Regulation|Proviso|Explanation)\b.*$')
SUPERSCRIPT_REF = re.compile(r'(?<=[a-z,;:\)\.])(\d{1,3})(?=\s|\[|\()')
REG_START = re.compile(r'(?m)^(\d{1,2}[A-Z]{0,2})\.\s+(?=\(1\)|[A-Z\(])')


def clean(text):
    text = text.replace('–', '-').replace('—', '-').replace('’', "'")
    text = text.replace('“', '"').replace('”', '"').replace('�', '-')
    text = FOOTNOTE.sub('', text)
    return text


def body_text(doc):
    """Only the operative text, separated from footnotes by font size.

    SEBI's consolidated texts carry amendment history as footnotes, and those
    footnotes quote the SUPERSEDED wording ("Prior to its substitution, clause
    (aa) read as ..."). Left in, an item could quote repealed text and still
    pass a verbatim check. Matching footnotes by their wording missed their
    continuation lines, so separate by size instead: the body is set larger
    than footnotes, and footnote markers are smaller still.
    """
    import collections
    sizes = collections.Counter()
    for p in doc:
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    if s['text'].strip():
                        sizes[round(s['size'], 1)] += len(s['text'])
    body = sizes.most_common(1)[0][0]
    keep = body - 0.6                      # tolerate rounding, drop smaller type

    lines = []
    for p in doc:
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                t = u''.join(s['text'] for s in l['spans'] if s['size'] >= keep)
                if t.strip():
                    lines.append(t)
    return u'\n'.join(lines)


def split_regulations(text):
    """Split a SEBI-style consolidated regulation into numbered regulations.

    The marginal heading is the non-empty line immediately before the number.
    Only the first occurrence of each number counts, so schedules and forms
    further down cannot overwrite a regulation.
    """
    out, seen = [], set()
    matches = list(REG_START.finditer(text))
    for i, m in enumerate(matches):
        num = m.group(1)
        if num in seen:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end]
        before = text[max(0, m.start() - 200):m.start()].rstrip().split('\n')
        heading = before[-1].strip().rstrip('.') if before else ''
        seen.add(num)
        out.append({
            'clause': 'reg-%s' % num,
            'number': num,
            'heading': heading if len(heading) < 120 else '',
            'text': re.sub(r'[ \t]+', ' ', body).strip(),
        })
    return out


def fetch(sid, local=None):
    src = sources().get(sid)
    if not src:
        raise SystemExit('unknown source %s (see content/statutes/sources.json)' % sid)
    import fitz
    data = open(local, 'rb').read() if local else fetch_pdf(src['url'])
    if not data.startswith(b'%PDF'):
        raise SystemExit('%s is not a PDF' % (local or src['url']))
    digest = hashlib.sha256(data).hexdigest()
    doc = fitz.open(stream=data, filetype='pdf')
    text = clean(body_text(doc))

    # Is this even the instrument claimed? A wrong file must be refused, not
    # stored under another regulation's name: testing the local-file path with
    # SEBI's AIF text once stored it, dated and plausible, as the Companies Act.
    ident = src.get('identify_by')
    if not ident:
        raise SystemExit('%s has no identify_by phrase in sources.json - cannot confirm '
                         'the document is the instrument claimed' % sid)
    head = normalise(text[:6000])
    if normalise(ident) not in head:
        raise SystemExit('%s: document does not identify itself as "%s" - refusing to store it'
                         % (local or src['url'], ident))

    m = re.search(r'Amended up\s*to\s+([A-Z][a-z]+ \d{1,2}, \d{4})', text)
    version = m.group(1) if m else src.get('version')
    if src.get('version') and version != src['version']:
        print('NOTE: issuer text says "%s", registry expected "%s"' % (version, src['version']))

    clauses = split_regulations(text)
    folder = os.path.join(ROOT, sid)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    if local and not m:
        # Nothing in the document states its currency. Refuse rather than
        # store an undated regulation that would look authoritative.
        raise SystemExit('%s does not state which amendment it is current to - '
                         'download the consolidated "as amended" text instead' % local)
    meta = {
        'id': sid, 'issuer': src['issuer'], 'title': src['title'], 'kind': src['kind'],
        'url': src['url'], 'version': version,
        'obtained': 'manual download' if local else 'fetched from issuer', 'sha256': digest, 'pages': doc.page_count,
        'fetched_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        'clauses': len(clauses),
    }
    io.open(os.path.join(folder, 'meta.json'), 'w', encoding='utf8').write(
        json.dumps(meta, indent=2, ensure_ascii=False) + '\n')
    io.open(os.path.join(folder, 'clauses.json'), 'w', encoding='utf8').write(
        json.dumps(clauses, indent=1, ensure_ascii=False) + '\n')
    print('%s: %s, version "%s", %d pages, %d clauses, sha256 %s...'
          % (sid, src['issuer'], version, doc.page_count, len(clauses), digest[:12]))


def load_clauses(sid):
    p = os.path.join(ROOT, sid, 'clauses.json')
    if not os.path.exists(p):
        return None
    return dict((c['clause'], c) for c in json.load(io.open(p, encoding='utf8')))


def normalise(s):
    """Whitespace, dash and quote variation is not a difference in wording."""
    s = s.replace('–', '-').replace('—', '-').replace('’', "'")
    s = s.replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', s).strip().lower()


def quote_ok(sid, clause, quote):
    """True, or the reason the quote cannot be found where it claims to be."""
    clauses = load_clauses(sid)
    if clauses is None:
        return 'statute %s is not in the store - run tools/statute_store.py fetch %s' % (sid, sid)
    c = clauses.get(clause)
    if c is None:
        return 'clause %s not found in %s' % (clause, sid)
    if normalise(quote) not in normalise(c['text']):
        return 'quote is not verbatim in %s %s' % (sid, clause)
    return True


def main(argv):
    if len(argv) >= 2 and argv[0] == 'fetch':
        local = argv[argv.index('--file') + 1] if '--file' in argv else None
        fetch(argv[1], local)
    elif len(argv) >= 3 and argv[0] == 'show':
        c = (load_clauses(argv[1]) or {}).get(argv[2])
        if not c:
            raise SystemExit('not found')
        sys.stdout.buffer.write((u'%s  %s\n\n%s\n' % (c['clause'], c['heading'], c['text'])).encode('utf8'))
    else:
        print(__doc__)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
