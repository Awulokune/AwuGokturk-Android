package com.awulokune.awugokturk

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Yerel sohbet deposu (cihaz içi, tamamen çevrimdışı).
 *
 * - Birden çok sohbet oturumu tutar (geçmiş menüsü gerçekten çalışır).
 * - Hiçbir veri cihaz dışına çıkmaz; INTERNET izni yoktur.
 * - Kullanıcı Ayarlar'dan tüm geçmişi silebilir.
 * - Eski (tek oturumlu) `chat_history.json` varsa sessizce içe aktarılır.
 */
class ChatStore(context: Context) {
    private val file = File(context.filesDir, "chat_sessions.json")
    private val legacyFile = File(context.filesDir, "chat_history.json")

    /** En fazla bu kadar oturum saklanır (dosya şişmesin). */
    private val maxSessions = 40

    fun load(): MutableList<ChatSession> {
        return try {
            if (file.exists()) parse(file.readText()) else migrateLegacy()
        } catch (_: Exception) {
            // Bozuk dosya: veri uydurma, boş dön.
            mutableListOf()
        }
    }

    fun save(sessions: List<ChatSession>) {
        try {
            val arr = JSONArray()
            sessions.take(maxSessions).forEach { s ->
                val msgs = JSONArray()
                s.messages.forEach { msgs.put(it.toJson()) }
                arr.put(
                    JSONObject()
                        .put("id", s.id)
                        .put("title", s.title)
                        .put("updatedAt", s.updatedAt)
                        .put("messages", msgs)
                )
            }
            file.writeText(JSONObject().put("version", 1).put("sessions", arr).toString())
        } catch (_: Exception) {
            // Yazma başarısız olsa da uygulama çalışmaya devam eder.
        }
    }

    fun clearAll() {
        try {
            file.delete()
            legacyFile.delete()
        } catch (_: Exception) {
        }
    }

    private fun parse(text: String): MutableList<ChatSession> {
        val out = mutableListOf<ChatSession>()
        val root = JSONObject(text)
        val arr = root.optJSONArray("sessions") ?: JSONArray()
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            val msgs = mutableListOf<ChatMessage>()
            o.optJSONArray("messages")?.let { m ->
                for (j in 0 until m.length()) {
                    m.optJSONObject(j)?.let { msgs.add(ChatMessage.fromJson(it)) }
                }
            }
            out.add(
                ChatSession(
                    id = o.optString("id", "s$i"),
                    title = o.optString("title", "Sohbet"),
                    updatedAt = o.optLong("updatedAt", 0L),
                    messages = msgs
                )
            )
        }
        return out
    }

    /** Eski tek-oturumlu geçmişi (varsa) tek bir oturuma dönüştürür. */
    private fun migrateLegacy(): MutableList<ChatSession> {
        val out = mutableListOf<ChatSession>()
        try {
            if (legacyFile.exists()) {
                val arr = JSONArray(legacyFile.readText())
                val msgs = mutableListOf<ChatMessage>()
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    msgs.add(ChatMessage(o.optString("role", "agent"), o.optString("text", "")))
                }
                if (msgs.isNotEmpty()) {
                    out.add(
                        ChatSession(
                            id = "legacy",
                            title = "Önceki sohbet",
                            updatedAt = System.currentTimeMillis(),
                            messages = msgs
                        )
                    )
                    save(out)
                }
                legacyFile.delete()
            }
        } catch (_: Exception) {
            out.clear()
        }
        return out
    }
}
