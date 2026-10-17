package com.awulokune.awugokturk.ui

import androidx.compose.foundation.background
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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.awulokune.awugokturk.AppState
import com.awulokune.awugokturk.AwuViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(state: AppState, vm: AwuViewModel) {
    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Column {
                    Text("Ayarlar", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(
                        "Yerel · çevrimdışı · gizli",
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
                .padding(horizontal = 16.dp, vertical = 14.dp)
        ) {
            SectionCard("Görünüm") {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("Koyu tema", style = MaterialTheme.typography.bodyMedium)
                        Text(
                            "Turkuaz ve mavi vurgulu koyu tasarım (varsayılan).",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Switch(checked = state.themeDark, onCheckedChange = { vm.toggleTheme() })
                }
            }

            SectionCard("Model") {
                KeyVal("Uygulama", state.appName)
                KeyVal("Model", state.modelName)
                KeyVal("Slogan", state.slogan)
                KeyVal("Paket", "com.awulokune.awugokturk")
                KeyVal("Sürüm", state.version)
                KeyVal(
                    "5K sınıflandırıcı",
                    if (state.classifierAvailable) "yüklü (${state.classifierParams} parametre)"
                    else "yüklü değil"
                )
                KeyVal("Desteklenen modül", state.modulesCount.toString())
                if (state.categories.isNotEmpty()) {
                    KeyValBlock("Kategoriler", state.categories.joinToString(", "))
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    "5K sınıflandırıcı yalnızca görev türü için ipucu üretir; sohbet ve kod " +
                        "üretimi kural/şablon katmanıyla yapılır.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            SectionCard("Çevrimdışı Durum") {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    StatusDot(if (state.ready) Basarili else UyariAmber)
                    Spacer(Modifier.width(8.dp))
                    Text(
                        state.modelStatus,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    "Sohbet ve kod üretimi tamamen cihazda çalışır; internet olmadan da " +
                        "kullanılabilir. Ağ yalnızca isteğe bağlı MODEL güncellemesi için " +
                        "kullanılır ve yalnızca github.com/Awulokune/AwuGokturk-Android adresine gider.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            SectionCard("Model Güncellemeleri") {
                KeyVal("Yüklü model sürümü", state.update.installedVersion.ifEmpty { state.version })
                KeyVal(
                    "En son uyumlu sürüm",
                    state.update.latestVersion.ifEmpty { "—" }
                )
                KeyVal(
                    "Son kontrol",
                    if (state.update.lastCheckAt > 0L) zaman(state.update.lastCheckAt) else "hiç yapılmadı"
                )
                if (state.update.progress.busy) {
                    Spacer(Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        StatusDot(MaterialTheme.colorScheme.primary)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            state.update.progress.stageLabel +
                                if (state.update.progress.percent >= 0) " · %${state.update.progress.percent}" else "",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                } else if (state.update.updateAvailable) {
                    Spacer(Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        StatusDot(UyariAmber)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "Yeni sürüm hazır: ${state.update.latestVersion}",
                            style = MaterialTheme.typography.bodySmall,
                            color = UyariAmber
                        )
                    }
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    "Model güncellemesi uygulama güncellemesinden bağımsızdır. Kontrol ve indirme " +
                        "işlemlerini bu ekrandan yönetebilirsiniz.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(10.dp))
                Button(onClick = { vm.openModelUpdates() }) {
                    Text("Güncellemeleri aç")
                }
            }

            SectionCard("Yerel Veri") {
                Text(
                    "${state.history.size} sohbet · ${state.messageCount} mesaj bu cihazda saklanıyor.",
                    style = MaterialTheme.typography.bodySmall
                )
                Spacer(Modifier.height(10.dp))
                Button(
                    onClick = { vm.clearHistory() },
                    enabled = state.messageCount > 0
                ) {
                    Icon(Icons.Filled.Delete, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Geçmişi temizle")
                }
            }

            SectionCard("Derleme Araçları") {
                if (state.tools.isEmpty()) {
                    Text("Bilgi yok.", style = MaterialTheme.typography.bodySmall)
                } else {
                    state.tools.forEach { (k, v) -> KeyVal(k, if (v) "var" else "yok") }
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    "Cihazda AVR/ESP32 derleyicisi bulunmadığından üretilen kod gerçek hedefe " +
                        "derlenmez. Derleme ve donanım testi durumu her yanıtta açıkça etiketlenir.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            SectionCard("Gizlilik") {
                Text(
                    "• Sohbet içeriği ve üretilen kod harici sunuculara gönderilmez.\n" +
                        "• Analitik, reklam veya izleme SDK'sı yoktur.\n" +
                        "• API anahtarı istenmez; hesap girişi gerekmez.\n" +
                        "• Sohbet geçmişi yalnızca cihazda tutulur ve sizin kontrolünüzdedir.\n" +
                        "• Ağ yalnızca isteğe bağlı model güncellemesi için, yalnızca " +
                        "github.com/Awulokune/AwuGokturk-Android adresine kullanılır.\n" +
                        "• Model ağırlıkları APK içinde gelir; güncelleme zorunlu değildir.",
                    style = MaterialTheme.typography.bodySmall
                )
            }

            Spacer(Modifier.height(10.dp))
            Text(
                "${state.appName} ${state.version} — NO SAY CAVAS",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
            Spacer(Modifier.height(12.dp))
        }
    }
}

@Composable
private fun StatusDot(color: androidx.compose.ui.graphics.Color) {
    androidx.compose.foundation.layout.Box(
        Modifier
            .size(9.dp)
            .clip(androidx.compose.foundation.shape.CircleShape)
            .background(color)
    )
}
