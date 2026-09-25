package com.probanker.data.pack

import android.content.Context
import com.probanker.data.db.ConceptEntity
import com.probanker.data.db.ContentDao
import com.probanker.data.db.GivenFigureEntity
import com.probanker.data.db.ItemEntity
import com.probanker.data.db.ItemOptionEntity
import com.probanker.data.db.LadderRungEntity
import com.probanker.data.db.MisconceptionEntity
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import androidx.room.withTransaction
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Loads the content pack shipped in assets into Room.
 *
 * The pack is the same JSON the authoring pipeline emits and `tools/validate.py`
 * gates, so what runs on the phone is what passed CI - there is no second
 * content format to keep in step.
 */

@Serializable
data class PackConcept(
    val id: String,
    val title: String,
    val prereqs: List<String> = emptyList(),
    val status: String = "proposed",
)

@Serializable
data class PackMisconception(
    val id: String,
    val statement: String,
    val concept: String,
    @SerialName("remediation_strategy") val remediationStrategy: String,
    val status: String = "proposed",
    val prevalence: Double? = null,
    /** Rungs in order. Authored, never generated (BLUEPRINT 2.3). */
    val ladder: List<String> = emptyList(),
    @SerialName("canned_hint_l1") val hintL1: String? = null,
    @SerialName("canned_hint_l2") val hintL2: String? = null,
) {
    /**
     * Until the pipeline emits all four rungs, fall back to the two authored
     * hints. Missing rungs shorten the ladder; they never leave it empty,
     * because RESOLVE still fires either way.
     */
    fun rungs(): List<String> =
        ladder.ifEmpty { listOfNotNull(hintL1, hintL2) }
}

@Serializable
data class PackGiven(val label: String, val value: Double, val unit: String = "")

@Serializable
data class PackOption(
    val id: String,
    val text: String,
    val key: Boolean = false,
    val misconception: String? = null,
)

@Serializable
data class PackItem(
    @SerialName("item_id") val itemId: String,
    @SerialName("syllabus_node") val syllabusNode: String,
    val concept: String,
    val stem: String,
    val given: List<PackGiven> = emptyList(),
    val options: List<PackOption>,
    val resolution: String = "",
    val grounding: List<PackGrounding> = emptyList(),
    val psychometrics: PackPsychometrics? = null,
    val lifecycle: PackLifecycle,
)

@Serializable
data class PackGrounding(
    val source: String = "",
    val locator: String = "",
    /** Verbatim regulation text, for statutory items. */
    val quote: String = "",
)

@Serializable
data class PackPsychometrics(val a: Double? = null, val b: Double? = null)

@Serializable
data class PackLifecycle(val state: String)

@Serializable
data class PackMeta(val version: String)

@Singleton
class ContentPackLoader @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: Context,
    private val db: com.probanker.data.db.ProBankerDatabase,
    private val dao: ContentDao,
) {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }
    private val mutex = kotlinx.coroutines.sync.Mutex()
    private val prefs by lazy {
        context.getSharedPreferences("content_pack", Context.MODE_PRIVATE)
    }

    /**
     * Make sure the database holds the pack that shipped in this APK.
     *
     * Called before every session plan. Cheap when nothing changed (one
     * preference read); when the pack's fingerprint differs, content tables are
     * replaced wholesale in one transaction, so a retired item cannot linger
     * and a failed load cannot leave the database half-empty. Learner history
     * - attempts, mastery, schedules - is never touched.
     */
    suspend fun ensureLoaded() = mutex.withLock {
        val version = json.decodeFromString<PackMeta>(read("content/pack.json")).version
        if (prefs.getString(KEY_VERSION, null) == version) return@withLock
        db.withTransaction {
            dao.clearOptions(); dao.clearGiven(); dao.clearItems()
            dao.clearRungs(); dao.clearMisconceptions(); dao.clearConcepts()
            loadFromAssets()
        }
        prefs.edit().putString(KEY_VERSION, version).apply()
    }

    suspend fun loadFromAssets(
        conceptsPath: String = "content/concepts.json",
        misconceptionsPath: String = "content/misconceptions.json",
        itemsPath: String = "content/items.json",
    ) {
        val concepts = json.decodeFromString<List<PackConcept>>(read(conceptsPath))
        val misconceptions = json.decodeFromString<List<PackMisconception>>(read(misconceptionsPath))
        val items = json.decodeFromString<List<PackItem>>(read(itemsPath))

        dao.insertConcepts(
            concepts.map {
                ConceptEntity(it.id, it.title, it.prereqs.joinToString(","), it.status)
            }
        )
        dao.insertMisconceptions(
            misconceptions.map {
                MisconceptionEntity(
                    id = it.id, statement = it.statement, concept = it.concept,
                    remediationStrategy = it.remediationStrategy,
                    status = it.status, prevalence = it.prevalence,
                )
            }
        )
        dao.insertRungs(
            misconceptions.flatMap { m ->
                m.rungs().mapIndexed { i, text -> LadderRungEntity(m.id, i, text) }
            }
        )

        // Only servable states reach the device. An item pulled to `review`
        // because its source changed should not be sitting in a content pack
        // waiting to be served (BLUEPRINT 3.5).
        val servable = items.filter { it.lifecycle.state in SERVABLE }
        dao.insertItems(
            servable.map {
                ItemEntity(
                    itemId = it.itemId,
                    syllabusNode = it.syllabusNode,
                    concept = it.concept,
                    stem = it.stem,
                    groundingLocator = it.grounding.firstOrNull()
                        ?.let { g -> listOf(g.source, g.locator).filter { s -> s.isNotBlank() }
                            .joinToString(" · ") }.orEmpty(),
                    groundingQuote = it.grounding.firstOrNull()?.quote?.ifBlank { null },
                    resolution = it.resolution,
                    difficulty = it.psychometrics?.b,
                    discrimination = it.psychometrics?.a,
                    state = it.lifecycle.state,
                )
            }
        )
        dao.insertOptions(
            servable.flatMap { item ->
                item.options.map {
                    ItemOptionEntity(item.itemId, it.id, it.text, it.key, it.misconception)
                }
            }
        )
        dao.insertGiven(
            servable.flatMap { item ->
                item.given.map { GivenFigureEntity(item.itemId, it.label, it.value, it.unit) }
            }
        )
    }

    private fun read(path: String): String =
        context.assets.open(path).bufferedReader().use { it.readText() }

    private companion object {
        val SERVABLE = setOf("live", "field")
        const val KEY_VERSION = "pack_version"
    }
}
