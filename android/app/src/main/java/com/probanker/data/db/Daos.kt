package com.probanker.data.db

import androidx.room.Dao
import androidx.room.Embedded
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Relation
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

/** An item with everything needed to render and mark it, in one read. */
data class ItemWithParts(
    @Embedded val item: ItemEntity,
    @Relation(parentColumn = "itemId", entityColumn = "itemId")
    val options: List<ItemOptionEntity>,
    @Relation(parentColumn = "itemId", entityColumn = "itemId")
    val given: List<GivenFigureEntity>,
)

@Dao
interface ContentDao {

    @Transaction
    @Query("SELECT * FROM items WHERE itemId = :id")
    suspend fun item(id: String): ItemWithParts?

    /**
     * Candidates the scheduler may choose from.
     *
     * Only `live` and `field` items are ever served; anything in `review` was
     * pulled because its source changed, and a slightly thinner pool beats a
     * confidently wrong statutory threshold (BLUEPRINT 3.5).
     */
    @Transaction
    @Query(
        """
        SELECT i.* FROM items i
        LEFT JOIN review_schedule r ON r.itemId = i.itemId
        WHERE i.state IN ('live', 'field')
          AND (:concepts = '' OR i.concept IN (:conceptList))
          AND (r.dueAt IS NULL OR r.dueAt <= :now)
        """
    )
    suspend fun dueCandidates(
        now: Long,
        concepts: String,
        conceptList: List<String>,
    ): List<ItemWithParts>

    @Query("SELECT * FROM ladder_rungs WHERE misconceptionId = :id ORDER BY ordinal")
    suspend fun ladder(id: String): List<LadderRungEntity>

    @Query("SELECT * FROM misconceptions WHERE id = :id")
    suspend fun misconception(id: String): MisconceptionEntity?

    @Query("SELECT * FROM concepts")
    fun concepts(): Flow<List<ConceptEntity>>

    @Query("SELECT COUNT(*) FROM items WHERE state IN ('live','field')")
    fun servableCount(): Flow<Int>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertConcepts(rows: List<ConceptEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMisconceptions(rows: List<MisconceptionEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRungs(rows: List<LadderRungEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertItems(rows: List<ItemEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOptions(rows: List<ItemOptionEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertGiven(rows: List<GivenFigureEntity>)
}

@Dao
interface ProgressDao {

    @Insert
    suspend fun record(attempt: AttemptEntity): Long

    @Query("SELECT * FROM concept_mastery WHERE conceptId = :id")
    suspend fun mastery(id: String): ConceptMasteryEntity?

    @Query("SELECT * FROM concept_mastery")
    fun allMastery(): Flow<List<ConceptMasteryEntity>>

    @Upsert
    suspend fun upsertMastery(row: ConceptMasteryEntity)

    @Query("SELECT * FROM misconception_state WHERE misconceptionId = :id")
    suspend fun misconceptionState(id: String): MisconceptionStateEntity?

    @Query("SELECT * FROM misconception_state WHERE status = 'active'")
    fun activeMisconceptions(): Flow<List<MisconceptionStateEntity>>

    @Upsert
    suspend fun upsertMisconceptionState(row: MisconceptionStateEntity)

    @Query("SELECT * FROM review_schedule WHERE itemId = :id")
    suspend fun schedule(id: String): ReviewScheduleEntity?

    @Upsert
    suspend fun upsertSchedule(row: ReviewScheduleEntity)

    /**
     * Escalation trigger 4 (BLUEPRINT 2.3): a third encounter with the same
     * misconception inside 14 days means probing has demonstrably failed, so
     * the ladder opens at the worked example instead of the first rung.
     */
    @Query(
        """
        SELECT COUNT(*) FROM attempts a
        JOIN item_options o ON o.itemId = a.itemId AND o.optionId = a.chosenOptionId
        WHERE o.misconceptionId = :misconceptionId AND a.answeredAt >= :since
        """
    )
    suspend fun recentEncounters(misconceptionId: String, since: Long): Int
}
