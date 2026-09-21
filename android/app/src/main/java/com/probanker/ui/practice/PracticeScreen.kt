package com.probanker.ui.practice

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.probanker.data.db.ItemWithParts
import com.probanker.domain.model.Advance
import com.probanker.domain.model.LadderState
import com.probanker.ui.theme.Reading

/** Minimum touch target. Nothing tappable in this file goes below it. */
private val Touch = 48.dp

@Composable
fun PracticeScreen(
    onFinished: () -> Unit,
    viewModel: PracticeViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.onIntent(PracticeIntent.Start) }
    LaunchedEffect(Unit) {
        viewModel.effects.collect { if (it is PracticeEffect.SessionComplete) onFinished() }
    }

    Surface(color = MaterialTheme.colorScheme.background, modifier = Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
            SessionProgress(state)
            Spacer(Modifier.height(8.dp))
            when (state.phase) {
                Phase.Loading -> Unit
                Phase.Answering -> AnswerPane(state, viewModel)
                Phase.Ladder -> LadderPane(state, viewModel)
                Phase.Resolved -> ResolvePane(state, viewModel)
                Phase.SessionDone -> DonePane(onFinished)
            }
        }
    }
}

@Composable
private fun SessionProgress(state: PracticeState) {
    if (state.queue.isEmpty()) return
    val (n, total) = state.progress
    Row(
        Modifier.fillMaxWidth().padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        LinearProgressIndicator(
            progress = { n.toFloat() / total },
            modifier = Modifier.weight(1f).clip(RoundedCornerShape(2.dp)),
        )
        Spacer(Modifier.width(8.dp))
        Text("$n / $total", style = MaterialTheme.typography.labelMedium)
    }
}

// ------------------------------------------------------------------ answering

@Composable
private fun AnswerPane(state: PracticeState, vm: PracticeViewModel) {
    val item = state.item ?: return
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {

        if (item.given.isNotEmpty()) GivenCard(item)

        Spacer(Modifier.height(16.dp))
        Text(item.item.stem, style = Reading.question)
        Spacer(Modifier.height(16.dp))

        item.options.forEach { option ->
            val selected = state.chosenOptionId == option.optionId
            OptionRow(
                label = option.optionId,
                text = option.text,
                selected = selected,
                onClick = { vm.onIntent(PracticeIntent.Choose(option.optionId)) },
            )
            Spacer(Modifier.height(10.dp))
        }

        Spacer(Modifier.height(8.dp))
        Button(
            onClick = { vm.onIntent(PracticeIntent.Submit) },
            enabled = state.chosenOptionId != null,
            modifier = Modifier.fillMaxWidth().heightIn(min = Touch),
        ) { Text("Check") }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun GivenCard(item: ItemWithParts) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerLowest,
        ),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(
                "GIVEN",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))
            // A grid never survives 390dp, so a table becomes stacked
            // label-value rows (Foundations artboard, transformation 4).
            item.given.forEach { g ->
                Row(
                    Modifier.fillMaxWidth().padding(vertical = 6.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(g.label, style = Reading.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(
                        formatFigure(g.value, g.unit),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }
    }
}

@Composable
private fun OptionRow(label: String, text: String, selected: Boolean, onClick: () -> Unit) {
    val scheme = MaterialTheme.colorScheme
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp)
            .semantics { contentDescription = "Option $label: $text" },
    ) {
        Box(
            Modifier.size(28.dp).clip(RoundedCornerShape(14.dp))
                .background(if (selected) scheme.primary else scheme.surfaceContainerHighest),
            contentAlignment = Alignment.Center,
        ) {
            // The letter carries the identity, not the colour: nothing here
            // depends on hue alone.
            Text(
                label,
                style = MaterialTheme.typography.labelMedium,
                color = if (selected) scheme.onPrimary else scheme.onSurfaceVariant,
            )
        }
        Spacer(Modifier.width(14.dp))
        Text(text, style = MaterialTheme.typography.titleMedium,
            color = scheme.onSurface, modifier = Modifier.weight(1f))
    }
}

// --------------------------------------------------------------------- ladder

@Composable
private fun LadderPane(state: PracticeState, vm: PracticeViewModel) {
    val ladder = state.ladder ?: return
    Column(Modifier.fillMaxSize()) {
        LadderDepth(ladder)
        Spacer(Modifier.height(16.dp))

        Column(Modifier.weight(1f).verticalScroll(rememberScrollState())) {
            ladder.rungs.take(ladder.index).forEach { spent ->
                Text(
                    spent, style = Reading.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 12.dp),
                )
            }
            ladder.current?.let { now ->
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        now, style = Reading.body,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.padding(16.dp),
                    )
                }
            }
        }

        Button(
            onClick = { vm.onIntent(PracticeIntent.AdvanceLadder(Advance.Tapped)) },
            modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp),
        ) { Text(if (ladder.isLast) "Show the answer" else "Next step") }

        Spacer(Modifier.height(10.dp))

        // The escape hatch is live from the first rung and never buried.
        // Withholding the answer was never the point; pacing was.
        OutlinedButton(
            onClick = { vm.onIntent(PracticeIntent.ShowAnswer) },
            modifier = Modifier.fillMaxWidth().heightIn(min = Touch),
        ) { Text("Just show me the answer") }

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun LadderDepth(ladder: LadderState) {
    Row(Modifier.padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        ladder.rungs.indices.forEach { i ->
            Box(
                Modifier.width(20.dp).height(4.dp).clip(RoundedCornerShape(2.dp))
                    .background(
                        if (i <= ladder.index) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.surfaceContainerHighest
                    )
            )
            Spacer(Modifier.width(4.dp))
        }
        Spacer(Modifier.width(6.dp))
        Text(
            "each one more direct",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

// -------------------------------------------------------------------- resolve

@Composable
private fun ResolvePane(state: PracticeState, vm: PracticeViewModel) {
    val item = state.item ?: return
    val key = item.options.firstOrNull { it.isKey }
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState())) {
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                ),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(18.dp)) {
                    Text(
                        key?.text.orEmpty(),
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                    )
                    Spacer(Modifier.height(10.dp))
                    Text(
                        item.item.resolution, style = Reading.body,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                    )
                }
            }
            Spacer(Modifier.height(14.dp))
            Text(
                item.item.groundingLocator,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(10.dp))
            TextButton(
                onClick = { vm.onIntent(PracticeIntent.ReportItem) },
                modifier = Modifier.heightIn(min = Touch),
            ) { Text("This looks wrong") }
        }
        Button(
            onClick = { vm.onIntent(PracticeIntent.Next) },
            modifier = Modifier.fillMaxWidth().heightIn(min = Touch),
        ) { Text("Next question") }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun DonePane(onFinished: () -> Unit) {
    Column(
        Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Session complete", style = MaterialTheme.typography.headlineSmall)
        Spacer(Modifier.height(16.dp))
        Button(onClick = onFinished, modifier = Modifier.heightIn(min = Touch)) { Text("Done") }
    }
}

/** Indian digit grouping, and tabular figures wherever a column of these appears. */
internal fun formatFigure(value: Double, unit: String): String = when (unit) {
    "INR" -> "₹" + groupIndian(value.toLong())
    "fraction" -> "${(value * 100).toInt()}%"
    "percent" -> "${value}%"
    else -> value.toString()
}

internal fun groupIndian(n: Long): String {
    val s = n.toString()
    if (s.length <= 3) return s
    val head = s.dropLast(3)
    val tail = s.takeLast(3)
    val grouped = head.reversed().chunked(2).joinToString(",").reversed()
    return "$grouped,$tail"
}
