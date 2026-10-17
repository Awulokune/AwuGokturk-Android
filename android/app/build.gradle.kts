// AwuGöktürk — uygulama modülü
//
// MİMARİ NOTU (dürüstlük):
//   Mevcut Python ajanı (`awa_agent/`) burada TEKRAR YAZILMAZ. Chaquopy ile
//   cihaz üzerinde (çevrimdışı) çalıştırılır ve Kotlin bir JSON köprüsüyle
//   konuşur. Böylece mevcut mimari korunur ve davranış sapması riski azalır.
//   5K modeli torch olmadan, JSON ağırlıklardan saf Python ile çalışır.
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

val buildPy: String? = (project.findProperty("buildPython") as String?)
    ?: System.getenv("AWU_BUILD_PYTHON")

android {
    namespace = "com.awulokune.awugokturk"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.awulokune.awugokturk"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
        // APK boyutunu ve derleme süresini sınırlamak için iki ABI (telefon + emülatör).
        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources.excludes += setOf("/META-INF/{AL2.0,LGPL2.1}")
    }

    // Üretilen APK adı sabit olsun (teslimat kolaylığı).
    applicationVariants.all {
        outputs.all {
            (this as? com.android.build.gradle.internal.api.BaseVariantOutputImpl)
                ?.outputFileName = "AwuGokturk-${name}.apk"
        }
    }
}

// Python paketini (embedded_agent/awa_agent) derleme dizinine kopyala.
// Kaynak: gerçek paket (tek doğruluk kaynağı). Kopya build/ altında üretilir.
val copyPython = tasks.register<Copy>("copyPython") {
    from(rootProject.file("../awa_agent"))
    into(layout.buildDirectory.dir("generated/python/awa_agent"))
    exclude("__pycache__/**", "**/*.pyc")
}

chaquopy {
    defaultConfig {
        // Hedef Python sürümü. F-Droid derleme sunucusu Debian trixie olduğu
        // için varsayılan python3 = 3.13'tür; bu sürüm onunla eşleşir.
        //
        // ÖNEMLİ (dürüstlük): Chaquopy, derleme Python'unun "magic number"ını
        // bu sürümle karşılaştırır ve uyuşmazsa derlemeyi DURDURUR
        // (bkz. chaquopy/pyc.py). Yani build makinesindeki python3 ile buradaki
        // sürüm AYNI minor sürüm olmalıdır. 3.13 -> magic 3571.
        version = "3.13"
        if (buildPy != null) {
            buildPython = listOf(buildPy)
        } else {
            // F-Droid / CI: PATH'teki python3 kullanılır (trixie'de 3.13).
            buildPython("python3")
        }
    }
    sourceSets {
        getByName("main") {
            srcDir(layout.buildDirectory.dir("generated/python"))
        }
    }
}

// Chaquopy, python dosyalarını paketlemeden önce kopyanın hazır olmasını garantile.
tasks.named("preBuild") { dependsOn(copyPython) }
tasks.matching { it.name.contains("Python") && it.name != "copyPython" }
    .configureEach { dependsOn(copyPython) }

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.2")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    implementation(platform("androidx.compose:compose-bom:2024.06.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
