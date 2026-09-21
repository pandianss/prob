# -*- coding: utf-8 -*-
"""Simulate the scheduler against synthetic learners.

BLUEPRINT.md 6 and 7 assert three things that are now committed to Kotlin:

  1. ability converges from adaptive serving,
  2. serving at p = 0.70-0.85 is worth the information it gives up against
     maximum-information selection at p = 0.5,
  3. compressing intervals as an exam approaches improves recall on the day.

None of those had been measured. This measures them, and writes golden vectors
the Kotlin unit tests assert against so the two implementations cannot drift.

What this deliberately does NOT claim: anything about interleaving. The benefit
of interleaving comes from improved discrimination between confusable topics,
and simulating it would mean assuming the effect we want to measure. It stays
an untested design decision until there are real learners (BLUEPRINT 5, E6).

    python tools/simulate.py
"""
import io, json, math, os, random, sys

random.seed(20260921)

# --------------------------------------------------------------------------
# Reference implementation. The Kotlin in android/.../domain/scheduler mirrors
# this; golden_vectors() pins them together.
# --------------------------------------------------------------------------

MASTERY_SE = 0.35
TARGET_P_LOW, TARGET_P_HIGH = 0.70, 0.85


def p_correct(theta, b, a=1.0):
    return 1.0 / (1.0 + math.exp(-a * (theta - b)))


def information(theta, b, a=1.0):
    p = p_correct(theta, b, a)
    return a * a * p * (1 - p)


def update(theta, b, a, correct, prior_info):
    p = p_correct(theta, b, a)
    score = a * ((1.0 if correct else 0.0) - p)
    total = prior_info + information(theta, b, a)
    step = 0.0 if total < 1e-6 else score / total
    return max(-4.0, min(4.0, theta + step)), total


def standard_error(total_info):
    return float('inf') if total_info <= 1e-9 else 1.0 / math.sqrt(total_info)


def target_band(theta, a=1.0):
    def difficulty_for(p):
        return theta - math.log(p / (1 - p)) / a
    return difficulty_for(TARGET_P_HIGH), difficulty_for(TARGET_P_LOW)


# --------------------------------------------------------------------------
# Experiment 1 + 2: convergence, and what the target band costs
# --------------------------------------------------------------------------

def run_learner(true_theta, bank, policy, max_items=50):
    """Serve adaptively under `policy`; return the trace."""
    theta, info, seen = 0.0, 0.0, set()
    errors, experienced = [], []
    items_to_mastery = None

    for n in range(1, max_items + 1):
        if policy == 'band':
            lo, hi = target_band(theta)
            centre = (lo + hi) / 2.0
            pick = min(
                (i for i in range(len(bank)) if i not in seen),
                key=lambda i: abs(bank[i] - centre), default=None)
        else:  # maximum information: hardest choice at p = 0.5
            pick = min(
                (i for i in range(len(bank)) if i not in seen),
                key=lambda i: abs(bank[i] - theta), default=None)
        if pick is None:
            break
        seen.add(pick)
        b = bank[pick]

        p = p_correct(true_theta, b)
        correct = random.random() < p
        experienced.append(1 if correct else 0)

        theta, info = update(theta, b, 1.0, correct, info)
        errors.append(abs(theta - true_theta))
        if items_to_mastery is None and standard_error(info) < MASTERY_SE:
            items_to_mastery = n

    return {
        'final_error': errors[-1] if errors else None,
        'se': standard_error(info),
        'items_to_mastery': items_to_mastery,
        'accuracy': sum(experienced) / float(len(experienced)) if experienced else 0.0,
        'trace': errors,
    }


