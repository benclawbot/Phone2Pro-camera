plugins {
    id("com.android.application")
}

android {
    namespace = "com.phone2pro.diagnostics"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.phone2pro.diagnostics"
        minSdk = 30
        targetSdk = 36
        versionCode = 7
        versionName = "0.7.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    lint {
        abortOnError = true
        warningsAsErrors = false
    }
}
