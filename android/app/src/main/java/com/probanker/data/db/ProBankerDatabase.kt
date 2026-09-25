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
    version = 2,
    exportSchema = true,
)
abstract class ProBankerDatabase : RoomDatabase() {
    abstract fun contentDao(): ContentDao
    abstract fun progressDao(): ProgressDao

    companion object {
        const val NAME = "probanker.db"

        /** v2: items carry the verbatim quote of the regulation they cite. */
        val MIGRATION_1_2 = object : androidx.room.migration.Migration(1, 2) {
            override fun migrate(db: androidx.sqlite.db.SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE items ADD COLUMN groundingQuote TEXT")
            }
        }
    }
}
