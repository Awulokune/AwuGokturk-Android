package com.awulokune.awugokturk.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.awulokune.awugokturk.AppState
import com.awulokune.awugokturk.AwuViewModel
import com.awulokune.awugokturk.R
import com.awulokune.awugokturk.UpdateInfo
import com.awulokune.awugokturk.UpdateProgress

/**
 * "Model Güncellemeleri" ekranı.
 *
 * Model güncellemesi UYGULAMA güncellemesinden bağımsızdır. Ağ yalnızca
 * kullanıcı isteğiyle (kontrol / indir) kullanılır; indirme ve etkinleştirme
 * her zaman açık onay gerektirir. Yayımlanmış bir sürüm yoksa bu dürüstçe yazılır.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ModelUpdateScreen(state: AppState, vm: AwuViewModel) {
    val u = state.update

    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            navigationIcon = {
                IconButton(onClick = { vm.closeModelUpdates() }) {
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Geri",
                        tint = MaterialTheme.colorScheme.onSurface
                    )
                }
            },
            title = {
                Column {
                    Text(
                        "Model Güncellemeleri",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        "Uygulama sürümünden bağımsız",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface,
                titleContentColor = MaterialTheme.colorScheme.onSurface
            )
        )

        Column(
            Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            InstalledCard(state, u)
            UpdateCard(u, vm)
            ProgressCard(u.progress, vm)
            ResultCard(u.progress)
            RollbackCard(u, vm)
            AutoCheckCard(u, vm)
            SecurityCard()

            Spacer(Modifier.height(10.dp))
            Text(
                "${state.appName} ${state.version} — NO SAY CAVAS",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
            Spacer(Modifier.height(14.dp))
        }
    }
}

// ---------------------------------------------------------------------------

@Composable
private fun InstalledCard(state: AppState, u: UpdateInfo) {
    SectionCard("Yüklü Model") {
        KeyVal("Sürüm", u.installedVersion.ifEmpty { state.version })
        KeyVal("Kaynak", u.sourceLabel)
        if (u.hasRevision) {
            KeyVal("Uygulamayla gelen", u.bundledVersion)
        }
        KeyVal("Model", state.modelName)
        KeyVal(
            "5K sınıflandırıcı",
            if (state.classifierAvailable) "yüklü (${state.classifierParams} parametre)"
            else "yüklü değil"
        )
        KeyVal("Durum", state.modelStatus)
    }
}

@Composable
private fun UpdateCard(u: UpdateInfo, vm: AwuViewModel) {
    val busy = u.progress.busy
    SectionCard("Sunucudaki Sürüm") {
        KeyVal(
            "Son kontrol",
            if (u.lastCheckAt > 0L) zaman(u.lastCheckAt) else "hiç yapılmadı"
        )
        KeyVal("En son uyumlu sürüm", u.latestVersion.ifEmpty { "—" })

        if (u.error != null) {
            Spacer(Modifier.height(8.dp))
            Note(u.error, MaterialTheme.colorScheme.error)
        } else if (u.message.isNotEmpty()) {
            Spacer(Modifier.height(8.dp))
            Note(
                u.message,
                if (u.updateAvailable) MaterialTheme.colorScheme.primary else Basarili
            )
        } else if (u.checked && u.latestVersion.isEmpty()) {
            Spacer(Modifier.height(8.dp))
            Note(
                "Bu depoda yayımlanmış bir model sürümü yok. Uygulamayla gelen model " +
                    "kullanılmaya devam ediyor.",
                MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedButton(
                onClick = { vm.checkForUpdates(force = true) },
                enabled = !u.checking && !busy
            ) {
                if (u.checking) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(15.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.primary
                    )
                } else {
                    Icon(Icons.Filled.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                }
                Spacer(Modifier.width(7.dp))
                Text(if (u.checking) "Kontrol ediliyor…" else "Güncellemeleri kontrol et")
            }
        }

        if (u.updateAvailable) {
            Spacer(Modifier.height(12.dp))
            Surface(
                color = MaterialTheme.colorScheme.primary.copy(alpha = 0.10f),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            "Yeni sürüm: ${u.latestVersion}",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                    if (u.releaseTag.isNotEmpty()) {
                        Text(
                            "Etiket: ${u.releaseTag}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Spacer(Modifier.height(6.dp))
                    KeyVal("Boyut", u.sizeText.ifEmpty { "—" })
                    KeyVal("En az uygulama", u.minAppVersion.ifEmpty { "—" })
                    if (u.tokenizerVersion.isNotEmpty()) KeyVal("Tokenizer", u.tokenizerVersion)
                    if (u.architecture.isNotEmpty()) KeyVal("Mimari", u.architecture)

                    if (u.releaseNotes.isNotEmpty()) {
                        Spacer(Modifier.height(8.dp))
                        ReleaseNotes(u.releaseNotes)
                    }

                    Spacer(Modifier.height(10.dp))
                    Button(
                        onClick = { vm.startModelUpdate() },
                        enabled = !busy && !u.checking,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(
                            painterResource(R.drawable.ic_download),
                            contentDescription = null,
                            modifier = Modifier.size(17.dp)
                        )
                        Spacer(Modifier.width(7.dp))
                        Text("İndir ve yükselt")
                    }
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "İndirme yalnızca bu düğmeye bastığınızda başlar ve yalnızca " +
                            "github.com/Awulokune/AwuGokturk-Android üzerinden, HTTPS ile yapılır.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@Composable
private fun ReleaseNotes(notes: String) {
    var expanded by remember { mutableStateOf(false) }
    Column {
        Text(
            "Sürüm notları",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(2.dp))
        Text(
            notes,
            style = MaterialTheme.typography.bodySmall,
            maxLines = if (expanded) Int.MAX_VALUE else 4
        )
        if (notes.length > 120) {
            TextButton(onClick = { expanded = !expanded }, contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)) {
                Text(
                    if (expanded) "Daralt" else "Tamamını göster",
                    style = MaterialTheme.typography.labelMedium
                )
            }
        }
    }
}

@Composable
private fun ProgressCard(p: UpdateProgress, vm: AwuViewModel) {
    if (!p.busy) return
    SectionCard("İşlem sürüyor") {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                p.stageLabel,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium
            )
            Spacer(Modifier.weight(1f))
            if (p.percent >= 0) {
                Text(
                    "%${p.percent}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )
            }
        }
        Spacer(Modifier.height(8.dp))
        if (p.percent >= 0) {
            LinearProgressIndicator(
                progress = { p.percent.coerceIn(0, 100) / 100f },
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(6.dp))
            )
        } else {
            LinearProgressIndicator(
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(6.dp))
            )
        }
        Spacer(Modifier.height(8.dp))
        if (p.total > 0) {
            Text(
                "İndirilen: ${p.processedText} / ${p.totalText}" +
                    if (p.remainingText.isNotEmpty()) "  ·  Kalan: ${p.remainingText}" else "",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        if (p.message.isNotEmpty()) {
            Spacer(Modifier.height(4.dp))
            Text(
                p.message,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(Modifier.height(10.dp))
        OutlinedButton(onClick = { vm.cancelModelUpdate() }) {
            Text("İndirmeyi iptal et")
        }
    }
}

@Composable
private fun ResultCard(p: UpdateProgress) {
    if (!p.terminal) return
    val color: Color
    val title: String
    when {
        p.done -> {
            color = Basarili
            title = "Güncelleme tamamlandı"
        }
        p.failed -> {
            color = MaterialTheme.colorScheme.error
            title = if (p.rolledBack) "Güncelleme geri alındı" else "Güncelleme başarısız"
        }
        else -> {
            color = UyariAmber
            title = "İptal edildi"
        }
    }
    SectionCard("Sonuç") {
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusDot(color)
            Spacer(Modifier.width(8.dp))
            Text(title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, color = color)
        }
        if (p.message.isNotEmpty()) {
            Spacer(Modifier.height(6.dp))
            Text(p.message, style = MaterialTheme.typography.bodySmall)
        }
        if (p.error.isNotEmpty() && p.error != p.message) {
            Spacer(Modifier.height(4.dp))
            Text(p.error, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (p.rolledBack) {
            Spacer(Modifier.height(6.dp))
            Note(
                "Yeni model yüklenemedi; doğrulama tamamlanmadığı için önceki çalışan " +
                    "model yeniden etkinleştirildi.",
                MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        if (p.done) {
            Spacer(Modifier.height(6.dp))
            Note(
                "Etkinleştirme öncesi model doğrulandı (boyut, SHA-256, yapı ve gerçek " +
                    "yükleme denemesi). Önceki model yedekte tutulur.",
                MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun RollbackCard(u: UpdateInfo, vm: AwuViewModel) {
    SectionCard("Önceki Modele Dön") {
        if (u.canRollback) {
            Text(
                "Yedekteki sürüm: ${u.backupVersion.ifEmpty { "—" }}",
                style = MaterialTheme.typography.bodySmall
            )
        } else {
            Text(
                "Bu cihazda indirilmiş bir güncelleme yok; geri dönülecek yedek bulunmuyor.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(Modifier.height(10.dp))
        OutlinedButton(
            onClick = { vm.rollbackModel() },
            enabled = u.canRollback && !u.progress.busy
        ) {
            Icon(
                painterResource(R.drawable.ic_history),
                contentDescription = null,
                modifier = Modifier.size(16.dp)
            )
            Spacer(Modifier.width(7.dp))
            Text("Önceki modele dön")
        }
    }
}

@Composable
private fun AutoCheckCard(u: UpdateInfo, vm: AwuViewModel) {
    SectionCard("Otomatik Kontrol") {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Güncellemeleri otomatik kontrol et", style = MaterialTheme.typography.bodyMedium)
                Text(
                    "Günde en fazla bir kez yalnızca sürüm bilgisi (küçük metadata) istenir. " +
                        "İndirme asla kendiliğinden başlatılmaz.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(Modifier.width(10.dp))
            Switch(checked = u.autoCheck, onCheckedChange = { vm.setAutoCheck(it) })
        }
    }
}

@Composable
private fun SecurityCard() {
    SectionCard("Güvenlik ve Gizlilik") {
        BulletList(
            listOf(
                "Yalnızca HTTPS ve yalnızca github.com/Awulokune/AwuGokturk-Android adresleri.",
                "Yönlendirmeler adım adım doğrulanır; izin listesi dışına çıkılamaz.",
                "Dosya geçici konuma indirilir; SHA-256 ve yapı doğrulanmadan etkinleştirilmez.",
                "Yeni model önce gerçekten yüklenir; başarısız olursa önceki modele dönülür.",
                "Model dosyası veri olarak işlenir; kod çalıştırılmaz, dosya adı doğrulanır.",
                "Erişim anahtarı/parola istenmez ve uygulamaya gömülmez.",
                "İndirme yalnızca sizin onayınızla başlar; arka planda indirme yapılmaz.",
                "İnternet yokken uygulama tamamen çevrimdışı çalışmaya devam eder."
            )
        )
    }
}

// ---------------------------------------------------------------------------

@Composable
private fun Note(text: String, color: Color) {
    Text(text, style = MaterialTheme.typography.bodySmall, color = color)
}

@Composable
private fun StatusDot(color: Color) {
    Box(
        Modifier
            .size(9.dp)
            .clip(androidx.compose.foundation.shape.CircleShape)
            .background(color)
    )
}
