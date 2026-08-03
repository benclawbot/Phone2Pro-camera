plugins {
    id("com.android.application")
}

android {
    namespace = "com.phone2pro.camera"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.phone2pro.camera"
        minSdk = 30
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
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

    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

dependencies {
    val cameraXVersion = "1.6.1"

    implementation("androidx.activity:activity:1.13.0")
    implementation("androidx.camera:camera-core:$cameraXVersion")
    implementation("androidx.camera:camera-camera2:$cameraXVersion")
    implementation("androidx.camera:camera-lifecycle:$cameraXVersion")
    implementation("androidx.camera:camera-view:$cameraXVersion")

    testImplementation("junit:junit:4.13.2")
}
