package com.awulokune.awugokturk.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.awulokune.awugokturk.AgentResult
import com.awulokune.awugokturk.AppState
import com.awulokune.awugokturk.AwuViewModel
import com.awulokune.awugokturk.ChatMessage

/**
 * Kod sekmesi: sohbet deneyiminden bağımsız bir ürün değil, asistanın
 * Arduino kod üretme yeteneği. Kart seçimi burada yapılır; sohbette zorunlu
 * değildir.
 */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun CodeScreen(state: AppState, vm: AwuViewModel) {
    var prompt by rememberSaveable { mutableStateOf("") }
    var selected by rememberSaveable { mutableStateOf(0) }
    val boards = state.boards

    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Column {
                    Text("Kod Üretimi", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(
                        "Arduino Uno · Mega 2560 · ESP32",
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

        state.error?.let { ErrorBanner(it) }

        Column(
            Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 14.dp)
        ) {
            Text(
                "Kartı seçin, isteğinizi doğal dille yazın. Desteklenmeyen özellikler için kod UYDURULMAZ.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(12.dp))

            if (boards.isEmpty()) {
                Text(
                    "Kart listesi yüklenemedi (yerel model hazır değil).",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            } else {
                Text("Hedef kart", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(6.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    boards.forEachIndexed { i, b ->
                        FilterChip(
                            selected = i == selected,
                            onClick = { selected = i },
                            label = { Text(b.name) }
                        )
                    }
                }
            }

            Spacer(Modifier.height(14.dp))
            OutlinedTextField(
                value = prompt,
                onValueChange = { prompt = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("Örn: 7. pindeki LED'i 500 ms aralıkla yakıp söndür.") },
                minLines = 3,
                maxLines = 7,
                shape = RoundedCornerShape(16.dp)
            )
            Spacer(Modifier.height(12.dp))

            Button(
                onClick = {
                    if (boards.isNotEmpty()) {
                        vm.generateCode(prompt.trim(), boards[selected])
                    }
                },
                enabled = prompt.isNotBlank() && !state.codeBusy && state.ready && boards.isNotEmpty(),
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(14.dp)
            ) {
                if (state.codeBusy) {
                    CircularProgressIndicator(
                        Modifier.size(16.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                    Spacer(Modifier.width(8.dp))
                }
                Text(if (state.codeBusy) "Üretiliyor…" else "Kod Üret")
            }

            Spacer(Modifier.height(20.dp))

            val r = state.lastCode
            if (r != null) {
                CodeResult(r)
            } else {
                Text(
                    "Henüz kod üretilmedi.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(Modifier.height(12.dp))
        }
    }
}

private fun statusText(s: String): String = when (s) {
    "ok" -> "kod üretildi"
    "error" -> "hata"
    "needs_info" -> "bilgi eksik"
    "unsupported" -> "desteklenmiyor"
    else -> s
}

private fun statusColor(s: String): Color = when (s) {
    "ok" -> Basarili
    "error" -> HataKirmizi
    "needs_info" -> UyariAmber
    "unsupported" -> UyariAmber
    else -> Basarili
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CodeResult(r: AgentResult) {
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        StatusChip(statusText(r.status), color = statusColor(r.status))
        r.category?.let { StatusChip(it) }
        r.board?.let { StatusChip(it, color = Mavi) }
        r.classifierHint?.let { StatusChip("5K: $it", color = Mavi) }
    }

    Spacer(Modifier.height(12.dp))
    AgentBlock(ChatMessage.agent(r))

    if (r.questions.isNotEmpty()) {
        Spacer(Modifier.height(12.dp))
        SectionCard("Eksik bilgi / Sorular") { BulletList(r.questions) }
    }

    if (r.modules.isNotEmpty() || r.libraries.isNotEmpty() || r.framework != null) {
        SectionCard("Ayrıntılar") {
            r.framework?.let { KeyVal("Framework", it) }
            if (r.modules.isNotEmpty()) KeyVal("Modüller", r.modules.joinToString(", "))
            if (r.libraries.isNotEmpty()) KeyVal("Kütüphaneler", r.libraries.joinToString(", "))
            if (r.classifierHint != null) KeyVal("5K sınıflandırıcı ipucu", r.classifierHint)
        }
    }

    if (r.hardwarePlan.isNotEmpty()) {
        SectionCard("Donanım doğrulama planı (henüz uygulanmadı)") { BulletList(r.hardwarePlan) }
    }
    if (r.wiring.isNotEmpty()) SectionCard("Bağlantı Notları") { BulletList(r.wiring) }
    if (r.assumptions.isNotEmpty()) SectionCard("Varsayımlar") { BulletList(r.assumptions) }
    if (r.notes.isNotEmpty()) SectionCard("Notlar") { BulletList(r.notes) }

    if (r.build.ran && !r.build.ok && r.build.stderr.isNotEmpty()) {
        SectionCard("Derleme çıktısı (host sözdizimi)") {
            Text(
                r.build.stderr,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
        }
    }
}
