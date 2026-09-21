package com.probanker.core.mvi

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.launch

/** Marker types for unidirectional data flow (BLUEPRINT.md 9: MVI + UDF). */
interface UiState
interface UiIntent
interface UiEffect

/**
 * One state holder per screen. State is a single immutable value; everything
 * the user does arrives as an Intent; one-shot things (navigation, snackbars)
 * leave as Effects so they cannot be replayed on recomposition.
 */
abstract class MviViewModel<S : UiState, I : UiIntent, E : UiEffect>(
    initial: S,
) : ViewModel() {

    private val _state = MutableStateFlow(initial)
    val state: StateFlow<S> = _state.asStateFlow()

    private val _effects = Channel<E>(Channel.BUFFERED)
    val effects = _effects.receiveAsFlow()

    protected val current: S get() = _state.value

    protected fun setState(reduce: S.() -> S) {
        _state.value = _state.value.reduce()
    }

    protected fun emit(effect: E) {
        viewModelScope.launch { _effects.send(effect) }
    }

    abstract fun onIntent(intent: I)
}
