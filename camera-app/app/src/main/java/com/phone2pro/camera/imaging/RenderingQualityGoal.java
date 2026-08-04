package com.phone2pro.camera.imaging;

/** Non-negotiable quality goals for the independent rendering pipeline. */
public enum RenderingQualityGoal {
    PRESERVE_NATURAL_COLOR,
    PRESERVE_HIGHLIGHT_DETAIL,
    PRESERVE_LOCAL_MOTION,
    AVOID_GHOSTING,
    AVOID_HALOS_AND_RINGING,
    AVOID_SYNTHETIC_TEXTURE,
    RETAIN_REAL_SENSOR_TEXTURE,
    PREFER_REFERENCE_FRAME_OVER_UNSTABLE_DETAIL
}
