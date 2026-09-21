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
     * Exam-date awareness (BLUEPRINT 7, modification 1).
     *
     * As the exam approaches the objective stops being long-term retention and
     * becomes recall on one specific day, so intervals compress and nothing is
     * ever scheduled past the paper. Most SRS implementations get this wrong,
     * and it is the single most-requested behaviour in exam prep.
     */
    private fun clampToExam(now: Long, idealDays: Double): Long {
        val ideal = now + (idealDays * TimeUnit.DAYS.toMillis(1)).toLong()
        val floor = now + TimeUnit.MINUTES.toMillis(MIN_INTERVAL_MIN)
        val exam = examDateProvider.examAt() ?: return ideal.coerceAtLeast(floor)

        val daysLeft = (exam - now).toDouble() / TimeUnit.DAYS.toMillis(1)
        if (daysLeft <= 0) return ideal.coerceAtLeast(floor)

        // Compress smoothly rather than only clipping at the boundary: an item
        // due the day before the exam is worth less than one seen twice in the
        // final week.
        val compression = (daysLeft / (daysLeft + idealDays)).coerceIn(0.15, 1.0)
        val compressed = now + (idealDays * compression * TimeUnit.DAYS.toMillis(1)).toLong()
        val latest = exam - TimeUnit.DAYS.toMillis(1)
        return compressed.coerceAtLeast(floor).coerceAtMost(maxOf(latest, floor))
    }

    /** Exposed for the simulation harness; not used by the app. */
    internal fun predictedRecall(stability: Double, elapsedDays: Double): Double =
        retrievability(elapsedDays, stability)

    init {
        require(W.size >= 9) { "FSRS weights truncated" }
        require(ln(TARGET_RETENTION) < 0) { "target retention must be below 1" }
    }
}
