package com.awulokune.awugokturk

import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.awulokune.awugokturk.ui.AwuTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Kenardan kenara (edge-to-edge): sistem çubukları ve klavye yönetimi
        // Compose tarafında (insets) ele alınır.
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT)
        )
        setContent {
            val vm: AwuViewModel = viewModel()
            val state by vm.state.collectAsState()

            SideEffect {
                WindowCompat.getInsetsController(window, window.decorView).apply {
                    isAppearanceLightStatusBars = !state.themeDark
                    isAppearanceLightNavigationBars = !state.themeDark
                }
            }

            AwuTheme(koyu = state.themeDark) {
                AwuApp(state, vm)
            }
        }
    }
}

@Composable
private fun AwuApp(state: AppState, vm: AwuViewModel) {
    var tab by rememberSaveable { mutableStateOf(0) }

    // Klavye açıkken alt gezinmeyi gizle: mesaj alanı klavyenin hemen üstünde kalır.
    val imeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0

    // Model Güncellemeleri ekranı açıkken sistem geri tuşu bu ekranı kapatır.
    androidx.activity.compose.BackHandler(enabled = state.modelScreen) {
        vm.closeModelUpdates()
    }

    Scaffold(
        containerColor = androidx.compose.material3.MaterialTheme.colorScheme.background,
        // Sistem çubuklarını ekranlar kendileri yönetir (TopAppBar + imePadding).
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            if (!imeVisible && !state.modelScreen) {
                NavigationBar {
                    NavigationBarItem(
                        selected = tab == 0,
                        onClick = { tab = 0 },
                        icon = { Icon(painterResource(R.drawable.ic_tab_chat), contentDescription = "Sohbet") },
                        label = { Text("Sohbet") }
                    )
                    NavigationBarItem(
                        selected = tab == 1,
                        onClick = { tab = 1 },
                        icon = { Icon(painterResource(R.drawable.ic_tab_code), contentDescription = "Kod") },
                        label = { Text("Kod") }
                    )
                    NavigationBarItem(
                        selected = tab == 2,
                        onClick = { tab = 2 },
                        icon = { Icon(Icons.Filled.Settings, contentDescription = "Ayarlar") },
                        label = { Text("Ayarlar") }
                    )
                }
            }
        }
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding).imePadding()) {
            if (state.modelScreen) {
                com.awulokune.awugokturk.ui.ModelUpdateScreen(state, vm)
            } else {
                when (tab) {
                    0 -> com.awulokune.awugokturk.ui.ChatScreen(state, vm)
                    1 -> com.awulokune.awugokturk.ui.CodeScreen(state, vm)
                    else -> com.awulokune.awugokturk.ui.SettingsScreen(state, vm)
                }
            }
        }
    }
}
