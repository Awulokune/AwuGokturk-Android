package com.awulokune.awugokturk

import org.json.JSONObject

/**
 * Model güncelleme durumu (Kotlin tarafı).
 *
 * İş mantığı Python `awa_agent.model_updater` içindedir; burada yalnızca
 * JSON'un Kotlin'e taşınmış hâli tutulur. Böylece mimari bozulmaz ve karar
 * mantığı tek yerde (Python, test edilebilir) kalır.
 */

/** İndirme/doğrulama/etkinleştirme ilerlemesi. */
data class UpdateProgress(
    val state: String = "idle",          // idle|downloading|verifying|applying|done|error|cancelled
    val percent: Int = -1,               // -1 → bilinmiyor
    val processed: Long = 0L,
    val total: Long = 0L,
    val processedText: String = "",
    val totalText: String = "",
    val remainingText: String = "",
    val message: String = "",
    val error: String = "",
    val errorCode: String = "",
    val rolledBack: Boolean = false,
    val running: Boolean = false,
    val version: String = "",
    val activeVersion: String = ""
) {
    /** İş sürüyor mu (iptal düğmesi gösterilir). */
    val busy: Boolean get() = state == "downloading" || state == "verifying" || state == "applying"

    /** Bitiş durumu (sonuç gösterilir). */
    val terminal: Boolean get() = state == "done" || state == "error" || state == "cancelled"

    val done: Boolean get() = state == "done"
    val failed: Boolean get() = state == "error"

    /** Arayüzde gösterilecek aşama adı. */
    val stageLabel: String
        get() = when (state) {
            "downloading" -> "İndiriliyor"
            "verifying" -> "Doğrulanıyor"
            "applying" -> "Etkinleştiriliyor"
            "done" -> "Tamamlandı"
            "error" -> "Başarısız"
            "cancelled" -> "İptal edildi"
            else -> "Bekliyor"
        }

    companion object {
        fun from(o: JSONObject): UpdateProgress = UpdateProgress(
            state = o.optString("state", "idle"),
            percent = o.optInt("percent", -1),
            processed = o.optLong("processed", 0L),
            total = o.optLong("total", 0L),
            processedText = o.optString("processed_h", ""),
            totalText = o.optString("total_h", ""),
            remainingText = o.optString("remaining_h", ""),
            message = o.optString("message", ""),
            error = o.optString("error", ""),
            errorCode = o.optString("error_code", ""),
            rolledBack = o.optBoolean("rolled_back", false),
            running = o.optBoolean("running", false),
            version = o.optString("version", ""),
            activeVersion = o.optString("active_version", "")
        )
    }
}

