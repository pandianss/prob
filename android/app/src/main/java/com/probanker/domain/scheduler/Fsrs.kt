package com.probanker.domain.scheduler

import com.probanker.data.db.ReviewScheduleEntity
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.pow

/**
 * Spaced repetition, FSRS-shaped, with the two banking-specific modifications
 * from BLUEPRINT.md 7.
 *
 * This is a reduced FSRS: stability and difficulty with a power-law forgetting
 * curve, binary grading (we have correct/incorrect, not a four-point self
 * rating). The published weights are fitted on flashcard corpora; ours will
 * differ, so [W] is a starting point to re-fit once there is response data,
 * not a constant to trust.
 */
@Singleton
class Fsrs @Inject constructor(
    private val examDateProvider: ExamDateProvider,
) {

    fun interface ExamDateProvider {
        /** Epoch millis of the learner's exam, or null if they have not set one. */
        fun examAt(): Long?
    }

    private companion object {
        // Initial stability, difficulty, and the growth/decay terms.
        val W = doubleArrayOf(0.40, 1.18, 3.17, 15.69, 7.19, 0.55, 1.20, 0.05, 1.54)
        const val DECAY = -0.5
        const val FACTOR = 19.0 / 81.0
        const val TARGET_RETENTION = 0.90
        const val MIN_INTERVAL_MIN = 10L
        const val MAX_INTERVAL_DAYS = 365L
    }

    fun next(
        prior: ReviewScheduleEntity?,
        itemId: String,
        correct: Boolean,
        now: Long,
    ): ReviewScheduleEntity {
        val elapsedDays = prior
            ?.let { (now - it.lastReviewedAt).toDouble() / TimeUnit.DAYS.toMillis(1) }
            ?.coerceAtLeast(0.0) ?: 0.0

        val difficulty = nextDifficulty(prior?.difficulty, correct)
        val stability = nextStability(prior?.stability, difficulty, elapsedDays, correct)

        val idealDays = intervalFor(stability)
        val dueAt = clampToExam(now, idealDays)

        return ReviewScheduleEntity(
            itemId = itemId,
            stability = stability,
            difficulty = difficulty,
            reps = (prior?.reps ?: 0) + 1,
            lapses = (prior?.lapses ?: 0) + if (correct) 0 else 1,
            lastReviewedAt = now,
            dueAt = dueAt,
        )
    }

    private fun nextDifficulty(prior: Double?, correct: Boolean): Double {
        val d = prior ?: W[4]
        val delta = if (correct) -W[6] else W[6] * 2
        // Mean-reversion keeps difficulty from ratcheting to the ceiling after
        // a run of lapses, which is the classic SM-2 failure.
        val reverted = d + delta + W[7] * (W[4] - d)
        return reverted.coerceIn(1.0, 10.0)
    }

    private fun nextStability(
        prior: Double?,
        difficulty: Double,
        elapsedDays: Double,
        correct: Boolean,
    ): Double {
        if (prior == null) return (if (correct) W[2] else W[0]).coerceAtLeast(0.1)
        val retrievability = retrievability(elapsedDays, prior)
        return if (correct) {
            val gain = exp(W[5]) *
                (11 - difficulty) *
                prior.pow(-W[1]) *
                (exp((1 - retrievability) * W[8]) - 1)
            (prior * (1 + gain)).coerceIn(0.1, MAX_INTERVAL_DAYS.toDouble())
        } else {
            // A lapse shortens stability but does not reset it: the learner has
            // not lost everything they knew, and treating a miss as a reset is
            // what makes SM-2 punish near-misses so heavily.
            (W[3] * difficulty.pow(-W[1]) * prior.pow(W[1]) * exp((1 - retrievability) * W[5]))
                .coerceIn(0.1, prior)
        }
    }

    private fun retrievability(elapsedDays: Double, stability: Double): Double =
        (1 + FACTOR * elapsedDays / stability).pow(DECAY)

    private fun intervalFor(stability: Double): Double =
        (stability / FACTOR) * (TARGET_RETENTION.pow(1 / DECAY) - 1)

    /**
     * Exam-date awareness (BLUEPRINT 7, modification 1) - corrected.
     *
     * The original design compressed intervals as the exam approached. The
     * simulation in tools/simulate.py measured that against an independent
     * forgetting model and it LOSES at every horizon a candidate cares about:
     *
     *     days to exam      plain    compressed
     *      5                0.461      0.345
     *     10                0.449      0.354
     *     21                0.548      0.416
     *     47                0.725      0.597
     *     90                0.760      0.827
     *
     * Compression pulls each review earlier, so less has been forgotten when it
     * happens, so the review consolidates less. With a fixed session budget that
     * trade is simply bad - cramming harder near the exam costs recall on the day.
     *
     * It only pays past ~8 weeks, and there the mechanism is different: plain
     * scheduling lets intervals grow so long that items fall due after the paper.
     * So the rule is not "compress near the exam" but "never let an interval run
     * past the exam", applied smoothly.
     *
     * Hard-clamping to the eve of the exam was worse than either (0.562 at 47
     * days): it piles every item onto one day, which exceeds what a session can
     * hold, and the surplus is never reviewed at all.
     */
    private fun clampToExam(now: Long, idealDays: Double): Long {
        val ideal = now + (idealDays * TimeUnit.DAYS.toMillis(1)).toLong()
        val floor = now + TimeUnit.MINUTES.toMillis(MIN_INTERVAL_MIN)
        val exam = examDateProvider.examAt() ?: return ideal.coerceAtLeast(floor)

        val daysLeft = (exam - now).toDouble() / TimeUnit.DAYS.toMillis(1)
        if (daysLeft <= 0) return ideal.coerceAtLeast(floor)

        // Inside the window: leave the interval alone. Spacing is doing its job
        // and pulling the review forward would only waste it.
        if (idealDays <= daysLeft) return ideal.coerceAtLeast(floor)

        // Would land after the paper: bring it back smoothly, never by clamping
        // everything onto one day.
        val factor = (daysLeft / (daysLeft + idealDays)).coerceIn(0.15, 1.0)
        val adjusted = now + (idealDays * factor * TimeUnit.DAYS.toMillis(1)).toLong()
        return adjusted.coerceAtLeast(floor)
    }

    /** Exposed for the simulation harness; not used by the app. */
    internal fun predictedRecall(stability: Double, elapsedDays: Double): Double =
        retrievability(elapsedDays, stability)

    init {
        require(W.size >= 9) { "FSRS weights truncated" }
        require(ln(TARGET_RETENTION) < 0) { "target retention must be below 1" }
    }
}