def experiment_ability(n_learners=400):
    # A bank the learner cannot exhaust: with 60 items and 60 served, every
    # policy degenerates to 'serve everything' and the comparison is empty.
    bank = [(-3.5 + 7.0 * i / 399.0) for i in range(400)]
    out = {}
    for policy in ('band', 'maxinfo'):
        runs = []
        for _ in range(n_learners):
            true_theta = random.gauss(0.0, 1.0)
            runs.append(run_learner(true_theta, bank, policy))
        mastered = [r['items_to_mastery'] for r in runs if r['items_to_mastery']]
        out[policy] = {
            'mean_abs_error': mean(r['final_error'] for r in runs),
            'mean_se': mean(r['se'] for r in runs),
            'mastered_pct': 100.0 * len(mastered) / len(runs),
            'median_items_to_mastery': median(mastered) if mastered else None,
            'experienced_accuracy': mean(r['accuracy'] for r in runs),
        }
    return out


# --------------------------------------------------------------------------
# Experiment 3: exam-date compression
#
# Ground truth is an independent exponential forgetting model, NOT the
# scheduler's own retrievability curve - grading the scheduler with its own
# assumptions would prove nothing.
# --------------------------------------------------------------------------

DAY = 1.0

# How much a maximally-spaced successful review multiplies durability.
SPACING_GAIN = 2.2


def true_recall(half_life_days, elapsed_days):
    return 0.5 ** (elapsed_days / half_life_days)


def simulate_schedule(exam_day, compress, days=120, n_items=40):
    """Return mean true recall on exam day.

    compress: None | 'naive' | 'no_defer' | 'exam_risk'.
    """
    half_life = [1.0] * n_items
    last_seen = [0.0] * n_items
    due = [0.0] * n_items
    reviews = 0

    for day in range(days):
        if day > exam_day:
            break
        if compress == 'exam_risk':
            # Spend the day's slots on whatever is most likely to be
            # forgotten BY EXAM DAY, due or not. This treats the exam as
            # the objective rather than treating intervals as the problem.
            todays = sorted(range(n_items),
                            key=lambda i: true_recall(half_life[i],
                                                      exam_day - last_seen[i]))
        else:
            todays = [i for i in range(n_items) if due[i] <= day]
        for i in todays[:12]:                     # a session holds ~12 items
            reviews += 1
            r = true_recall(half_life[i], day - last_seen[i])
            recalled = random.random() < r
            if recalled:
                # Desirable difficulty: a review earns its keep in proportion
                # to how much had been forgotten. Recalling something you saw
                # an hour ago (r ~ 1) teaches almost nothing; recalling it at
                # the edge of forgetting is what consolidates.
                #
                # Without this term the model rewards constant re-review, and
                # every timing policy becomes unevaluable - which is exactly
                # what the first version of this simulation did.
                half_life[i] *= 1.0 + SPACING_GAIN * (1.0 - r)
            else:
                half_life[i] *= 0.6
            half_life[i] = max(0.5, min(180.0, half_life[i]))
            last_seen[i] = day

            ideal = half_life[i]                  # schedule at ~50% predicted recall
            days_left = max(0.0, exam_day - day)

            if compress == 'naive':
                # What BLUEPRINT 7 actually specified: compress everything as
                # the exam nears.
                if days_left > 0:
                    factor = max(0.15, min(1.0, days_left / (days_left + ideal)))
                    due[i] = min(day + ideal * factor, exam_day - 1)
                else:
                    due[i] = day + ideal
            elif compress == 'no_defer':
                # Only intervene when the item would otherwise fall due AFTER
                # the exam. An item already scheduled inside the window is left
                # alone, because pulling it earlier wastes the spacing effect.
                if day + ideal > exam_day - 1 and days_left > 0:
                    due[i] = exam_day - 1
                else:
                    due[i] = day + ideal
            else:
                due[i] = day + ideal

    recalls = [true_recall(half_life[i], exam_day - last_seen[i]) for i in range(n_items)]
    return mean(recalls), reviews


def experiment_horizon(trials=150):
    """Does compression ever win? Sweep how far away the exam is.

    Spacing needs time to pay off, so the interesting question is not whether
    compression helps on average but whether there is a horizon short enough
    that it does.
    """
    out = {}
    for horizon in (5, 10, 21, 47, 90):
        row = {}
        for label, compress in (('plain', None), ('naive', 'naive'),
                                ('no_defer', 'no_defer')):
            rs = [simulate_schedule(exam_day=horizon, compress=compress)[0]
                  for _ in range(trials)]
            row[label] = mean(rs)
        out[horizon] = row
    return out


