package com.phone2pro.camera.imaging;

import java.util.Arrays;
import java.util.Objects;

/** Global and local alignment output for one candidate frame relative to a reference. */
public final class AlignmentResult {
    private final String referenceFrameId;
    private final String candidateFrameId;
    private final int pyramidLevelsUsed;
    private final double[] globalTransform3x3;
    private final MotionField localMotion;
    private final ConfidenceMask alignmentConfidence;
    private final ConfidenceMask validityMask;
    private final double residualErrorPixels;

    public AlignmentResult(
            String referenceFrameId,
            String candidateFrameId,
            int pyramidLevelsUsed,
            double[] globalTransform3x3,
            MotionField localMotion,
            ConfidenceMask alignmentConfidence,
            ConfidenceMask validityMask,
            double residualErrorPixels
    ) {
        this.referenceFrameId = Objects.requireNonNull(referenceFrameId, "referenceFrameId");
        this.candidateFrameId = Objects.requireNonNull(candidateFrameId, "candidateFrameId");
        if (pyramidLevelsUsed <= 0) {
            throw new IllegalArgumentException("pyramidLevelsUsed must be positive");
        }
        if (globalTransform3x3 == null || globalTransform3x3.length != 9) {
            throw new IllegalArgumentException("globalTransform3x3 must contain nine values");
        }
        for (double value : globalTransform3x3) {
            if (!Double.isFinite(value)) {
                throw new IllegalArgumentException("global transform values must be finite");
            }
        }
        this.localMotion = Objects.requireNonNull(localMotion, "localMotion");
        this.alignmentConfidence = Objects.requireNonNull(
                alignmentConfidence,
                "alignmentConfidence"
        );
        this.validityMask = Objects.requireNonNull(validityMask, "validityMask");
        if (alignmentConfidence.width() != localMotion.width()
                || alignmentConfidence.height() != localMotion.height()
                || validityMask.width() != localMotion.width()
                || validityMask.height() != localMotion.height()) {
            throw new IllegalArgumentException("all local alignment grids must share dimensions");
        }
        if (!Double.isFinite(residualErrorPixels) || residualErrorPixels < 0.0) {
            throw new IllegalArgumentException("residualErrorPixels must be finite and non-negative");
        }
        this.pyramidLevelsUsed = pyramidLevelsUsed;
        this.globalTransform3x3 = Arrays.copyOf(globalTransform3x3, 9);
        this.residualErrorPixels = residualErrorPixels;
    }

    public String referenceFrameId() { return referenceFrameId; }
    public String candidateFrameId() { return candidateFrameId; }
    public int pyramidLevelsUsed() { return pyramidLevelsUsed; }
    public double[] copyGlobalTransform3x3() { return Arrays.copyOf(globalTransform3x3, 9); }
    public MotionField localMotion() { return localMotion; }
    public ConfidenceMask alignmentConfidence() { return alignmentConfidence; }
    public ConfidenceMask validityMask() { return validityMask; }
    public double residualErrorPixels() { return residualErrorPixels; }
}
