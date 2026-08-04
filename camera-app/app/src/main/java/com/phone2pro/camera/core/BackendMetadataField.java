package com.phone2pro.camera.core;

/** Metadata that every backend must normalize when the native source provides it. */
public enum BackendMetadataField {
    FRAME_NUMBER,
    SENSOR_TIMESTAMP,
    EXPOSURE_TIME,
    SENSITIVITY_ISO,
    FRAME_DURATION,
    FOCUS_DISTANCE,
    FOCAL_LENGTH,
    APERTURE,
    WHITE_BALANCE,
    CROP_REGION,
    ACTIVE_ROUTE,
    ACTIVE_PHYSICAL_ID,
    ORIENTATION,
    ERROR_CATEGORY
}
