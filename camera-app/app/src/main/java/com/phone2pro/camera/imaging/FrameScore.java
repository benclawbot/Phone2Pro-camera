package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Normalized quality components used for transparent reference-frame selection. */
public final class FrameScore {
    private final double sharpness;
    private final double motionStability;
    private final double exposureQuality;
    private final double highlightRetention;
    private final double noiseQuality;
    private final double total;
    private final String explanation;

    public FrameScore(
            double sharpness,
            double motionStability,
            double exposureQuality,
            double highlightRetention,
            double noiseQuality,
            double total,
            String explanation
    ) {
        this.sharpness = normalized(sharpness, "sharpness");
        this.motionStability = normalized(motionStability, "motionStability");
        this.exposureQuality = normalized(exposureQuality, "exposureQuality");
        this.highlightRetention = normalized(highlightRetention, "highlightRetention");
        this.noiseQuality = normalized(noiseQuality, "noiseQuality");
        this.total = normalized(total, "total");
        this.explanation = Objects.requireNonNull(explanation, "explanation");
    }

    public double sharpness() { return sharpness; }
    public double motionStability() { return motionStability; }
    public double exposureQuality() { return exposureQuality; }
    public double highlightRetention() { return highlightRetention; }
    public double noiseQuality() { return noiseQuality; }
    public double total() { return total; }
    public String explanation() { return explanation; }

    private static double normalized(double value, String name) {
        if (!Double.isFinite(value) || value < 0.0 || value > 1.0) {
            throw new IllegalArgumentException(name + " must be finite and within [0, 1]");
        }
        return value;
    }
}
