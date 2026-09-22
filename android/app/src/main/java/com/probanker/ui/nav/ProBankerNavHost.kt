package com.probanker.ui.nav

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.probanker.ui.map.MapScreen
import com.probanker.ui.practice.PracticeScreen

object Routes {
    const val MAP = "map"
    const val PRACTICE = "practice"
}

@Composable
fun ProBankerNavHost() {
    val nav = rememberNavController()

    // The Surface paints edge to edge so the background runs under the system
    // bars, but content is inset by safeDrawing. Without this, enableEdgeToEdge()
    // draws the first line of every screen underneath the status bar - which is
    // exactly what it did on the first device run.
    Surface(
        color = MaterialTheme.colorScheme.background,
        modifier = Modifier.fillMaxSize(),
    ) {
        NavHost(
            navController = nav,
            startDestination = Routes.MAP,
            modifier = Modifier.windowInsetsPadding(WindowInsets.safeDrawing),
        ) {
            composable(Routes.MAP) {
                MapScreen(onPractice = { nav.navigate(Routes.PRACTICE) })
            }
            composable(Routes.PRACTICE) {
                PracticeScreen(onFinished = { nav.popBackStack() })
            }
        }
    }
}
