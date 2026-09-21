package com.probanker.domain

import com.probanker.domain.model.Advance
import com.probanker.domain.model.LadderState
import com.probanker.domain.scheduler.Irt
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The invariants that would be expensive to discover on a device.
 *
 * These run on the JVM with no Android dependency - the scheduler and the
 * ladder are pure logic by design, which is the other payoff from removing the
 * runtime model (BLUEPRINT.md 2.3).
 */
class LadderAndPlannerTest {

    private val rungs = listOf("probe", "narrow", "hint1", "hint2")

    @Test
    fun `resolve always fires, whatever path the learner takes`() {
        var s = LadderState.start("m1", rungs, repeatEncounter = false)
        repeat(rungs.size) {
            assertTrue("ladder resolved early", !s.resolved)
            s = s.advance(Advance.Tapped)
        }
        assertTrue("a spent ladder must resolve", s.resolved)
    }

    @Test
    fun `show me jumps straight to the answer from the first rung`() {
        val s = LadderState.start("m1", rungs, repeatEncounter = false)
            .advance(Advance.Requested)
        assertTrue(s.resolved)
        assertEquals(Advance.Requested, s.reachedBy)
    }

    @Test
    fun `third encounter in 14 days opens at the worked example`() {
        // Probing has demonstrably failed for this learner on this
        // misconception; asking the same opening question again is the failure
        // mode the trigger exists to prevent.
        val s = LadderState.start("m1", rungs, repeatEncounter = true)
        assertEquals(4, s.index)
        assertTrue(s.resolved || s.current == null)
    }

    @Test
    fun `ladder never de-escalates`() {
        var s = LadderState.start("m1", rungs, repeatEncounter = false)
        s = s.advance().advance().advance()
        val before = s.index
        s = s.advance(Advance.Tapped)
        assertTrue("index must not move backwards", s.index >= before)
    }

    @Test
    fun `target band sits in the intended success range, not at maximum information`() {
        val theta = 0.0
        val band = Irt.targetBand(theta)
        val pAtEasyEnd = Irt.pCorrect(theta, band.start)
        val pAtHardEnd = Irt.pCorrect(theta, band.endInclusive)

        assertEquals(Irt.TARGET_P_HIGH, pAtEasyEnd, 0.01)
        assertEquals(Irt.TARGET_P_LOW, pAtHardEnd, 0.01)
        // Maximum information would put us at 0.5. We are deliberately not there.
        assertTrue("band must be easier than max-information selection", pAtHardEnd > 0.5)
    }

    @Test
    fun `ability converges towards a learner's true level`() {
        var theta = 0.0
        var info = 0.0
        val trueTheta = 1.2
        repeat(40) {
            val difficulty = theta   // adaptive: serve near current estimate
            val correct = Irt.pCorrect(trueTheta, difficulty) > 0.5
            val (t, i) = Irt.update(theta, difficulty, 1.0, correct, info)
            theta = t; info = i
        }
        assertTrue(
            "theta $theta should approach $trueTheta",
            kotlin.math.abs(theta - trueTheta) < 0.75,
        )
        assertTrue("standard error should tighten", Irt.standardError(info) < 1.0)
    }

    @Test
    fun `uncalibrated items cannot claim mastery`() {
        // SE stays wide with no information, so mastery must not trigger on a
        // lucky streak over items whose difficulty we do not know.
        val se = Irt.standardError(0.0)
        assertTrue(!Irt.hasMastered(theta = 3.0, standardError = se, examThreshold = 0.5))
    }
}
