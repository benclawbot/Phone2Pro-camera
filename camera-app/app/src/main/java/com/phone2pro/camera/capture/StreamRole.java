package com.phone2pro.camera.capture;

/** Semantic stream role independent from Android Surface and ImageReader objects. */
public enum StreamRole {
    PREVIEW,
    STILL_JPEG,
    STILL_YUV,
    RAW,
    POSTVIEW,
    ANALYSIS,
    VIDEO,
    REPROCESS_INPUT
}
