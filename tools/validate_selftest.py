# -*- coding: utf-8 -*-
"""Prove the validator still catches what it claims to.

A validator that only ever prints OK is not evidence of anything. This breaks
the content on purpose, once per class of violation, and fails if any mutation
slips through.

With no human reviewer in the pipeline (BLUEPRINT.md 3.7), tools/validate.py is
the review - so its own coverage has to be checked by something.

    python tools/validate_selftest.py
"""
import copy, io, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, 'content', 'items', 'abfm-u8-leverage.json')
MIS = os.path.join(ROOT, 'content', 'misconceptions', 'abfm-leverage.json')


def mutations():
    """name -> (file, mutate). Each must make tools/validate.py exit non-zero."""
    return [
        ('orphan distractor (3.1)', TARGET,
         lambda d: d[0]['options'][1].pop('misconception')),
        ('filler option (3.1)', TARGET,
         lambda d: d[0]['options'][1].__setitem__('text', 'None of the above')),
        ('two keys (3.1)', TARGET,
         lambda d: d[0]['options'][1].__setitem__('key', True)),
        ('no key at all (3.1)', TARGET,
         lambda d: d[0]['options'][0].__setitem__('key', False)),
        ('wrong arithmetic (3.7)', TARGET,
         lambda d: d[0]['verification']['arithmetic'].__setitem__('expected', 0.93)),
        ('key value disagrees with computation (3.7)', TARGET,
         lambda d: d[0]['options'][0].__setitem__('value', 9.99)),
        ('live without second-model agreement (3.7)', TARGET,
         lambda d: d[0]['verification'].__setitem__('second_model_agrees', False)),
        ('live without entailing span (3.7)', TARGET,
         lambda d: d[0]['verification'].__setitem__('entailed_span', '')),
        ('copied too closely from source (3.6)', TARGET,
         lambda d: d[0]['verification'].__setitem__('derivation_overlap', 0.72)),
        ('statutory item with no statute cited (3.6)', TARGET,
         lambda d: d[0].__setitem__('grounding_regime', 'statutory')),
        ('textbook shown as the learner-facing source (3.6)', TARGET,
         lambda d: d[0]['grounding'][0].__setitem__('kind', 'courseware')),
        ('regulation cited with no version or date (13.4)', TARGET,
         lambda d: d[0]['grounding'].append({'kind': 'statute', 'source': 'RBI',
                                              'locator': 'Master Direction'})),
        ('missing concept (2.5)', TARGET,
         lambda d: d[0].pop('concept')),
        ('unknown misconception cited (3.1)', TARGET,
         lambda d: d[0]['options'][1].__setitem__('misconception', 'ABFM.B.LEV.NOPE')),
        ('negative discrimination left live (3.7)', TARGET,
         lambda d: d[0].__setitem__('psychometrics', {'a': -0.4, 'n_responses': 400})),
        ('ladder too short (2.3)', MIS,
         lambda d: d[0].__setitem__('ladder', d[0]['ladder'][:1])),
        ('guessed prevalence on a proposed misconception (3.7)', MIS,
         lambda d: d[0].__setitem__('prevalence', 0.4)),
    ]


def run_validator():
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, 'tools', 'validate.py')],
        capture_output=True, text=True, cwd=ROOT).returncode


def main():
    if run_validator() != 0:
        print(u'content is already invalid - fix that before running the self-test')
        return 2

    originals = {}
    for path in (TARGET, MIS):
        originals[path] = io.open(path, encoding='utf8').read()

    missed = []
    try:
        for name, path, mutate in mutations():
            data = json.loads(originals[path])
            if path == TARGET:
                # Several checks only apply to servable items. Promote the test
                # copy first, so those checks are exercised however the real
                # content is currently staged.
                data[0]['lifecycle']['state'] = 'field'
                data[0]['verification']['second_model_agrees'] = True
            try:
                mutate(data)
            except Exception as e:
                missed.append(u'%s (mutation itself failed: %s)' % (name, e))
                continue
            io.open(path, 'w', encoding='utf8').write(json.dumps(data, indent=2))
            caught = run_validator() != 0
            io.open(path, 'w', encoding='utf8').write(originals[path])
            print(u'  %-52s %s' % (name, u'caught' if caught else u'*** MISSED ***'))
            if not caught:
                missed.append(name)
    finally:
        for path, text in originals.items():
            io.open(path, 'w', encoding='utf8').write(text)

    if run_validator() != 0:
        print(u'\nFAILED to restore content cleanly')
        return 2
    if missed:
        print(u'\nFAILED - %d violation(s) not caught:' % len(missed))
        for m in missed:
            print(u'  %s' % m)
        return 1
    print(u'\nOK - %d violation classes, all caught' % len(mutations()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
