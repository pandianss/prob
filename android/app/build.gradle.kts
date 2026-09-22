plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

android {
    namespace = "com.probanker"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.probanker"
        // The target user is on a mid-range handset, not a flagship
        // (BLUEPRINT.md 8), and P0 runs no on-device inference - so nothing
        // here needs a modern platform except variable-font support, which
        // starts at 26. In 2026 that floor is a nine-year-old device.
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
        // Room/kotlinx-datetime style APIs on minSdk 24
        isCoreLibraryDesugaringEnabled = false
    }
    buildFeatures { compose = true }

    // AGP 9 provides Kotlin itself; jvmTarget moves here.
    kotlin {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
        }
    }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }

    testOptions {
        unitTests.all {
            // Gradle 9 defaults to the JUnit Platform, so JUnit 4 tests are
            // silently not discovered - the task succeeds having run nothing,
            // which is worse than failing.
            it.useJUnit()
            it.testLogging { events("passed", "failed", "skipped") }
        }
    }
}

ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.graphics)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.material3)
    debugImplementation(libs.compose.ui.tooling)

    implementation(libs.androidx.navigation.compose)

    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    implementation(libs.androidx.datastore.preferences)
    implementation(libs.androidx.work.runtime.ktx)

    implementation(libs.hilt.android)
    implementation(libs.hilt.navigation.compose)
    ksp(libs.hilt.compiler)

    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)

    // No networking dependency, deliberately. P0 runs no model in a learner
    // session (BLUEPRINT.md 2.3) and the content pack ships in assets, so the
    // app has nothing to call. Adding Retrofit here would be the first step
    // back towards a runtime that can be wrong.

    testImplementation(libs.junit)
    // org.json for the golden-vector test; Android ships a stub of it, so the
    // JVM test source set needs the real implementation.
    testImplementation("org.json:json:20240303")
    testImplementation(libs.kotlinx.coroutines.test)
}
