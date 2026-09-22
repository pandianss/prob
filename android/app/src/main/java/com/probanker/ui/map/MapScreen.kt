package com.probanker.ui.map

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.probanker.ui.theme.Reading

/**
 * Syllabus map. Speaks the learner's vocabulary - "Module B, Unit 8" - even
 * though the scheduler underneath sequences by concept (BLUEPRINT.md 2.5).
 *
 * The surrounding Surface and window insets belong to the nav host, so this
 * screen only lays out its own content.
 *
 * TODO(P0): drive from ConceptMastery + servable counts; this is the shell.
 */
@Composable
fun MapScreen(onPractice: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            "CAIIB",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            "Advanced Business & Financial Management",
            style = MaterialTheme.typography.headlineSmall,
        )
        Spacer(Modifier.height(20.dp))

        // Coverage is stated honestly. The system does not author what it
        // cannot verify, and the UI says so rather than hiding the gap
        // (BLUEPRINT.md 3.7).
        Card(
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceContainer,
            ),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(Modifier.padding(14.dp)) {
                Text(
                    "Module C is not covered yet",
                    style = MaterialTheme.typography.titleSmall,
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    "Valuation and M&A need source we can cite before we set " +
                        "questions on them. We would rather leave a gap than guess.",
                    style = Reading.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        Spacer(Modifier.height(24.dp))
        Button(
            onClick = onPractice,
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
        ) { Text("Start a session") }
    }
}
