package com.phone2pro.camera.imaging;

import java.util.Arrays;
import java.util.Objects;

/** Grid of local image-space displacement vectors with per-cell confidence. */
public final class MotionField {
    private final int width;
    private final int height;
    private final float[] deltaX;
    private final float[] deltaY;
    private final ConfidenceMask confidence;

    public MotionField(
            int width,
            int height,
            float[] deltaX,
            float[] deltaY,
            ConfidenceMask confidence
    ) {
        if (width <= 0 || height <= 0) {
            throw new IllegalArgumentException("motion field dimensions must be positive");
        }
        int count = Math.multiplyExact(width, height);
        if (deltaX == null || deltaY == null || deltaX.length != count || deltaY.length != count) {
            throw new IllegalArgumentException("motion vector count must match dimensions");
        }
        for (int index = 0; index < count; index++) {
            if (!Float.isFinite(deltaX[index]) || !Float.isFinite(deltaY[index])) {
                throw new IllegalArgumentException("motion vectors must be finite");
            }
        }
        this.confidence = Objects.requireNonNull(confidence, "confidence");
        if (confidence.width() != width || confidence.height() != height) {
            throw new IllegalArgumentException("confidence mask dimensions must match motion field");
        }
        this.width = width;
        this.height = height;
        this.deltaX = Arrays.copyOf(deltaX, count);
        this.deltaY = Arrays.copyOf(deltaY, count);
    }

    public int width() { return width; }
    public int height() { return height; }
    public ConfidenceMask confidence() { return confidence; }

    public float deltaXAt(int x, int y) { return deltaX[index(x, y)]; }
    public float deltaYAt(int x, int y) { return deltaY[index(x, y)]; }

    private int index(int x, int y) {
        if (x < 0 || x >= width || y < 0 || y >= height) {
            throw new IndexOutOfBoundsException("motion coordinate outside dimensions");
        }
        return y * width + x;
    }
}
