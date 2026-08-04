package com.phone2pro.camera.ui;

/** Display-relative orientation used by preview and JPEG controls. */
public enum PreviewOrientation {
    PORTRAIT_0(0),
    LANDSCAPE_90(90),
    PORTRAIT_180(180),
    LANDSCAPE_270(270);

    private final int clockwiseDegrees;

    PreviewOrientation(int clockwiseDegrees) {
        this.clockwiseDegrees = clockwiseDegrees;
    }

    public int clockwiseDegrees() {
        return clockwiseDegrees;
    }

    public static PreviewOrientation fromClockwiseDegrees(int degrees) {
        int normalized = ((degrees % 360) + 360) % 360;
        switch (normalized) {
            case 0:
                return PORTRAIT_0;
            case 90:
                return LANDSCAPE_90;
            case 180:
                return PORTRAIT_180;
            case 270:
                return LANDSCAPE_270;
            default:
                throw new IllegalArgumentException("orientation must be a multiple of 90 degrees");
        }
    }
}
