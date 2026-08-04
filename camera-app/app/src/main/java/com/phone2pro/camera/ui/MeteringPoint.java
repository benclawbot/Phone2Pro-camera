package com.phone2pro.camera.ui;

/** Preview-normalized focus/metering point in the closed range [0, 1]. */
public final class MeteringPoint {
    private final float x;
    private final float y;

    public MeteringPoint(float x, float y) {
        if (!Float.isFinite(x) || !Float.isFinite(y)
                || x < 0.0f || x > 1.0f || y < 0.0f || y > 1.0f) {
            throw new IllegalArgumentException("metering coordinates must be within [0, 1]");
        }
        this.x = x;
        this.y = y;
    }

    public float x() { return x; }
    public float y() { return y; }
}