def experiment_exam(trials=200):
    out = {}
    for label, compress in (('plain_fsrs', None), ('naive_compression', 'naive'),
                            ('no_defer_past_exam', 'no_defer'),
                            ('exam_risk_priority', 'exam_risk')):
        rs, revs = [], []
        for _ in range(trials):
            r, n = simulate_schedule(exam_day=47, compress=compress)
            rs.append(r); revs.append(n)
        out[label] = {'recall_on_exam_day': mean(rs), 'reviews': mean(revs)}
    return out


# --------------------------------------------------------------------------

def golden_vectors():
    """Pinned values the Kotlin tests assert against, so the two cannot drift."""
    vectors = []
    theta, info = 0.0, 0.0
    for (b, correct) in ((0.0, True), (0.5, True), (1.0, False), (0.8, True), (1.2, True)):
        theta, info = update(theta, b, 1.0, correct, info)
        vectors.append({'b': b, 'correct': correct,
                        'theta': round(theta, 6), 'se': round(standard_error(info), 6)})
    lo, hi = target_band(0.0)
    return {
        'update_sequence': vectors,
        'target_band_at_zero': {'easy_end': round(lo, 6), 'hard_end': round(hi, 6)},
        'p_at_band_ends': {'easy': round(p_correct(0.0, lo), 6),
                           'hard': round(p_correct(0.0, hi), 6)},
    }


def mean(xs):
    xs = list(xs)
    return sum(xs) / float(len(xs)) if xs else 0.0


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def main():
    print(u'=' * 68)
    print(u'ABILITY MODEL (BLUEPRINT 6)')
    print(u'=' * 68)
    ability = experiment_ability()
    print(u'  %-10s %9s %8s %10s %12s %11s' %
          ('policy', 'abs err', 'SE', 'mastered', 'items@mastery', 'accuracy'))
    for policy, r in ability.items():
        print(u'  %-10s %9.3f %8.3f %9.0f%% %12s %10.0f%%' % (
            policy, r['mean_abs_error'], r['mean_se'], r['mastered_pct'],
            r['median_items_to_mastery'], 100 * r['experienced_accuracy']))
    print(u'\n  band    = serve at p 0.70-0.85 (what we shipped)')
    print(u'  maxinfo = serve at p 0.50 (statistically efficient, brutal)')

    print(u'\n' + u'=' * 68)
    print(u'EXAM-DATE COMPRESSION (BLUEPRINT 7)')
    print(u'=' * 68)
    exam = experiment_exam()
    for label, r in exam.items():
        print(u'  %-12s recall on exam day %.3f   reviews %.0f'
              % (label, r['recall_on_exam_day'], r['reviews']))

    print(u'\n' + u'=' * 68)
    print(u'DOES COMPRESSION EVER WIN? (horizon sweep)')
    print(u'=' * 68)
    horizon = experiment_horizon()
    print(u'  %-14s %9s %9s %10s' % ('days to exam', 'plain', 'naive', 'no_defer'))
    for h, row in sorted(horizon.items()):
        best = max(row, key=row.get)
        print(u'  %-14d %9.3f %9.3f %10.3f   best: %s'
              % (h, row['plain'], row['naive'], row['no_defer'], best))

    out = {'ability': ability, 'exam': exam, 'horizon': horizon,
           'golden': golden_vectors()}
    if not os.path.isdir('content/sim'):
        os.makedirs('content/sim')
    io.open('content/sim/results.json', 'w', encoding='utf8').write(
        json.dumps(out, indent=1))
    gp = 'android/app/src/test/resources'
    if not os.path.isdir(gp):
        os.makedirs(gp)
    io.open(os.path.join(gp, 'golden_irt.json'), 'w', encoding='utf8').write(
        json.dumps(out['golden'], indent=1))
    print(u'\n  -> content/sim/results.json')
    print(u'  -> %s/golden_irt.json  (asserted by the Kotlin tests)' % gp)
    return 0


if __name__ == '__main__':
    sys.exit(main())
