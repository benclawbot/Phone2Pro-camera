package com.phone2pro.camera.imaging;

/** Tunable, implementation-neutral requirements for one frame alignment. */
public final class AlignmentRequest {
    private final int pyramidLevels;
    private final float maximumDisplacementPixels;
    private final boolean useMotionPrior;
    private final float minimumConfidence;

    public AlignmentRequest(
            int pyramidLevels,
            float maximumDisplacementPixels,
            boolean useMotionPrior,
            float minimumConfidence
    ) {
        if (pyramidLevels <= 0) {
            throw new IllegalArgumentException("pyramidLevels must be positive");
        }
        if (!(maximumDisplacementPixels >= 0.0f) || !Float.isFinite(maximumDisplacementPixels)) {
            throw new IllegalArgumentException("maximumDisplacementPixels must be finite and non-negative");
        }
        if (!Float.isFinite(minimumConfidence)
                || minimumConfidence < 0.0f
                || minimumConfidence > 1.0f) {
            throw new IllegalArgumentException("minimumConfidence must be within [0, 1]");
        }
        this.pyramidLevels = pyramidLevels;
        this.maximumDisplacementPixels = maximumDisplacementPixels;
        this.useMotionPrior = useMotionPrior;
        this.minimumConfidence = minimumConfidence;
    }

    public int pyramidLevels() { return pyramidLevels; }
    public float maximumDisplacementPixels() { return maximumDisplacementPixels; }
    public boolean useMotionPrior() { return useMotionPrior; }
    public float minimumConfidence() { return minimumConfidence; }
}
