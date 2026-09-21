package com.probanker.domain

import com.probanker.domain.scheduler.Irt
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * Pin the Kotlin ability model to the Python reference.
 *
 * `tools/simulate.py` is where the scheduler's claims were measured, so it is
 * the reference implementation; this file is what stops the two drifting apart
 * silently. CI regenerates golden_irt.json and fails on any diff, so a change
 * here has to be a deliberate change in both places.
 */
class GoldenVectorTest {

    private fun golden(): JSONObject {
        val stream = javaClass.classLoader?.getResourceAsStream("golden_irt.json")
        assertNotNull("golden_irt.json missing - run tools/simulate.py", stream)
        return JSONObject(stream!!.bufferedReader().use { it.readText() })
    }

    @Test
    fun `ability updates match the python reference`() {
        val seq = golden().getJSONArray("update_sequence")
        var theta = 0.0
        var info = 0.0
        for (i in 0 until seq.length()) {
            val step = seq.getJSONObject(i)
            val (t, n) = Irt.update(
                theta = theta,
                difficulty = step.getDouble("b"),
                discrimination = 1.0,
                correct = step.getBoolean("correct"),
                priorInformation = info,
            )
            theta = t; info = n
            assertEquals(
                "theta diverged at step $i",
                step.getDouble("theta"), theta, 1e-5,
            )
            assertEquals(
                "standard error diverged at step $i",
                step.getDouble("se"), Irt.standardError(info), 1e-5,
            )
        }
    }

    @Test
    fun `target band matches the python reference`() {
        val g = golden()
        val band = g.getJSONObject("target_band_at_zero")
        val kotlinBand = Irt.targetBand(0.0)
        assertEquals(band.getDouble("easy_end"), kotlinBand.start, 1e-5)
        assertEquals(band.getDouble("hard_end"), kotlinBand.endInclusive, 1e-5)

        val p = g.getJSONObject("p_at_band_ends")
        assertEquals(p.getDouble("easy"), Irt.pCorrect(0.0, kotlinBand.start), 1e-5)
        assertEquals(p.getDouble("hard"), Irt.pCorrect(0.0, kotlinBand.endInclusive), 1e-5)
    }
}
