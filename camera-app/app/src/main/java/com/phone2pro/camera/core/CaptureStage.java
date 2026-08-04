package com.phone2pro.camera.core;

/** Modular on-device stages that may be selected by a capture plan. */
public enum CaptureStage {
    FRAME_SCORING,
    MOTION_ESTIMATION,
    ALIGNMENT,
    HDR_MERGE,
    DENOISE,
    SUPER_RESOLUTION,
    SHARPENING,
    COLOR_RENDERING,
    TONE_MAPPING,
    JPEG_ENCODING
}
