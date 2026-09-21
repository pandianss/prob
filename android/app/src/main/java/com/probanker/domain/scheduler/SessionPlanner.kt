package com.probanker.domain.scheduler

import com.probanker.data.db.ItemWithParts

/**
 * Picks what the learner sees next (BLUEPRINT.md 6, 7, 2.5).
 *
 * Two rules do most of the work:
 *
 *  1. Serve inside the target success band, not at maximum information.
 *  2. Interleave by CONCEPT, not by syllabus node. One concept can span several
 *     nodes, so varying the node while repeating the concept would look like
 *     interleaving while actually rehearsing the same retrieval (BLUEPRINT 2.5).
 */
class SessionPlanner(
    private val sessionSize: Int = 10,
) {

    data class Candidate(
        val item: ItemWithParts,
        val theta: Double,
        val overdueBy: Long,
    )

    /**
     * @param uncalibratedQuota how many field items to slip in unscored. These
     *   are how psychometrics get measured at all, and how a wrong key is later
     *   caught by negative discrimination with no human involved (BLUEPRINT 3.7).
     */
    fun plan(
        candidates: List<Candidate>,
        uncalibratedQuota: Int = 1,
    ): List<ItemWithParts> {
        if (candidates.isEmpty()) return emptyList()

        val (calibrated, uncalibrated) = candidates.partition { it.item.item.difficulty != null }

        val ranked = calibrated.sortedBy { c ->
            val b = c.item.item.difficulty ?: 0.0
            val a = c.item.item.discrimination ?: 1.0
            val band = Irt.targetBand(c.theta, a)
            // Overdue items earn priority, but never at the cost of dropping a
            // learner far outside the band - a brutal item they were due for is
            // still a brutal item.
            val overdueBonus = (c.overdueBy / (1000.0 * 60 * 60 * 24)).coerceIn(0.0, 3.0) * 0.15
            Irt.distanceFromBand(b, band) - overdueBonus
        }.map { it.item }

        val field = uncalibrated.shuffled().take(uncalibratedQuota).map { it.item }
        return interleave(ranked, field, sessionSize)
    }

    /**
     * Fill the session, never putting two consecutive items from one concept.
     *
     * If the pool cannot satisfy that - a narrow catalogue early on - we take
     * the repeat rather than cut the session short; a shorter session is a
     * worse failure than a weaker interleave.
     */
    internal fun interleave(
        primary: List<ItemWithParts>,
        field: List<ItemWithParts>,
        size: Int,
    ): List<ItemWithParts> {
        val pool = primary.toMutableList()
        val out = mutableListOf<ItemWithParts>()
        val fieldAt = if (field.isEmpty()) -1 else (size / 2)

        while (out.size < size && (pool.isNotEmpty() || out.size == fieldAt)) {
            if (out.size == fieldAt && field.isNotEmpty()) {
                out += field.first()
                continue
            }
            if (pool.isEmpty()) break
            val lastConcept = out.lastOrNull()?.item?.concept
            val pick = pool.indexOfFirst { it.item.concept != lastConcept }
                .takeIf { it >= 0 } ?: 0
            out += pool.removeAt(pick)
        }
        return out
    }
}
