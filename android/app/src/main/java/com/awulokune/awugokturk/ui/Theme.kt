package com.awulokune.awugokturk.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

// ---------------------------------------------------------------------------
// AwuGöktürk — modern AI asistanı görünümü.
// Koyu zemin + turkuaz/mavi vurgular. Logo turuncu-kırmızısı marka rengi olarak
// yalnızca ikon ve marka rozetlerinde kullanılır.
// ---------------------------------------------------------------------------

val MarkaKirmizi = Color(0xFFD94A25)   // kaynak görselden örneklenen arka plan
val Turkuaz = Color(0xFF2DE1C2)
val TurkuazKoyu = Color(0xFF0FB39B)
val Mavi = Color(0xFF4D9CFF)
val MaviKoyu = Color(0xFF2A6FD6)

val ArkaPlanKoyu = Color(0xFF0A1114)
val YuzeyKoyu = Color(0xFF111C21)
val YuzeyVarKoyu = Color(0xFF17272E)
val MetinKoyu = Color(0xFFE8F4F2)
val MetinSolgun = Color(0xFF9DB4B2)
val OutlineKoyu = Color(0xFF27424A)
val KodZemin = Color(0xFF0A1418)

val HataKirmizi = Color(0xFFFF6B6B)
val UyariAmber = Color(0xFFFFC24B)
val Basarili = Color(0xFF57E39B)

/** Kullanıcı mesaj balonu ve marka vurguları için turkuaz→mavi geçiş. */
val DegradeVurgu = Brush.horizontalGradient(listOf(Turkuaz, Mavi))

private val KoyuRenkler = darkColorScheme(
    primary = Turkuaz,
    onPrimary = Color(0xFF04211C),
    primaryContainer = TurkuazKoyu,
    onPrimaryContainer = Color(0xFF04211C),
    secondary = Mavi,
    onSecondary = Color(0xFF04182E),
    secondaryContainer = MaviKoyu,
    onSecondaryContainer = Color(0xFFEAF3FF),
    tertiary = Mavi,
    onTertiary = Color(0xFF04182E),
    background = ArkaPlanKoyu,
    onBackground = MetinKoyu,
    surface = YuzeyKoyu,
    onSurface = MetinKoyu,
    surfaceVariant = YuzeyVarKoyu,
    onSurfaceVariant = MetinSolgun,
    error = HataKirmizi,
    onError = Color(0xFF2A0000),
    outline = OutlineKoyu
)

private val AcikRenkler = lightColorScheme(
    primary = TurkuazKoyu,
    onPrimary = Color.White,
    secondary = MaviKoyu,
    onSecondary = Color.White,
    background = Color(0xFFF2F8F7),
    onBackground = Color(0xFF081114),
    surface = Color.White,
    onSurface = Color(0xFF081114),
    surfaceVariant = Color(0xFFDDECEA),
    onSurfaceVariant = Color(0xFF34504C),
    error = Color(0xFFB3261E)
)

@Composable
fun AwuTheme(koyu: Boolean, content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (koyu) KoyuRenkler else AcikRenkler,
        typography = Typography(),
        content = content
    )
}
