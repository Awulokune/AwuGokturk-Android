package com.awulokune.awugokturk.ui

import android.content.Context
import android.content.Intent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.awulokune.awugokturk.ChatMessage
import com.awulokune.awugokturk.GuardFinding
import com.awulokune.awugokturk.R
import kotlinx.coroutines.delay
import kotlin.math.abs

// ---------------------------------------------------------------------------
// Marka görselleri (kaynak görselden üretildi: tools/make_icons.py)
// ---------------------------------------------------------------------------

/** Uygulama logosu (yuvarlatılmış kare karo). */
@Composable
fun AwuLogo(size: Dp, modifier: Modifier = Modifier) {
    Image(
        painter = painterResource(R.drawable.ic_awu_logo),
        contentDescription = "AwuGöktürk",
        modifier = modifier.size(size).clip(RoundedCornerShape(size * 0.26f))
    )
}

/** Asistan avatarı (yuvarlak logo). */
@Composable
fun AwuAvatar(size: Dp, modifier: Modifier = Modifier) {
    Image(
        painter = painterResource(R.drawable.ic_awu_avatar),
        contentDescription = null,
        modifier = modifier.size(size).clip(CircleShape)
    )
}

// ---------------------------------------------------------------------------
// Küçük yapı taşları
// ---------------------------------------------------------------------------

@Composable
fun StatusChip(text: String, color: Color = MaterialTheme.colorScheme.primary) {
    Surface(color = color.copy(alpha = 0.15f), shape = RoundedCornerShape(50)) {
        Text(
            text,
            color = color,
            style = MaterialTheme.typography.labelSmall,
            maxLines = 1,
            softWrap = false,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
        )
    }
}

@Composable
fun SectionCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(Modifier.fillMaxWidth().padding(vertical = 5.dp)) {
        Column(Modifier.padding(14.dp)) {
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(Modifier.height(8.dp))
            content()
        }
    }
}

@Composable
fun BulletList(items: List<String>) {
    items.forEach {
        Text(
            "• $it",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(vertical = 1.dp)
        )
    }
}

@Composable
fun KeyVal(k: String, v: String) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 3.dp),
        verticalAlignment = Alignment.Top
    ) {
        Text(
            k,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.width(12.dp))
        Text(
            v,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Medium,
            textAlign = TextAlign.End,
            modifier = Modifier.weight(1f)
        )
    }
}

/** Uzun değerler için: etiket üstte, değer altta (satır kaybı olmadan). */
@Composable
fun KeyValBlock(k: String, v: String) {
    Column(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
        Text(
            k,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(2.dp))
        Text(v, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
    }
}

/** Boş sohbette gösterilen, tıklanınca gönderilen örnek istem. */
@Composable
fun ExampleChip(text: String, onClick: () -> Unit) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant,
        contentColor = MaterialTheme.colorScheme.onSurface,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)
    ) {
        Row(
            Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.AutoMirrored.Filled.ArrowForward,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            Spacer(Modifier.width(10.dp))
            Text(text, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

/** Yazıyor göstergesi: üç nokta. */
@Composable
fun TypingDots(color: Color = MaterialTheme.colorScheme.primary) {
    val tr = rememberInfiniteTransition(label = "yaziyor")
    val p by tr.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1000, easing = LinearEasing), RepeatMode.Restart),
        label = "faz"
    )
    Row(verticalAlignment = Alignment.CenterVertically) {
        for (i in 0 until 3) {
            val phase = (p + i * 0.22f) % 1f
            val alpha = 0.22f + 0.78f * (1f - abs(phase - 0.5f) * 2f)
            Box(
                Modifier
                    .padding(horizontal = 2.dp)
                    .size(6.dp)
                    .clip(CircleShape)
                    .background(color.copy(alpha = alpha))
            )
        }
    }
}

