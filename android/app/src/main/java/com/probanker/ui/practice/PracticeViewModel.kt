package com.probanker.ui.practice

import androidx.lifecycle.viewModelScope
import com.probanker.core.mvi.MviViewModel
import com.probanker.core.mvi.UiEffect
import com.probanker.core.mvi.UiIntent
import com.probanker.core.mvi.UiState
import com.probanker.data.db.ItemWithParts
import com.probanker.data.repo.PracticeRepository
import com.probanker.domain.model.Advance
import com.probanker.domain.model.LadderState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * The core loop: answer -> (ladder) -> resolve -> next.
 *
 * Note what is absent. There is no loading state for a tutor response, no
 * retry, no offline branch, because nothing here calls anything (BLUEPRINT 2.3).
 * Every rung the learner sees was authored and verified before it shipped.
 */

enum class Phase { Loading, Answering, Ladder, Resolved, SessionDone }

data class PracticeState(
    val phase: Phase = Phase.Loading,
    val queue: List<ItemWithParts> = emptyList(),
    val index: Int = 0,
    val chosenOptionId: String? = null,
    val ladder: LadderState? = null,
    val startedAt: Long = 0L,
    val itemShownAt: Long = 0L,
) : UiState {
    val item: ItemWithParts? get() = queue.getOrNull(index)
    val progress: Pair<Int, Int> get() = (index + 1) to queue.size
    val wasCorrect: Boolean
        get() = item?.options?.firstOrNull { it.optionId == chosenOptionId }?.isKey == true
}

sealed interface PracticeIntent : UiIntent {
    data object Start : PracticeIntent
    data class Choose(val optionId: String) : PracticeIntent
    data object Submit : PracticeIntent
    data class AdvanceLadder(val by: Advance) : PracticeIntent
    data object ShowAnswer : PracticeIntent
    data object Next : PracticeIntent
    data object ReportItem : PracticeIntent
}

sealed interface PracticeEffect : UiEffect {
    data object SessionComplete : PracticeEffect
    data class Reported(val itemId: String) : PracticeEffect
}

@HiltViewModel
class PracticeViewModel @Inject constructor(
    private val repo: PracticeRepository,
) : MviViewModel<PracticeState, PracticeIntent, PracticeEffect>(PracticeState()) {

    override fun onIntent(intent: PracticeIntent) {
        when (intent) {
            PracticeIntent.Start -> start()
            is PracticeIntent.Choose -> setState { copy(chosenOptionId = intent.optionId) }
            PracticeIntent.Submit -> submit()
            is PracticeIntent.AdvanceLadder -> advance(intent.by)
            PracticeIntent.ShowAnswer -> advance(Advance.Requested)
            PracticeIntent.Next -> next()
            PracticeIntent.ReportItem -> report()
        }
    }

    private fun start() = viewModelScope.launch {
        val queue = repo.planSession()
        val now = System.currentTimeMillis()
        setState {
            copy(
                phase = if (queue.isEmpty()) Phase.SessionDone else Phase.Answering,
                queue = queue, index = 0, startedAt = now, itemShownAt = now,
            )
        }
    }

    private fun submit() = viewModelScope.launch {
        val s = current
        val item = s.item ?: return@launch
        val chosen = s.chosenOptionId ?: return@launch
        val option = item.options.firstOrNull { it.optionId == chosen } ?: return@launch

        repo.recordAttempt(
            item = item,
            chosenOptionId = chosen,
            correct = option.isKey,
            ladderDepth = 0,
            elapsedMs = System.currentTimeMillis() - s.itemShownAt,
        )

        if (option.isKey) {
            // Right first time: no ladder to climb, straight to the resolution.
            setState { copy(phase = Phase.Resolved) }
            return@launch
        }

        // Wrong: the distractor names the misconception, so rung selection is
        // a lookup, not a judgement.
        val misconceptionId = option.misconceptionId
        if (misconceptionId == null) {
            setState { copy(phase = Phase.Resolved) }
            return@launch
        }
        val ladder = repo.ladderFor(misconceptionId)
        setState { copy(phase = Phase.Ladder, ladder = ladder) }
    }

    private fun advance(by: Advance) {
        val ladder = current.ladder ?: return
        val next = ladder.advance(by)
        setState {
            copy(
                ladder = next,
                phase = if (next.resolved) Phase.Resolved else Phase.Ladder,
            )
        }
    }

    private fun next() {
        val s = current
        if (s.index + 1 >= s.queue.size) {
            setState { copy(phase = Phase.SessionDone) }
            emit(PracticeEffect.SessionComplete)
            return
        }
        setState {
            copy(
                phase = Phase.Answering,
                index = index + 1,
                chosenOptionId = null,
                ladder = null,
                itemShownAt = System.currentTimeMillis(),
            )
        }
    }

    /**
     * Learner reports are the review queue (BLUEPRINT 3.7, mechanism 4): with
     * no human reviewer upstream, this is how a bad item gets found.
     */
    private fun report() = viewModelScope.launch {
        val id = current.item?.item?.itemId ?: return@launch
        repo.reportItem(id)
        emit(PracticeEffect.Reported(id))
    }
}