/** "Model Güncellemeleri" bölümünün tüm durumu. */
data class UpdateInfo(
    val installedVersion: String = "",
    val bundledVersion: String = "",
    val activeVersion: String = "",
    val source: String = "",
    val latestVersion: String = "",
    val updateAvailable: Boolean = false,
    val checked: Boolean = false,          // en az bir kontrol yapıldı mı?
    val checking: Boolean = false,
    val sizeText: String = "",
    val releaseNotes: String = "",
    val minAppVersion: String = "",
    val tokenizerVersion: String = "",
    val architecture: String = "",
    val releaseTag: String = "",
    val releaseUrl: String = "",
    val canRollback: Boolean = false,
    val backupVersion: String = "",
    val autoCheck: Boolean = true,
    val lastCheckAt: Long = 0L,
    val message: String = "",
    val error: String? = null,
    val progress: UpdateProgress = UpdateProgress(),
    val appVersion: String = ""
) {
    /** Yüklü modelin kaynağı (dürüst etiket). */
    val sourceLabel: String
        get() = when (source) {
            "updated" -> "indirilmiş sürüm"
            "bundled" -> "uygulamayla gelen sürüm"
            "bundled_fallback" -> "uygulamayla gelen sürüm (bozuk güncelleme geri alındı)"
            else -> source.ifEmpty { "bilinmiyor" }
        }

    val hasRevision: Boolean get() = installedVersion.isNotEmpty() && installedVersion != bundledVersion

    companion object {

        /** JSON `null` değerini "yok" sayar (`optString` aksi hâlde "null" döner). */
        private fun JSONObject.txt(key: String, def: String = ""): String {
            if (!has(key) || isNull(key)) return def
            val v = optString(key, def)
            return if (v == "null") def else v
        }

        /** Hata kodunu kullanıcıya gösterilecek Türkçe cümleye çevirir. */
        fun errorText(code: String): String = when (code) {
            "" -> ""
            "network" -> "Ağ hatası: sunucuya ulaşılamadı (internet bağlantısını kontrol edin)."
            "rate_limit" -> "GitHub API istek sınırı aşıldı; sınır yenilenince yeniden deneyin."
            "http" -> "Sunucu hatası: GitHub beklenen yanıtı vermedi."
            "unsafe_url" -> "Güvenlik: izin verilmeyen bir adres reddedildi."
            "invalid_manifest" -> "Yayımlanmış sürüm manifesti geçersiz; sürüm önerilmedi."
            "size_limit" -> "Dosya boyut sınırı aşıldı."
            "disk" -> "Yeterli disk alanı yok."
            "verification" -> "Doğrulama başarısız."
            "bridge" -> "Güncelleme köprüsü hatası."
            else -> "Hata: $code"
        }

        /** `update_status()` (kalıcı durum + ilerleme) yanıtından. */
        fun fromStatus(o: JSONObject): UpdateInfo {
            val last = o.optJSONObject("last_check_result")
            val prog = o.optJSONObject("progress")
            val lastErr = last?.txt("error").orEmpty()
            val lastMsg = last?.txt("message").orEmpty()
            val hasLast = last != null && last.length() > 0
            val latest = last?.txt("latest_version").orEmpty()
            return UpdateInfo(
                installedVersion = o.txt("installed_version"),
                bundledVersion = o.txt("bundled_version"),
                activeVersion = o.txt("active_version"),
                source = o.txt("source"),
                latestVersion = latest,
                updateAvailable = last?.optBoolean("update_available", false) ?: false,
                checked = hasLast && (last?.has("ok") ?: false),
                sizeText = "",
                canRollback = o.optBoolean("can_rollback", false),
                backupVersion = o.txt("backup_version"),
                autoCheck = o.optBoolean("auto_check", true),
                // Python saniye cinsinden zaman damgası yazar; arayüz milisaniye bekler.
                lastCheckAt = o.optLong("last_check_at", 0L) * 1000L,
                message = if (lastErr.isEmpty()) lastMsg else "",
                error = if (lastErr.isNotEmpty()) lastMsg.ifEmpty { errorText(lastErr) } else null,
                progress = prog?.let { UpdateProgress.from(it) } ?: UpdateProgress(),
                appVersion = o.txt("app_version")
            )
        }

        /** `update_check()` yanıtından (ağ kontrolü sonucu). */
        fun fromCheck(o: JSONObject, prev: UpdateInfo): UpdateInfo {
            if (!o.optBoolean("ok", false)) {
                val code = o.txt("error")
                return prev.copy(
                    checking = false,
                    checked = true,
                    message = "",
                    error = o.txt("message").ifEmpty { errorText(code) }
                )
            }
            val man = o.optJSONObject("manifest")
            val rel = o.optJSONObject("release")
            val notes = o.txt("release_notes")
                .ifEmpty { man?.txt("release_notes").orEmpty() }
            val available = o.optBoolean("update_available", false)
            return prev.copy(
                checking = false,
                checked = true,
                installedVersion = o.txt("installed_version").ifEmpty { prev.installedVersion },
                latestVersion = o.txt("latest_version"),
                updateAvailable = available,
                sizeText = o.txt("size_h"),
                releaseNotes = notes,
                minAppVersion = o.txt("min_app_version"),
                tokenizerVersion = o.txt("tokenizer_version"),
                architecture = o.txt("architecture"),
                releaseTag = rel?.txt("tag").orEmpty(),
                releaseUrl = rel?.txt("html_url").orEmpty(),
                lastCheckAt = o.optLong("checked_at", 0L) * 1000L,
                message = o.txt("message"),
                error = null,
                progress = prev.progress
            )
        }
    }
}
