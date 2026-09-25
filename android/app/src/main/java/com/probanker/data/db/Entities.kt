package com.probanker.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * The on-device content model. Mirrors the JSON schemas in content/schema.
 *
 * (Written without a `/`+`*` glob in this comment on purpose: Kotlin block
 * comments nest, so one inside a KDoc opens a comment that never closes and
 * silently swallows the rest of the file.)
 *
 * Everything a learner meets is here: items, the misconception each distractor
 * encodes, and the authored ladder rungs. Nothing is generated at runtime
 * (BLUEPRINT.md 2.3), so there is no network state to model and no "pending
 * response" anywhere in this schema.
 */

// ---------------------------------------------------------------- content

@Entity(tableName = "concepts")
data class ConceptEntity(
    @PrimaryKey val id: String,
    val title: String,
    /** Prerequisite concept ids, comma-separated. Shallow by design (BLUEPRINT 2.5). */
    val prereqs: String,
    val status: String,
)

@Entity(tableName = "misconceptions")
data class MisconceptionEntity(
    @PrimaryKey val id: String,
    val statement: String,
    val concept: String,
    /** contrast-cases | clause-anchor | boundary-probe | quantity-intuition */
    val remediationStrategy: String,
    val status: String,
    /** null until measured. A guess is never stored here (BLUEPRINT 3.7). */
    val prevalence: Double?,
)

/**
 * One rung of the authored Socratic ladder.
 *
 * `ordinal` is the rung's position: 0 PROBE, 1 NARROW, 2 HINT_L1, 3 HINT_L2,
 * 4 WORKED_EXAMPLE. RESOLVE is not a rung - it is the item's own explanation,
 * and it always fires.
 */
@Entity(
    tableName = "ladder_rungs",
    primaryKeys = ["misconceptionId", "ordinal"],
    foreignKeys = [ForeignKey(
        entity = MisconceptionEntity::class,
        parentColumns = ["id"],
        childColumns = ["misconceptionId"],
        onDelete = ForeignKey.CASCADE,
    )],
)
data class LadderRungEntity(
    val misconceptionId: String,
    val ordinal: Int,
    val text: String,
)

@Entity(
    tableName = "items",
    indices = [Index("concept"), Index("syllabusNode"), Index("state")],
)
data class ItemEntity(
    @PrimaryKey val itemId: String,
    /** IIBF spine - coverage accounting. Never reorganised (BLUEPRINT 2.5). */
    val syllabusNode: String,
    /** Our graph - what the scheduler sequences on. */
    val concept: String,
    val stem: String,
    /** Learner-facing statutory/courseware locator, rendered under the answer. */
    val groundingLocator: String,
    /** Verbatim text of the regulation cited, for statutory items (BLUEPRINT 4.2). */
    val groundingQuote: String? = null,
    /** Authored explanation shown at RESOLVE. Never generated. */
    val resolution: String,
    // 2PL psychometrics; null until calibrated.
    val difficulty: Double?,
    val discrimination: Double?,
    val state: String,
)

@Entity(
    tableName = "item_options",
    primaryKeys = ["itemId", "optionId"],
    foreignKeys = [ForeignKey(
        entity = ItemEntity::class,
        parentColumns = ["itemId"],
        childColumns = ["itemId"],
        onDelete = ForeignKey.CASCADE,
    )],
)
data class ItemOptionEntity(
    val itemId: String,
    val optionId: String,
    val text: String,
    @ColumnInfo(name = "is_key") val isKey: Boolean,
    /** null on the key; required on every distractor (BLUEPRINT 3.1). */
    val misconceptionId: String?,
)

@Entity(tableName = "given_figures", primaryKeys = ["itemId", "label"])
data class GivenFigureEntity(
    val itemId: String,
    val label: String,
    val value: Double,
    val unit: String,
)

// ---------------------------------------------------------------- learner

/**
 * One response. Local-first: this never leaves the device unless the learner
 * opts into sync (BLUEPRINT 9, Privacy).
 */
@Entity(tableName = "attempts", indices = [Index("itemId"), Index("answeredAt")])
data class AttemptEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val itemId: String,
    val chosenOptionId: String,
    val correct: Boolean,
    /** How far down the ladder they went. 0 means they never needed it. */
    val ladderDepth: Int,
    val answeredAt: Long,
    val elapsedMs: Long,
)

/** Ability per concept, 2PL (BLUEPRINT 6). Mastery is theta with a tight enough SE. */
@Entity(tableName = "concept_mastery")
data class ConceptMasteryEntity(
    @PrimaryKey val conceptId: String,
    val theta: Double,
    val standardError: Double,
    val nResponses: Int,
    val updatedAt: Long,
)

/**
 * Per-misconception state, tracked separately from ability: a learner can have
 * adequate theta and still reliably hold one wrong belief (BLUEPRINT 6).
 */
@Entity(tableName = "misconception_state")
data class MisconceptionStateEntity(
    @PrimaryKey val misconceptionId: String,
    /** active | remediated | stale */
    val status: String,
    val consecutiveCorrect: Int,
    val lastSeenAt: Long,
    val firstSeenAt: Long,
)

/** FSRS scheduling state, one row per item (BLUEPRINT 7). */
@Entity(tableName = "review_schedule", indices = [Index("dueAt")])
data class ReviewScheduleEntity(
    @PrimaryKey val itemId: String,
    val stability: Double,
    val difficulty: Double,
    val reps: Int,
    val lapses: Int,
    val lastReviewedAt: Long,
    val dueAt: Long,
)
