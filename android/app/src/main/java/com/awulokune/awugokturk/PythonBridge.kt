package com.awulokune.awugokturk

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.io.File

/**
 * Kotlin <-> Python köprüsü (Chaquopy).
 *
 * İş mantığı Python `awa_agent` paketindedir; burada yalnızca JSON köprü vardır.
 * Böylece mevcut mimari korunur ve davranış iki dilde çatallanmaz.
 */
object PythonBridge {

    @Volatile
    private var ready = false

    @Synchronized
    fun configure(context: Context) {
        if (ready) return
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(context.applicationContext))
        }
        // 5K lite ağırlıklarını asset'ten çıkar (paket içi sürüm; referans kopya).
        val f = File(context.filesDir, "classifier5k.json")
        if (!f.exists()) {
            context.assets.open("classifier5k.json").use { input ->
                f.outputStream().use { out -> input.copyTo(out) }
            }
        }
        // Etkin modeli Python tarafı seçer: indirilmiş güncel sürüm geçerliyse o,
        // aksi hâlde paket içi model. Böylece yeniden başlatmada doğru model yüklenir.
        module().callAttr("configure_models", context.filesDir.absolutePath, f.absolutePath)
        ready = true
    }

    private fun module(): PyObject =
        Python.getInstance().getModule("awa_agent.android_bridge")

    fun appInfo(): JSONObject = JSONObject(module().callAttr("app_info").toString())

    fun classifierStatus(): JSONObject =
        JSONObject(module().callAttr("classifier_status").toString())

    fun handle(text: String, boardHint: String?): JSONObject =
        JSONObject(module().callAttr("handle", text, boardHint ?: "").toString())

    fun route(text: String): JSONObject =
        JSONObject(module().callAttr("route", text).toString())

    fun guardCheck(code: String, boardKey: String?): JSONObject =
        JSONObject(module().callAttr("guard_check", code, boardKey ?: "").toString())

    // ---- Model güncelleme (GitHub Releases) ----

    fun updateStatus(): JSONObject =
        JSONObject(module().callAttr("update_status").toString())

    /** Ağ isteği yapar; çağıran bunu IO dispatcher'ında çalıştırmalıdır. */
    fun updateCheck(force: Boolean): JSONObject =
        JSONObject(module().callAttr("update_check", force).toString())

    fun updateDownloadStart(): JSONObject =
        JSONObject(module().callAttr("update_download_start").toString())

    fun updateProgress(): JSONObject =
        JSONObject(module().callAttr("update_progress").toString())

    fun updateCancel(): JSONObject =
        JSONObject(module().callAttr("update_cancel").toString())

    fun updateRollback(): JSONObject =
        JSONObject(module().callAttr("update_rollback").toString())

    fun updateSetAuto(enabled: Boolean): JSONObject =
        JSONObject(module().callAttr("update_set_auto", enabled).toString())
}
