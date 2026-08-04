package com.phone2pro.camera.diagnostics;

/** Read-only or bounded modules allowed when validating a new firmware build. */
public enum FirmwareValidationModule {
    PUBLIC_CAPABILITY_INVENTORY(true),
    CAMERA_OPEN_PROBE(true),
    STREAM_SESSION_MATRIX(true),
    REQUEST_TEMPLATE_INVENTORY(true),
    REDACTED_CAPTURE_TRACE(true),
    BOUNDED_BURST_BENCHMARK(true),
    VENDOR_KEY_INVENTORY(true),
    GUARDED_VENDOR_WRITE_PROBE(false),
    SYSTEM_CAMERA_OPEN_PROBE(false);

    private final boolean safeByDefault;

    FirmwareValidationModule(boolean safeByDefault) {
        this.safeByDefault = safeByDefault;
    }

    public boolean safeByDefault() { return safeByDefault; }
}
