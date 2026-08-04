package com.phone2pro.camera.core;

import java.util.Objects;
import java.util.OptionalDouble;

/**
 * Describes a physical field-of-view target independently of any Camera2 ID.
 *
 * <p>Concrete endpoint IDs belong exclusively to backend route tables.</p>
 */
public final class OpticalRoute {
    private static final String STOCK_EXPERT_EVIDENCE =
            "Controlled stock Expert captures and the recovered Galaga manual route table.";

    public static final OpticalRoute ULTRAWIDE = new OpticalRoute(
            "ultrawide",
            "0.6×",
            LensIdentity.withUnknownAperture(
                    1.64f,
                    15,
                    EvidenceConfidence.VERIFIED,
                    STOCK_EXPERT_EVIDENCE + " Exact aperture value is not yet recorded."
            ),
            3264,
            2448
    );

    public static final OpticalRoute MAIN = new OpticalRoute(
            "main",
            "1×",
            LensIdentity.withUnknownAperture(
                    5.56f,
                    24,
                    EvidenceConfidence.VERIFIED,
                    STOCK_EXPERT_EVIDENCE + " Exact aperture value is not yet recorded."
            ),
            4080,
            3072
    );

    public static final OpticalRoute TELEPHOTO = new OpticalRoute(
            "telephoto",
            "2×",
            LensIdentity.withUnknownAperture(
                    7.10f,
                    50,
                    EvidenceConfidence.VERIFIED,
                    STOCK_EXPERT_EVIDENCE + " Exact aperture value is not yet recorded."
            ),
            4096,
            3072
    );

    private final String id;
    private final String label;
    private final LensIdentity lensIdentity;
    private final int verifiedWidth;
    private final int verifiedHeight;

    public OpticalRoute(
            String id,
            String label,
            LensIdentity lensIdentity,
            int verifiedWidth,
            int verifiedHeight
    ) {
        this.id = Objects.requireNonNull(id, "id");
        this.label = Objects.requireNonNull(label, "label");
        this.lensIdentity = Objects.requireNonNull(lensIdentity, "lensIdentity");
        if (verifiedWidth <= 0 || verifiedHeight <= 0) {
            throw new IllegalArgumentException("Verified dimensions must be positive");
        }
        this.verifiedWidth = verifiedWidth;
        this.verifiedHeight = verifiedHeight;
    }

    /** Compatibility constructor for callers without aperture evidence. */
    public OpticalRoute(
            String id,
            String label,
            float physicalFocalLengthMm,
            int equivalentFocalLengthMm,
            int verifiedWidth,
            int verifiedHeight
    ) {
        this(
                id,
                label,
                LensIdentity.withUnknownAperture(
                        physicalFocalLengthMm,
                        equivalentFocalLengthMm,
                        EvidenceConfidence.UNKNOWN,
                        "No evidence note was supplied by this caller."
                ),
                verifiedWidth,
                verifiedHeight
        );
    }

    public String id() {
        return id;
    }

    public String label() {
        return label;
    }

    public LensIdentity lensIdentity() {
        return lensIdentity;
    }

    public float physicalFocalLengthMm() {
        return lensIdentity.physicalFocalLengthMm();
    }

    public int equivalentFocalLengthMm() {
        return lensIdentity.equivalentFocalLengthMm();
    }

    public OptionalDouble aperture() {
        return lensIdentity.aperture();
    }

    public double cropFactor() {
        return lensIdentity.cropFactor();
    }

    public EvidenceConfidence confidence() {
        return lensIdentity.confidence();
    }

    public int verifiedWidth() {
        return verifiedWidth;
    }

    public int verifiedHeight() {
        return verifiedHeight;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof OpticalRoute)) {
            return false;
        }
        OpticalRoute route = (OpticalRoute) other;
        return id.equals(route.id);
    }

    @Override
    public int hashCode() {
        return id.hashCode();
    }

    @Override
    public String toString() {
        return label + " (" + equivalentFocalLengthMm() + " mm equivalent)";
    }
}
