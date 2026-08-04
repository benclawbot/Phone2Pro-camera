package com.phone2pro.camera.diagnostics;

/** Stable user-visible error categories, independent from backend exception classes. */
public enum UserErrorCategory {
    HARDWARE_UNAVAILABLE,
    PERMISSION_DENIED,
    THERMAL_LIMIT,
    UNSUPPORTED_FEATURE,
    RESOURCE_LIMIT,
    SESSION_FAILURE,
    CAPTURE_FAILURE,
    STORAGE_FAILURE,
    PROCESSING_FAILURE,
    INTERNAL_ERROR
}
