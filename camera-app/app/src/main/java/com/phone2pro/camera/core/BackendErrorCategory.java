package com.phone2pro.camera.core;

/** Stable backend failure contract mapped later to user-facing errors. */
public enum BackendErrorCategory {
    UNSUPPORTED,
    PERMISSION,
    DISCONNECTED,
    IN_USE,
    MAX_CAMERAS,
    CONFIGURATION,
    REQUEST,
    TIMEOUT,
    THERMAL,
    RESOURCE,
    DEVICE,
    SERVICE,
    INTERNAL
}
