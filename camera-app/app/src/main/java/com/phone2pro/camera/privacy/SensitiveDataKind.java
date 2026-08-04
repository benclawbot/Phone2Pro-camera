package com.phone2pro.camera.privacy;

/** Sensitive data classes with independently enforced retention and diagnostic rules. */
public enum SensitiveDataKind {
    PREVIEW_FRAME,
    CAPTURE_FRAME,
    PROCESSING_INTERMEDIATE,
    FINAL_IMAGE,
    LOCATION,
    CAMERA_METADATA,
    DEVICE_IDENTITY,
    DIAGNOSTIC_EVENT,
    CRASH_CONTEXT
}
