package com.probanker.di

import android.content.Context
import androidx.room.Room
import com.probanker.data.db.ContentDao
import com.probanker.data.db.ProBankerDatabase
import com.probanker.data.db.ProgressDao
import com.probanker.domain.scheduler.Fsrs
import com.probanker.domain.scheduler.SessionPlanner
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun database(@ApplicationContext ctx: Context): ProBankerDatabase =
        Room.databaseBuilder(ctx, ProBankerDatabase::class.java, ProBankerDatabase.NAME)
            .build()

    @Provides
    fun contentDao(db: ProBankerDatabase): ContentDao = db.contentDao()

    @Provides
    fun progressDao(db: ProBankerDatabase): ProgressDao = db.progressDao()

    @Provides
    @Singleton
    fun sessionPlanner(): SessionPlanner = SessionPlanner(sessionSize = 10)

    /**
     * Exam date drives interval compression (BLUEPRINT.md 7). Wired to DataStore
     * once the settings screen exists; null until then, which degrades to plain
     * FSRS rather than to wrong scheduling.
     */
    @Provides
    @Singleton
    fun examDateProvider(): Fsrs.ExamDateProvider = Fsrs.ExamDateProvider { null }

    @Provides
    @Singleton
    fun fsrs(provider: Fsrs.ExamDateProvider): Fsrs = Fsrs(provider)
}
