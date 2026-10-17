package com.awulokune.awugokturk

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

data class BoardOption(val key: String, val name: String, val hint: String)

data class AppState(
    val messages: List<ChatMessage> = emptyList(),
    val activeId: String = "",
    val history: List<SessionMeta> = emptyList(),
    val busy: Boolean = false,
    val ready: Boolean = false,
    val error: String? = null,
    val modelStatus: String = "başlatılıyor…",
    val classifierLabel: String? = null,
    val appName: String = "AwuGöktürk",
    val modelName: String = "AwuGöktürk-Microcontroller:5K",
    val slogan: String = "NO SAY CAVAS",
    val version: String = "1.0.0",
    val boards: List<BoardOption> = emptyList(),
    val modulesCount: Int = 0,
    val categories: List<String> = emptyList(),
    val tools: Map<String, Boolean> = emptyMap(),
    val classifierAvailable: Boolean = false,
    val classifierParams: Int = 0,
    val lastCode: AgentResult? = null,
    val codeBusy: Boolean = false,
    val themeDark: Boolean = true,
    /** Model güncelleme durumu (Ayarlar → Model Güncellemeleri). */
    val update: UpdateInfo = UpdateInfo(),
    /** Model Güncellemeleri ekranı açık mı? */
    val modelScreen: Boolean = false
) {
    val messageCount: Int get() = history.sumOf { it.count }
}

class AwuViewModel(app: Application) : AndroidViewModel(app) {

    private val store = ChatStore(app)
    private val sessions = mutableListOf<ChatSession>()
    private var activeId: String = ""

    private val _state = MutableStateFlow(AppState())
    val state: StateFlow<AppState> = _state.asStateFlow()

    init {
        val loaded = store.load()
        sessions.addAll(loaded)
        if (sessions.isEmpty()) sessions.add(newSession())
        activeId = sessions.last().id
        publish()
        bootstrap()
    }

    // ---- Sohbet ----

