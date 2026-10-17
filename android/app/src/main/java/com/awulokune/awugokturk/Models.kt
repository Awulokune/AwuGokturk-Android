package com.awulokune.awugokturk

import org.json.JSONArray
import org.json.JSONObject

/** Python köprüsünden gelen JSON'un Kotlin modeli. */

data class GuardFinding(val level: String, val message: String)

data class BuildInfo(
    val ran: Boolean,
    val ok: Boolean,
    val tool: String,
    val kind: String,
    val note: String,
    val stderr: String
) {
    companion object {
        private fun nstr(o: JSONObject, k: String): String =
            if (!o.has(k) || o.isNull(k)) "" else o.optString(k, "")

        fun from(o: JSONObject?): BuildInfo {
            if (o == null) return BuildInfo(false, false, "", "none", "", "")
            return BuildInfo(
                ran = o.optBoolean("ran", false),
                ok = o.optBoolean("ok", false),
                tool = nstr(o, "tool"),
                kind = nstr(o, "kind").ifEmpty { "none" },
                note = nstr(o, "note"),
                stderr = nstr(o, "stderr")
            )
        }
    }
}

data class AgentResult(
    val status: String,
    val category: String?,
    val intent: String?,
    val message: String,
    val board: String?,
    val framework: String?,
    val code: String?,
    val modules: List<String>,
    val libraries: List<String>,
    val wiring: List<String>,
    val assumptions: List<String>,
    val guard: List<GuardFinding>,
    val build: BuildInfo,
    val hardwarePlan: List<String>,
    val questions: List<String>,
    val notes: List<String>,
    val classifierHint: String?,
    val modelName: String
) {
    val isCode: Boolean get() = code != null

    companion object {
        private fun nstr(o: JSONObject, k: String): String? {
            if (!o.has(k) || o.isNull(k)) return null
            return o.optString(k, "").ifEmpty { null }
        }

        private fun strList(a: JSONArray?): List<String> {
            if (a == null) return emptyList()
            return (0 until a.length()).map { a.getString(it) }
        }

        fun from(o: JSONObject): AgentResult {
            val guardArr = o.optJSONArray("guard")
            val guard = mutableListOf<GuardFinding>()
            if (guardArr != null) {
                for (i in 0 until guardArr.length()) {
                    val g = guardArr.getJSONObject(i)
                    guard.add(GuardFinding(g.optString("level", "info"), g.optString("message", "")))
                }
            }
            return AgentResult(
                status = o.optString("status", "info"),
                category = nstr(o, "category"),
                intent = nstr(o, "intent"),
                message = o.optString("message", ""),
                board = nstr(o, "board"),
                framework = nstr(o, "framework"),
                code = nstr(o, "code"),
                modules = strList(o.optJSONArray("modules")),
                libraries = strList(o.optJSONArray("libraries")),
                wiring = strList(o.optJSONArray("wiring")),
                assumptions = strList(o.optJSONArray("assumptions")),
                guard = guard,
                build = BuildInfo.from(o.optJSONObject("build")),
                hardwarePlan = strList(o.optJSONArray("hardware_plan")),
                questions = strList(o.optJSONArray("questions")),
                notes = strList(o.optJSONArray("notes")),
                classifierHint = nstr(o, "classifier_hint"),
                modelName = o.optString("model_name", "AwuGöktürk-Microcontroller:5K")
            )
        }
    }
}

/**
 * Sohbet balonunda gösterilen mesaj.
 * Gerçek ajan çıktısını (kod, AwuGuard sonucu, derleme durumu) taşır; böylece
 * arayüz sahte metin üretmez, modelin gerçek yanıtını gösterir.
 */
data class ChatMessage(
    val role: String,                      // "user" | "agent"
    val text: String,
    val code: String? = null,
    val board: String? = null,
    val guard: List<GuardFinding> = emptyList(),
    val status: String = "ok",
    val questions: List<String> = emptyList(),
    val buildRan: Boolean = false,
    val buildOk: Boolean = false,
    val buildNote: String = ""
) {
    val isUser: Boolean get() = role == "user"

    fun toJson(): JSONObject {
        val o = JSONObject()
        o.put("role", role)
        o.put("text", text)
        if (code != null) o.put("code", code)
        if (board != null) o.put("board", board)
        o.put("status", status)
        if (questions.isNotEmpty()) o.put("questions", JSONArray(questions))
        if (guard.isNotEmpty()) {
            val arr = JSONArray()
            for (g in guard) arr.put(JSONObject().put("level", g.level).put("message", g.message))
            o.put("guard", arr)
        }
        if (buildRan) {
            o.put("buildRan", true)
            o.put("buildOk", buildOk)
            o.put("buildNote", buildNote)
        }
        return o
    }

    companion object {
        fun user(text: String) = ChatMessage(role = "user", text = text)

        fun agent(r: AgentResult) = ChatMessage(
            role = "agent",
            text = r.message,
            code = r.code,
            board = r.board,
            guard = r.guard,
            status = r.status,
            questions = r.questions,
            buildRan = r.build.ran,
            buildOk = r.build.ok,
            buildNote = r.build.note
        )

        private fun strList(a: JSONArray?): List<String> {
            if (a == null) return emptyList()
            return (0 until a.length()).map { a.optString(it, "") }
        }

        fun fromJson(o: JSONObject): ChatMessage {
            val guard = mutableListOf<GuardFinding>()
            o.optJSONArray("guard")?.let { arr ->
                for (i in 0 until arr.length()) {
                    val g = arr.optJSONObject(i) ?: continue
                    guard.add(GuardFinding(g.optString("level", "info"), g.optString("message", "")))
                }
            }
            return ChatMessage(
                role = o.optString("role", "agent"),
                text = o.optString("text", ""),
                code = if (o.has("code") && !o.isNull("code")) o.optString("code") else null,
                board = if (o.has("board") && !o.isNull("board")) o.optString("board") else null,
                guard = guard,
                status = o.optString("status", "ok"),
                questions = strList(o.optJSONArray("questions")),
                buildRan = o.optBoolean("buildRan", false),
                buildOk = o.optBoolean("buildOk", false),
                buildNote = o.optString("buildNote", "")
            )
        }
    }
}

/** Cihazda saklanan tek bir sohbet oturumu. */
data class ChatSession(
    val id: String,
    val title: String,
    val updatedAt: Long,
    val messages: List<ChatMessage>
)

/** Geçmiş listesinde gösterilen özet (mesaj gövdeleri taşınmaz). */
data class SessionMeta(
    val id: String,
    val title: String,
    val updatedAt: Long,
    val count: Int
)
