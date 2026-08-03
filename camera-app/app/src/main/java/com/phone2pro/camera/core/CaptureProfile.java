package com.phone2pro.camera.core;

import androidx.camera.core.ImageCapture;

/** Product capture modes and their current single-frame bootstrap policy. */
public enum CaptureProfile {
    QUICK(
            "Quick",
            ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY,
            "Single-frame low-latency baseline"
    ),
    AUTO(
            "Auto",
            ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY,
            "Single-frame quality baseline; adaptive burst pipeline pending"
    ),
    MAX_DETAIL(
            "Max Detail",
            ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY,
            "Single-frame quality baseline; super-resolution pipeline pending"
    );

    private final String label;
    @ImageCapture.CaptureMode
    private final int imageCaptureMode;
    private final String implementationStatus;

    CaptureProfile(
            String label,
            @ImageCapture.CaptureMode int imageCaptureMode,
            String implementationStatus
    ) {
        this.label = label;
        this.imageCaptureMode = imageCaptureMode;
        this.implementationStatus = implementationStatus;
    }

    public String label() {
        return label;
    }

    @ImageCapture.CaptureMode
    public int imageCaptureMode() {
        return imageCaptureMode;
    }

    public String implementationStatus() {
        return implementationStatus;
    }
}
