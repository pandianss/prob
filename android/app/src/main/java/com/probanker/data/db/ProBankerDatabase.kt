package com.probanker.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        ConceptEntity::class,
        MisconceptionEntity::class,
        LadderRungEntity::class,
        ItemEntity::class,
        ItemOptionEntity::class,
        GivenFigureEntity::class,
        AttemptEntity::class,
        ConceptMasteryEntity::class,
        MisconceptionStateEntity::class,
        ReviewScheduleEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class ProBankerDatabase : RoomDatabase() {
    abstract fun contentDao(): ContentDao
    abstract fun progressDao(): ProgressDao

    companion object {
        const val NAME = "probanker.db"
    }
}
