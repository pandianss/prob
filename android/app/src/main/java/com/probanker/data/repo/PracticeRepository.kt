package com.probanker.data.repo

import com.probanker.data.db.AttemptEntity
import com.probanker.data.db.ConceptMasteryEntity
import com.probanker.data.db.ContentDao
import com.probanker.data.db.ItemWithParts
import com.probanker.data.db.MisconceptionStateEntity
import com.probanker.data.db.ProgressDao
import com.probanker.domain.model.LadderState
import com.probanker.domain.scheduler.Fsrs
import com.probanker.domain.scheduler.Irt
import com.probanker.domain.scheduler.SessionPlanner
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PracticeRepository @Inject constructor(
    private val content: ContentDao,
    private val progress: ProgressDao,
    private val planner: SessionPlanner,
    private val fsrs: Fsrs,
    private val pack: com.probanker.data.pack.ContentPackLoader,
) {

    suspend fun planSession(): List<ItemWithParts> {
        // The pack ships in the APK; nothing reaches the database until this
        // runs. It was never called in the first build, so every session was
        // empty however much content had shipped.
        pack.ensureLoaded()
        val now = System.currentTimeMillis()
        val due = content.dueCandidates(now = now, concepts = "", conceptList = emptyList())
        val candidates = due.map { item ->
            val mastery = progress.mastery(item.item.concept)
            val schedule = progress.schedule(item.item.itemId)
            SessionPlanner.Candidate(
                item = item,
                theta = mastery?.theta ?: 0.0,
                overdueBy = schedule?.let { now - it.dueAt }?.coerceAtLeast(0L) ?: 0L,
            )
        }
        return planner.plan(candidates)
    }

    /**
     * Open the ladder for a misconception.
     *
     * Escalation trigger 4 (BLUEPRINT 2.3): on a third encounter inside 14
     * days, probing has already failed for this learner, so skip to the worked
     * example rather than asking the same opening question a third time.
     */
    suspend fun ladderFor(misconceptionId: String): LadderState {
        val rungs = content.ladder(misconceptionId).sortedBy { it.ordinal }.map { it.text }
        val since = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(14)
        val repeats = progress.recentEncounters(misconceptionId, since)
        return LadderState.start(
            misconceptionId = misconceptionId,
            rungs = rungs,
            repeatEncounter = repeats >= 2,
        )
    }

    suspend fun recordAttempt(
        item: ItemWithParts,
        chosenOptionId: String,
        correct: Boolean,
        ladderDepth: Int,
        elapsedMs: Long,
    ) {
        val now = System.currentTimeMillis()
        progress.record(
            AttemptEntity(
                itemId = item.item.itemId,
                chosenOptionId = chosenOptionId,
                correct = correct,
                ladderDepth = ladderDepth,
                answeredAt = now,
                elapsedMs = elapsedMs,
            )
        )
        updateMastery(item, correct, now)
        updateMisconception(item, chosenOptionId, correct, now)
        progress.upsertSchedule(
            fsrs.next(progress.schedule(item.item.itemId), item.item.itemId, correct, now)
        )
    }

    private suspend fun updateMastery(item: ItemWithParts, correct: Boolean, now: Long) {
        // An uncalibrated field item must not move ability: its difficulty is
        // unknown, so any update would be noise dressed as measurement.
        val difficulty = item.item.difficulty ?: return
        val discrimination = item.item.discrimination ?: 1.0
        val prior = progress.mastery(item.item.concept)
        val priorInfo = Irt.informationFrom(prior?.standardError ?: Double.MAX_VALUE)
        val (theta, info) = Irt.update(
            theta = prior?.theta ?: 0.0,
            difficulty = difficulty,
            discrimination = discrimination,
            correct = correct,
            priorInformation = priorInfo,
        )
        progress.upsertMastery(
            ConceptMasteryEntity(
                conceptId = item.item.concept,
                theta = theta,
                standardError = Irt.standardError(info),
                nResponses = (prior?.nResponses ?: 0) + 1,
                updatedAt = now,
            )
        )
    }

    /**
     * Misconception state is tracked apart from ability, because a learner can
     * have adequate theta and still hold one specific wrong belief.
     *
     * Remediated needs two correct encounters at least seven days apart - one
     * correct answer right after being told the answer proves nothing.
     */
    private suspend fun updateMisconception(
        item: ItemWithParts,
        chosenOptionId: String,
        correct: Boolean,
        now: Long,
    ) {
        val chosen = item.options.firstOrNull { it.optionId == chosenOptionId }
        val touched = item.options.mapNotNull { it.misconceptionId }.distinct()

        if (!correct && chosen?.misconceptionId != null) {
            val prior = progress.misconceptionState(chosen.misconceptionId)
            progress.upsertMisconceptionState(
                MisconceptionStateEntity(
                    misconceptionId = chosen.misconceptionId,
                    status = "active",
                    consecutiveCorrect = 0,
                    lastSeenAt = now,
                    firstSeenAt = prior?.firstSeenAt ?: now,
                )
            )
            return
        }

        if (correct) {
            for (id in touched) {
                val prior = progress.misconceptionState(id) ?: continue
                if (prior.status != "active") continue
                val spacedEnough = now - prior.lastSeenAt >= TimeUnit.DAYS.toMillis(7)
                val streak = if (spacedEnough) prior.consecutiveCorrect + 1 else prior.consecutiveCorrect
                progress.upsertMisconceptionState(
                    prior.copy(
                        status = if (streak >= 2) "remediated" else "active",
                        consecutiveCorrect = streak,
                        lastSeenAt = now,
                    )
                )
            }
        }
    }

    /** Placeholder until the report queue ships; the call site is already correct. */
    suspend fun reportItem(itemId: String) {
        // TODO(P0): persist to a local report table, upload opportunistically.
    }
}
