package com.phone2pro.camera.core;

import java.util.Objects;
import java.util.OptionalDouble;

/** Evidence-backed optical identity for one field-of-view route. */
public final class LensIdentity {
    private final float physicalFocalLengthMm;
    private final int equivalentFocalLengthMm;
    private final OptionalDouble aperture;
    private final double cropFactor;
    private final EvidenceConfidence geometryConfidence;
    private final EvidenceConfidence apertureConfidence;
    private final String evidence;

    public LensIdentity(
            float physicalFocalLengthMm,
            int equivalentFocalLengthMm,
            OptionalDouble aperture,
            EvidenceConfidence geometryConfidence,
            EvidenceConfidence apertureConfidence,
            String evidence
    ) {
        if (!(physicalFocalLengthMm > 0.0f) || !Float.isFinite(physicalFocalLengthMm)) {
            throw new IllegalArgumentException("physicalFocalLengthMm must be finite and positive");
        }
        if (equivalentFocalLengthMm <= 0) {
            throw new IllegalArgumentException("equivalentFocalLengthMm must be positive");
        }
        this.aperture = Objects.requireNonNull(aperture, "aperture");
        if (aperture.isPresent()
                && (!(aperture.getAsDouble() > 0.0) || !Double.isFinite(aperture.getAsDouble()))) {
            throw new IllegalArgumentException("aperture must be finite and positive when present");
        }
        this.geometryConfidence = Objects.requireNonNull(
                geometryConfidence,
                "geometryConfidence"
        );
        this.apertureConfidence = Objects.requireNonNull(
                apertureConfidence,
                "apertureConfidence"
        );
        if (!aperture.isPresent() && apertureConfidence != EvidenceConfidence.UNKNOWN) {
            throw new IllegalArgumentException(
                    "Missing aperture must retain UNKNOWN confidence"
            );
        }
        this.physicalFocalLengthMm = physicalFocalLengthMm;
        this.equivalentFocalLengthMm = equivalentFocalLengthMm;
        this.cropFactor = equivalentFocalLengthMm / (double) physicalFocalLengthMm;
        this.evidence = Objects.requireNonNull(evidence, "evidence");
    }

    public static LensIdentity withUnknownAperture(
            float physicalFocalLengthMm,
            int equivalentFocalLengthMm,
            EvidenceConfidence geometryConfidence,
            String evidence
    ) {
        return new LensIdentity(
                physicalFocalLengthMm,
                equivalentFocalLengthMm,
                OptionalDouble.empty(),
                geometryConfidence,
                EvidenceConfidence.UNKNOWN,
                evidence
        );
    }

    public float physicalFocalLengthMm() {
        return physicalFocalLengthMm;
    }

    public int equivalentFocalLengthMm() {
        return equivalentFocalLengthMm;
    }

    public OptionalDouble aperture() {
        return aperture;
    }

    public double cropFactor() {
        return cropFactor;
    }

    public EvidenceConfidence geometryConfidence() {
        return geometryConfidence;
    }

    public EvidenceConfidence apertureConfidence() {
        return apertureConfidence;
    }

    public EvidenceConfidence confidence() {
        if (geometryConfidence == EvidenceConfidence.UNKNOWN
                && apertureConfidence == EvidenceConfidence.UNKNOWN) {
            return EvidenceConfidence.UNKNOWN;
        }
        if (geometryConfidence == EvidenceConfidence.HYPOTHESIS
                || apertureConfidence == EvidenceConfidence.HYPOTHESIS) {
            return EvidenceConfidence.HYPOTHESIS;
        }
        if (geometryConfidence == EvidenceConfidence.VERIFIED
                && apertureConfidence == EvidenceConfidence.VERIFIED) {
            return EvidenceConfidence.VERIFIED;
        }
        return EvidenceConfidence.PARTIALLY_VERIFIED;
    }

    public String evidence() {
        return evidence;
    }
}
