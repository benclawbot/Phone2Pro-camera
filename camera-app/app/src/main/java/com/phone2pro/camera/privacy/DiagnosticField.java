package com.phone2pro.camera.privacy;

/** Fields that may appear in a structured diagnostic event. */
public enum DiagnosticField {
    EVENT_TYPE(false),
    TIMESTAMP(false),
    BUILD_FINGERPRINT(false),
    BACKEND_ID(false),
    ROUTE_ID(false),
    ERROR_CATEGORY(false),
    DURATION_MS(false),
    CAMERA_METADATA_VALUE(true),
    CONTENT_URI(true),
    FILE_PATH(true),
    LOCATION(true),
    IMAGE_BYTES(true),
    THUMBNAIL_BYTES(true),
    USER_TEXT(true),
    DEVICE_SERIAL(true);

    private final boolean sensitive;

    DiagnosticField(boolean sensitive) {
        this.sensitive = sensitive;
    }

    public boolean sensitive() {
        return sensitive;
    }
}
