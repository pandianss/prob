package com.probanker.domain.model

/**
 * The authored Socratic ladder (BLUEPRINT.md 2.3).
 *
 * Rungs are written per misconception at content time. No model runs during a
 * learner's session, so this is a pure state machine over content that is
 * already on the device.
 */
enum class Rung(val ordinal0: Int) {
    Probe(0),
    Narrow(1),
    HintL1(2),
    HintL2(3),
    WorkedExample(4);

    companion object {
        fun at(index: Int): Rung = entries.getOrElse(index) { WorkedExample }
        val last: Rung = WorkedExample
    }
}

/** Why the ladder moved. Recorded so abandonment signals stay legible later. */
enum class Advance {
    /** The learner tapped through. */
    Tapped,

    /** "Show me the answer" - live from the first rung, never buried. */
    Requested,

    /** No interaction for 25s on a rung. */
    Dwell,

    /** More than 6 minutes into a session entered during commute hours. */
    SessionLength,

    /** Third-plus encounter with this misconception in 14 days: open at the worked example. */
    RepeatEncounter,
}

data class LadderState(
    val misconceptionId: String,
    val rungs: List<String>,
    val index: Int,
    val reachedBy: Advance = Advance.Tapped,
) {
    val current: String? get() = rungs.getOrNull(index)
    val isLast: Boolean get() = index >= rungs.lastIndex

    /**
     * Advance one rung, or jump if an escalation trigger fired.
     *
     * De-escalation never happens: once past HintL2 we do not return to Probe
     * within a session, because that reads as withholding.
     */
    fun advance(by: Advance = Advance.Tapped): LadderState = when (by) {
        Advance.Requested -> copy(index = rungs.size, reachedBy = by)
        Advance.RepeatEncounter -> copy(index = Rung.WorkedExample.ordinal0, reachedBy = by)
        else -> copy(index = (index + 1).coerceAtMost(rungs.size), reachedBy = by)
    }

    /** True once the ladder is spent and RESOLVE should render. */
    val resolved: Boolean get() = index >= rungs.size

    companion object {
        /**
         * RESOLVE always fires. A learner who closes the app still not knowing
         * the answer is a failure, not a Socratic success - so this is the one
         * transition the state machine cannot skip.
         */
        fun start(misconceptionId: String, rungs: List<String>, repeatEncounter: Boolean) =
            LadderState(
                misconceptionId = misconceptionId,
                rungs = rungs,
                index = if (repeatEncounter) Rung.WorkedExample.ordinal0 else 0,
                reachedBy = if (repeatEncounter) Advance.RepeatEncounter else Advance.Tapped,
            )
    }
}
