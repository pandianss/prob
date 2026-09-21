package com.probanker.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat
import com.probanker.R

/**
 * Material 3 scheme for ProBanker.
 *
 * Teal primary, deliberately away from the blue every incumbent in this market
 * already owns. Dynamic colour is NOT used: a wrong/right distinction that
 * re-tints itself per handset wallpaper is a correctness signal we no longer
 * control, and the tertiary/error roles below carry meaning.
 */
private val LightScheme = lightColorScheme(
    primary = Color(0xFF00677E),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFB5EBFF),
    onPrimaryContainer = Color(0xFF001F28),
    secondary = Color(0xFF4B6269),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFCEE7EF),
    onSecondaryContainer = Color(0xFF061E25),
    tertiary = Color(0xFF7C5800),
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFFFDEA6),
    onTertiaryContainer = Color(0xFF261900),
    error = Color(0xFFBA1A1A),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF410002),
    background = Color(0xFFF6FAFC),
    onBackground = Color(0xFF171C1F),
    surface = Color(0xFFF6FAFC),
    onSurface = Color(0xFF171C1F),
    surfaceVariant = Color(0xFFDBE4E8),
    onSurfaceVariant = Color(0xFF40484C),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFF0F4F7),
    surfaceContainer = Color(0xFFEAEEF1),
    surfaceContainerHigh = Color(0xFFE4E9EC),
    surfaceContainerHighest = Color(0xFFDEE3E6),
    outline = Color(0xFF70787C),
    outlineVariant = Color(0xFFBFC8CC),
)

private val DarkScheme = darkColorScheme(
    primary = Color(0xFF5AD5F4),
    onPrimary = Color(0xFF003641),
    primaryContainer = Color(0xFF004E5D),
    onPrimaryContainer = Color(0xFFB5EBFF),
    secondary = Color(0xFFB2CBD3),
    onSecondary = Color(0xFF1C343B),
    secondaryContainer = Color(0xFF334A51),
    onSecondaryContainer = Color(0xFFCEE7EF),
    tertiary = Color(0xFFF2BF48),
    onTertiary = Color(0xFF412D00),
    tertiaryContainer = Color(0xFF5E4200),
    onTertiaryContainer = Color(0xFFFFDEA6),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    background = Color(0xFF0E1416),
    onBackground = Color(0xFFDEE3E6),
    surface = Color(0xFF0E1416),
    onSurface = Color(0xFFDEE3E6),
    surfaceVariant = Color(0xFF3F484B),
    onSurfaceVariant = Color(0xFFBFC8CC),
    surfaceContainerLowest = Color(0xFF090F11),
    surfaceContainerLow = Color(0xFF171C1F),
    surfaceContainer = Color(0xFF1B2124),
    surfaceContainerHigh = Color(0xFF252B2E),
    surfaceContainerHighest = Color(0xFF303639),
    outline = Color(0xFF899295),
    outlineVariant = Color(0xFF3F484B),
)

/**
 * Two families, one job each (see the Foundations artboard).
 *
 *  - Plus Jakarta Sans: interface. Not Roboto - every study app on the Play
 *    Store is already Roboto, and the default reads as unconsidered.
 *  - Literata: reading body. Drawn for long-form screen reading, which is what
 *    a commuter does for several hundred words at a stretch.
 *
 * Drop the .ttf files into res/font/ before first build.
 */
private val Jakarta = FontFamily(
    Font(R.font.plus_jakarta_sans_regular, FontWeight.Normal),
    Font(R.font.plus_jakarta_sans_medium, FontWeight.Medium),
    Font(R.font.plus_jakarta_sans_semibold, FontWeight.SemiBold),
    Font(R.font.plus_jakarta_sans_bold, FontWeight.Bold),
)

val Literata = FontFamily(
    Font(R.font.literata_regular, FontWeight.Normal),
    Font(R.font.literata_medium, FontWeight.Medium),
    Font(R.font.literata_semibold, FontWeight.SemiBold),
)

private val BaseTypography = Typography()

private val ProBankerTypography = Typography(
    headlineLarge = BaseTypography.headlineLarge.copy(fontFamily = Jakarta, fontWeight = FontWeight.Bold),
    headlineMedium = BaseTypography.headlineMedium.copy(fontFamily = Jakarta, fontWeight = FontWeight.Bold),
    headlineSmall = BaseTypography.headlineSmall.copy(fontFamily = Jakarta, fontWeight = FontWeight.Bold),
    titleLarge = BaseTypography.titleLarge.copy(fontFamily = Jakarta, fontWeight = FontWeight.SemiBold),
    titleMedium = BaseTypography.titleMedium.copy(fontFamily = Jakarta, fontWeight = FontWeight.SemiBold),
    titleSmall = BaseTypography.titleSmall.copy(fontFamily = Jakarta, fontWeight = FontWeight.Medium),
    bodyLarge = BaseTypography.bodyLarge.copy(fontFamily = Jakarta),
    bodyMedium = BaseTypography.bodyMedium.copy(fontFamily = Jakarta),
    bodySmall = BaseTypography.bodySmall.copy(fontFamily = Jakarta),
    labelLarge = BaseTypography.labelLarge.copy(fontFamily = Jakarta, fontWeight = FontWeight.SemiBold),
    labelMedium = BaseTypography.labelMedium.copy(fontFamily = Jakarta, fontWeight = FontWeight.Medium),
    labelSmall = BaseTypography.labelSmall.copy(fontFamily = Jakarta, fontWeight = FontWeight.Medium),
)

/** Reading styles. Measure caps near 42 characters at 390dp - the phone decides for us. */
object Reading {
    val body = TextStyle(
        fontFamily = Literata, fontSize = 17.sp, lineHeight = 28.sp,
        textAlign = TextAlign.Start,
    )
    val bodySmall = TextStyle(fontFamily = Literata, fontSize = 15.sp, lineHeight = 24.sp)
    val question = TextStyle(fontFamily = Literata, fontSize = 18.sp, lineHeight = 27.sp)
}

@Composable
fun ProBankerTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val scheme = if (darkTheme) DarkScheme else LightScheme
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }
    MaterialTheme(colorScheme = scheme, typography = ProBankerTypography, content = content)
}