    fun send(text: String) {
        val t = text.trim()
        if (t.isEmpty() || _state.value.busy || !_state.value.ready) return
        append(ChatMessage.user(t))
        _state.value = _state.value.copy(busy = true, error = null)
        viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    AgentResult.from(PythonBridge.handle(t, null))
                }
                append(ChatMessage.agent(result))
                _state.value = _state.value.copy(
                    busy = false,
                    classifierLabel = result.classifierHint,
                    lastCode = if (result.isCode) result else _state.value.lastCode
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(busy = false, error = e.message ?: "Yanıt üretilemedi.")
            }
        }
    }

    /** Yeni sohbet: mevcut sohbet boş değilse geçmişe alınır, boş bir oturum açılır. */
    fun newChat() {
        if (activeSession().messages.isEmpty()) return
        val s = newSession()
        sessions.add(s)
        activeId = s.id
        store.save(sessions)
        publish()
    }

    fun openSession(id: String) {
        if (sessions.none { it.id == id }) return
        activeId = id
        publish()
    }

    fun deleteSession(id: String) {
        sessions.removeAll { it.id == id }
        if (sessions.isEmpty()) sessions.add(newSession())
        if (activeId == id) activeId = sessions.last().id
        store.save(sessions)
        publish()
    }

    /** Tüm yerel geçmişi siler (Ayarlar). */
    fun clearHistory() {
        sessions.clear()
        val s = newSession()
        sessions.add(s)
        activeId = s.id
        store.clearAll()
        publish()
    }

    private fun newSession() = ChatSession(
        id = UUID.randomUUID().toString(),
        title = "Yeni sohbet",
        updatedAt = System.currentTimeMillis(),
        messages = emptyList()
    )

    private fun activeSession(): ChatSession {
        val found = sessions.firstOrNull { it.id == activeId }
        if (found != null) return found
        val s = newSession()
        sessions.add(s)
        activeId = s.id
        return s
    }

    private fun append(m: ChatMessage) {
        val cur = activeSession()
        val msgs = cur.messages + m
        val title = if (cur.messages.none { it.isUser } && m.isUser) titleOf(m.text) else cur.title
        val updated = cur.copy(messages = msgs, title = title, updatedAt = System.currentTimeMillis())
        val idx = sessions.indexOfFirst { it.id == cur.id }
        if (idx >= 0) sessions[idx] = updated else sessions.add(updated)
        store.save(sessions)
        publish()
    }

    private fun titleOf(text: String): String {
        val t = text.trim().replace("\n", " ")
        return if (t.length <= 40) t else t.substring(0, 39).trimEnd() + "…"
    }

    private fun publish() {
        val cur = activeSession()
        _state.value = _state.value.copy(
            messages = cur.messages,
            activeId = activeId,
            history = sessions
                .filter { it.messages.isNotEmpty() }
                .sortedByDescending { it.updatedAt }
                .map { SessionMeta(it.id, it.title, it.updatedAt, it.messages.size) }
        )
    }

    // ---- Kod üretimi (Kod sekmesi) ----

    fun generateCode(text: String, board: BoardOption) {
        val t = text.trim()
        if (t.isEmpty() || _state.value.codeBusy || !_state.value.ready) return
        _state.value = _state.value.copy(codeBusy = true, error = null)
        viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    AgentResult.from(PythonBridge.handle(t, board.hint))
                }
                _state.value = _state.value.copy(codeBusy = false, lastCode = result)
            } catch (e: Exception) {
                _state.value = _state.value.copy(codeBusy = false, error = e.message ?: "Kod üretilemedi.")
            }
        }
    }

    fun toggleTheme() {
        _state.value = _state.value.copy(themeDark = !_state.value.themeDark)
    }

    // ---- Model güncellemeleri (GitHub Releases) ----
    //
    // Ağ ve dosya işlemleri Python tarafında yapılır; burada yalnızca durum
    // yönetimi ve ilerleme yoklaması vardır. Otomatik kontrol SADECE küçük
    // metadata isteği yapar; hiçbir zaman kendiliğinden indirme başlatmaz.

    private var updateJob: Job? = null

    fun openModelUpdates() {
        _state.value = _state.value.copy(modelScreen = true)
        refreshUpdateStatus()
    }

    fun closeModelUpdates() {
        _state.value = _state.value.copy(modelScreen = false)
    }

    /** Kalıcı güncelleme durumunu tazeler; süren iş varsa yoklamayı başlatır. */
    fun refreshUpdateStatus() {
        viewModelScope.launch {
            try {
                val s = withContext(Dispatchers.IO) { PythonBridge.updateStatus() }
                val info = UpdateInfo.fromStatus(s)
                _state.value = _state.value.copy(update = info)
                if (info.progress.busy && updateJob?.isActive != true) pollUpdate()
            } catch (_: Exception) {
                // Durum okunamazsa mevcut bilgi korunur (uydurma yapılmaz).
            }
        }
    }

    /** GitHub Releases kontrolü (ağ isteği). `force=false` → 24 saat önbelleği. */
    fun checkForUpdates(force: Boolean = true) {
        if (_state.value.update.checking) return
        _state.value = _state.value.copy(
            update = _state.value.update.copy(checking = true, error = null, message = "")
        )
        viewModelScope.launch {
            val res = try {
                withContext(Dispatchers.IO) { PythonBridge.updateCheck(force) }
            } catch (e: Exception) {
                JSONObject()
                    .put("ok", false)
                    .put("error", "bridge")
                    .put("message", e.message ?: "Güncelleme kontrolü yapılamadı.")
            }
            _state.value = _state.value.copy(
                update = UpdateInfo.fromCheck(res, _state.value.update)
            )
        }
    }

    /** Kullanıcı onayıyla: indir → doğrula → etkinleştir (arka planda). */
    fun startModelUpdate() {
        if (_state.value.update.progress.busy) return
        viewModelScope.launch {
            val r = try {
                withContext(Dispatchers.IO) { PythonBridge.updateDownloadStart() }
            } catch (e: Exception) {
                JSONObject().put("ok", false).put("message", e.message ?: "İndirme başlatılamadı.")
            }
            if (!r.optBoolean("ok", false)) {
                _state.value = _state.value.copy(
                    update = _state.value.update.copy(
                        error = r.optString("message", "İndirme başlatılamadı.")
                    )
                )
                return@launch
            }
            _state.value = _state.value.copy(
                update = _state.value.update.copy(error = null, message = "")
            )
            pollUpdate()
        }
    }

    fun cancelModelUpdate() {
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) { PythonBridge.updateCancel() }
            } catch (_: Exception) {
            }
        }
    }

    /** Yedekteki önceki modele döner ve onu yükler. */
    fun rollbackModel() {
        viewModelScope.launch {
            val r = try {
                withContext(Dispatchers.IO) { PythonBridge.updateRollback() }
            } catch (e: Exception) {
                JSONObject().put("ok", false).put("message", e.message ?: "Geri dönülemedi.")
            }
            val ok = r.optBoolean("ok", false)
            val statusJson = r.optJSONObject("status")
            val info = statusJson?.let { UpdateInfo.fromStatus(it) } ?: _state.value.update
            _state.value = _state.value.copy(
                update = info.copy(error = if (ok) null else r.optString("message", "Geri dönülemedi."))
            )
            if (ok) refreshClassifier()
        }
    }

    fun setAutoCheck(enabled: Boolean) {
        _state.value = _state.value.copy(update = _state.value.update.copy(autoCheck = enabled))
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) { PythonBridge.updateSetAuto(enabled) }
            } catch (_: Exception) {
            }
            refreshUpdateStatus()
        }
    }

    private fun pollUpdate() {
        updateJob?.cancel()
        updateJob = viewModelScope.launch {
            while (isActive) {
                val p = try {
                    withContext(Dispatchers.IO) { PythonBridge.updateProgress() }
                } catch (e: Exception) {
                    null
                }
                if (p != null) {
                    val prog = UpdateProgress.from(p)
                    _state.value = _state.value.copy(
                        update = _state.value.update.copy(progress = prog)
                    )
                    if (prog.terminal) {
                        finishUpdate()
                        break
                    }
                }
                delay(280)
            }
        }
    }

    private suspend fun finishUpdate() {
        try {
            val s = withContext(Dispatchers.IO) { PythonBridge.updateStatus() }
            val fresh = UpdateInfo.fromStatus(s)
            // Sonucu (bitti/hata mesajı) korumak için ilerleme durumunu koruyoruz.
            val keep = _state.value.update.progress
            _state.value = _state.value.copy(update = fresh.copy(progress = keep))
        } catch (_: Exception) {
        }
        refreshClassifier()
    }

    private suspend fun refreshClassifier() {
        try {
            val c = withContext(Dispatchers.IO) { PythonBridge.classifierStatus() }
            _state.value = _state.value.copy(
                classifierAvailable = c.optBoolean("available", false),
                classifierParams = c.optInt("params", 0)
            )
        } catch (_: Exception) {
        }
    }

    /** Başlangıçta: durumu oku; zamanı geldiyse SADECE kontrol et. */
    private fun kickoffUpdateStatus() {
        viewModelScope.launch {
            try {
                val s = withContext(Dispatchers.IO) { PythonBridge.updateStatus() }
                val info = UpdateInfo.fromStatus(s)
                _state.value = _state.value.copy(update = info)
                if (info.progress.busy) {
                    pollUpdate()
                } else if (s.optBoolean("auto_check_due", false)) {
                    checkForUpdates(force = false)
                }
            } catch (_: Exception) {
            }
        }
    }

    // ---- Başlatma ----

    private fun bootstrap() {
        viewModelScope.launch {
            try {
                val info = withContext(Dispatchers.IO) {
                    PythonBridge.configure(getApplication())
                    PythonBridge.appInfo()
                }
                val clf = info.optJSONObject("classifier")
                _state.value = _state.value.copy(
                    ready = true,
                    error = null,
                    appName = info.optString("app_name", "AwuGöktürk"),
                    modelName = info.optString("model_name", "AwuGöktürk-Microcontroller:5K"),
                    slogan = info.optString("slogan", "NO SAY CAVAS"),
                    version = info.optString("version", "1.0.0"),
                    boards = parseBoards(info),
                    modulesCount = info.optJSONArray("modules")?.length() ?: 0,
                    categories = parseStrList(info.optJSONArray("categories")),
                    tools = parseTools(info.optJSONObject("tools")),
                    classifierAvailable = clf?.optBoolean("available", false) ?: false,
                    classifierParams = clf?.optInt("params", 0) ?: 0,
                    modelStatus = "çevrimdışı · cihazda çalışıyor"
                )
                // Model güncelleme durumunu oku; zamanı geldiyse yalnızca kontrol et.
                kickoffUpdateStatus()
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    ready = false,
                    modelStatus = "başlatılamadı",
                    error = e.message ?: "Python çalışma zamanı başlatılamadı."
                )
            }
        }
    }

    // ---- JSON yardımcıları ----

    private fun parseStrList(a: JSONArray?): List<String> {
        if (a == null) return emptyList()
        return (0 until a.length()).map { a.getString(it) }
    }

    private fun parseBoards(info: JSONObject): List<BoardOption> {
        val arr = info.optJSONArray("boards") ?: return emptyList()
        val out = mutableListOf<BoardOption>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val key = o.optString("key")
            val name = o.optString("name")
            val hint = when (key) {
                "arduino_uno" -> "Arduino Uno"
                "arduino_mega2560" -> "Arduino Mega 2560"
                "esp32" -> "Klasik ESP32 (Arduino)"
                else -> name
            }
            out.add(BoardOption(key, name, hint))
        }
        return out
    }

    private fun parseTools(o: JSONObject?): Map<String, Boolean> {
        if (o == null) return emptyMap()
        val m = mutableMapOf<String, Boolean>()
        val it = o.keys()
        while (it.hasNext()) {
            val k = it.next()
            m[k] = o.optBoolean(k, false)
        }
        return m
    }
}
