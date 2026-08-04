package com.phone2pro.camera.imaging;

/** Conservative recovery actions; detail is always sacrificed before naturalness. */
public enum FallbackAction {
    KEEP_RESULT,
    MASK_UNRELIABLE_REGIONS,
    DISABLE_SUPER_RESOLUTION,
    DISABLE_SHARPENING,
    REDUCE_DENOISE_STRENGTH,
    PROTECT_HIGHLIGHTS,
    USE_REFERENCE_FRAME_ONLY
}
