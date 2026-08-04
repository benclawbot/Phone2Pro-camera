package com.phone2pro.camera.imaging;

/** Explicit color spaces used by the on-device rendering pipeline. */
public enum ColorSpace {
    /** Sensor-native linear values before color correction. */
    SENSOR_NATIVE(true),
    /** Scene-linear CIE XYZ referenced to D50. */
    CIE_XYZ_D50(true),
    /** Scene-linear sRGB primaries. */
    LINEAR_SRGB(true),
    /** Scene-linear Display P3 primaries. */
    LINEAR_DISPLAY_P3(true),
    /** Nonlinear sRGB output encoding. */
    SRGB(false),
    /** Nonlinear Display P3 output encoding. */
    DISPLAY_P3(false);

    private final boolean linear;

    ColorSpace(boolean linear) {
        this.linear = linear;
    }

    public boolean isLinear() {
        return linear;
    }
}
