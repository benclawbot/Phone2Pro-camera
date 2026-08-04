package com.phone2pro.camera.capture;

/** Stable failure categories used by the portable recovery policy. */
public enum TransientFailureCategory {
    REQUEST_TIMEOUT,
    CAPTURE_FAILED,
    SESSION_CONFIGURE_FAILED,
    CAMERA_DISCONNECTED,
    CAMERA_IN_USE,
    DEVICE_FATAL,
    PERMISSION_DENIED,
    UNSUPPORTED_CONFIGURATION
}
