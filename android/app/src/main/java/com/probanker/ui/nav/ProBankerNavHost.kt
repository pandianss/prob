package com.probanker.ui.nav

import androidx.compose.runtime.Composable
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
    NavHost(navController = nav, startDestination = Routes.MAP) {
        composable(Routes.MAP) {
            MapScreen(onPractice = { nav.navigate(Routes.PRACTICE) })
        }
        composable(Routes.PRACTICE) {
            PracticeScreen(onFinished = { nav.popBackStack() })
        }
    }
}
