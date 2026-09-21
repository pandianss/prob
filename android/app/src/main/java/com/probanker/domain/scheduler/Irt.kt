package com.probanker.domain.scheduler

import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.sqrt

/**
 * Two-parameter logistic ability model (BLUEPRINT.md 6).
 *
 * "80% correct" is meaningless without knowing the difficulty of what was
 * answered, so mastery is defined on theta with a bounded standard error
 * instead of on a raw score.
 */
object Irt {

    const val MASTERY_SE = 0.35

    /** Serve items here, not at maximum information. See [targetBand]. */
    const val TARGET_P_LOW = 0.70
    const val TARGET_P_HIGH = 0.85

    fun pCorrect(theta: Double, difficulty: Double, discrimination: Double = 1.0): Double =
        1.0 / (1.0 + exp(-discrimination * (theta - difficulty)))

    /** Fisher information for one item at an ability. */
    fun information(theta: Double, difficulty: Double, discrimination: Double = 1.0): Double {
        val p = pCorrect(theta, difficulty, discrimination)
        return discrimination * discrimination * p * (1 - p)
    }

    /**
     * Update ability from one response, Newton-Raphson on the log-likelihood.
     *
     * Kept to a single step per response: this runs on-device after every
     * answer, and a converged re-fit over the full history would be both
     * slower and no more accurate for one additional observation.
     */
    fun update(
        theta: Double,
        difficulty: Double,
        discrimination: Double,
        correct: Boolean,
        priorInformation: Double,
    ): Pair<Double, Double> {
        val p = pCorrect(theta, difficulty, discrimination)
        val score = discrimination * ((if (correct) 1.0 else 0.0) - p)
        val info = information(theta, difficulty, discrimination)
        val totalInfo = priorInformation + info
        // Guard the first few responses, where information is tiny and the
        // step would otherwise throw theta to an implausible value.
        val step = if (totalInfo < 1e-6) 0.0 else (score / totalInfo)
        val next = (theta + step).coerceIn(-4.0, 4.0)
        return next to totalInfo
    }

    fun standardError(totalInformation: Double): Double =
        if (totalInformation <= 1e-9) Double.MAX_VALUE else 1.0 / sqrt(totalInformation)

    fun informationFrom(standardError: Double): Double =
        if (standardError >= Double.MAX_VALUE / 2) 0.0 else 1.0 / (standardError * standardError)

    fun hasMastered(theta: Double, standardError: Double, examThreshold: Double): Boolean =
        theta >= examThreshold && standardError < MASTERY_SE

    /**
     * The difficulty band that lands inside the target success range.
     *
     * Maximum-information selection targets p = 0.5, which is the statistically
     * efficient choice and a miserable experience on a phone at 8am. We give up
     * some information per item to keep the learner in the session.
     */
    fun targetBand(theta: Double, discrimination: Double = 1.0): ClosedFloatingPointRange<Double> {
        fun difficultyFor(p: Double) = theta - ln(p / (1 - p)) / discrimination
        return difficultyFor(TARGET_P_HIGH)..difficultyFor(TARGET_P_LOW)
    }

    fun distanceFromBand(difficulty: Double, band: ClosedFloatingPointRange<Double>): Double = when {
        difficulty < band.start -> band.start - difficulty
        difficulty > band.endInclusive -> difficulty - band.endInclusive
        else -> 0.0
    }

    fun isNear(a: Double, b: Double, eps: Double = 1e-6): Boolean = abs(a - b) < eps
}