@Composable
fun ErrorBanner(message: String) {
    Surface(
        color = MaterialTheme.colorScheme.error.copy(alpha = 0.14f),
        shape = RoundedCornerShape(0.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            "Hata: $message",
            color = MaterialTheme.colorScheme.error,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
        )
    }
}

// ---------------------------------------------------------------------------
// Kod bloğu + AwuGuard
// ---------------------------------------------------------------------------

/** Kopyalanabilir/paylaşılabilir, sözdizimi vurgulu kod kartı. */
@Composable
fun CodeCard(
    code: String,
    board: String?,
    onShare: (() -> Unit)? = null
) {
    val clipboard = LocalClipboardManager.current
    var copied by remember { mutableStateOf(false) }
    LaunchedEffect(copied) {
        if (copied) {
            delay(1600)
            copied = false
        }
    }
    val shape = RoundedCornerShape(14.dp)
    Column(
        Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(1.dp, MaterialTheme.colorScheme.outline, shape)
    ) {
        Row(
            Modifier.fillMaxWidth().padding(start = 12.dp, end = 4.dp, top = 2.dp, bottom = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    board ?: "Arduino",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    "derleme/donanım testi: yapılmadı",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            TextButton(onClick = {
                clipboard.setText(AnnotatedString(code))
                copied = true
            }) {
                if (copied) {
                    Icon(
                        Icons.Filled.Check,
                        contentDescription = null,
                        modifier = Modifier.size(15.dp)
                    )
                } else {
                    Icon(
                        painterResource(R.drawable.ic_copy),
                        contentDescription = null,
                        modifier = Modifier.size(15.dp)
                    )
                }
                Spacer(Modifier.width(5.dp))
                Text(if (copied) "Kopyalandı" else "Kopyala", style = MaterialTheme.typography.labelMedium)
            }
            if (onShare != null) {
                IconButton(onClick = onShare, modifier = Modifier.size(38.dp)) {
                    Icon(
                        Icons.Filled.Share,
                        contentDescription = "Paylaş",
                        modifier = Modifier.size(17.dp),
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.outline)
        Box(
            Modifier
                .fillMaxWidth()
                .background(KodZemin)
                .horizontalScroll(rememberScrollState())
        ) {
            Text(
                highlightCpp(code),
                fontFamily = FontFamily.Monospace,
                style = MaterialTheme.typography.bodySmall.copy(lineHeight = 18.sp),
                modifier = Modifier.padding(12.dp)
            )
        }
    }
}

/**
 * AwuGuard durumu: kompakt etiket + açılabilir ayrıntı.
 * "Belirgin hata yok" sonucu, kodun doğru olduğu anlamına GELMEZ; bu açıkça yazılır.
 */
@Composable
fun GuardAndDetails(m: ChatMessage) {
    var open by remember { mutableStateOf(false) }
    val hasError = m.guard.any { it.level == "error" }
    val hasWarn = m.guard.any { it.level == "warning" }
    val label: String
    val color: Color
    when {
        hasError -> {
            label = "AwuGuard: hata buldu"
            color = MaterialTheme.colorScheme.error
        }
        hasWarn -> {
            label = "AwuGuard: uyarı var"
            color = UyariAmber
        }
        else -> {
            label = "AwuGuard: belirgin hata yok"
            color = Basarili
        }
    }
    Column {
        Row(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(10.dp))
                .clickable { open = !open }
                .padding(vertical = 7.dp, horizontal = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(Modifier.size(7.dp).clip(CircleShape).background(color))
            Spacer(Modifier.width(8.dp))
            Text(label, style = MaterialTheme.typography.labelMedium, color = color)
            Spacer(Modifier.weight(1f))
            Text(
                "ayrıntı",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Icon(
                if (open) Icons.Filled.KeyboardArrowUp else Icons.Filled.KeyboardArrowDown,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        AnimatedVisibility(visible = open) {
            Column(Modifier.padding(start = 15.dp, end = 2.dp, bottom = 4.dp)) {
                if (m.guard.isEmpty()) {
                    Text(
                        "• Kontrol edilecek belirgin bir sorun bulunamadı.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    m.guard.forEach { f ->
                        val renk = when (f.level) {
                            "error" -> MaterialTheme.colorScheme.error
                            "warning" -> UyariAmber
                            else -> MaterialTheme.colorScheme.primary
                        }
                        val etiket = when (f.level) {
                            "error" -> "[HATA]"
                            "warning" -> "[UYARI]"
                            else -> "[BİLGİ]"
                        }
                        Row(Modifier.padding(vertical = 1.dp)) {
                            Text(etiket + " ", color = renk, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                            Text(f.message, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                Spacer(Modifier.height(5.dp))
                Text(
                    "• Derleme: " + when {
                        !m.buildRan -> "yapılmadı (cihazda derleyici yok)"
                        m.buildOk -> "host sözdizimi denetimi başarılı"
                        else -> "başarısız"
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    "• Fiziksel donanım testi: yapılmadı",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    "Güvenlik kontrolünden geçmek, kodun doğru olduğunu KANITLAMAZ.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

/** Asistan yanıtının gövdesi: metin + sorular + kod + AwuGuard. */
@Composable
fun AgentBlock(m: ChatMessage) {
    val context = LocalContext.current
    if (m.text.isNotBlank()) {
        Text(m.text, style = MaterialTheme.typography.bodyMedium)
    }
    if (m.questions.isNotEmpty()) {
        Spacer(Modifier.height(6.dp))
        m.questions.forEach {
            Row(Modifier.padding(vertical = 1.dp)) {
                Text("• ", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                Text(it, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
    if (m.code != null) {
        Spacer(Modifier.height(10.dp))
        CodeCard(m.code, m.board, onShare = { shareText(context, m.code) })
    }
    if (m.code != null || m.guard.isNotEmpty() || m.buildRan) {
        Spacer(Modifier.height(4.dp))
        GuardAndDetails(m)
    }
}

// ---------------------------------------------------------------------------
// Yardımcılar
// ---------------------------------------------------------------------------

fun shareText(context: Context, code: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, code)
    }
    context.startActivity(Intent.createChooser(intent, "Kodu paylaş"))
}

fun zaman(ts: Long): String {
    if (ts <= 0L) return ""
    val dk = (System.currentTimeMillis() - ts) / 60000L
    return when {
        dk < 1 -> "az önce"
        dk < 60 -> "$dk dk önce"
        dk < 60 * 24 -> "${dk / 60} sa önce"
        dk < 60 * 24 * 7 -> "${dk / (60 * 24)} gün önce"
        else -> java.text.SimpleDateFormat("d MMM yyyy", java.util.Locale("tr", "TR"))
            .format(java.util.Date(ts))
    }
}

/** Eski çağrılar için korunan basit kod bloğu. */
@Composable
fun CodeBlock(code: String) {
    CodeCard(code, null, onShare = null)
}

/** Eski çağrılar için korunan düz liste. */
@Composable
fun GuardList(findings: List<GuardFinding>) {
    if (findings.isEmpty()) {
        Text(
            "AwuGuard: belirgin hata bulunmadı (kapsam sınırlıdır; bu, kodun doğru olduğunu KANITLAMAZ).",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        return
    }
    findings.forEach { f ->
        val renk = when (f.level) {
            "error" -> MaterialTheme.colorScheme.error
            "warning" -> UyariAmber
            else -> MaterialTheme.colorScheme.primary
        }
        val etiket = when (f.level) {
            "error" -> "[HATA]"
            "warning" -> "[UYARI]"
            else -> "[BİLGİ]"
        }
        Row(Modifier.padding(vertical = 2.dp)) {
            Text("$etiket ", color = renk, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
            Text(f.message, style = MaterialTheme.typography.bodySmall)
        }
    }
}
