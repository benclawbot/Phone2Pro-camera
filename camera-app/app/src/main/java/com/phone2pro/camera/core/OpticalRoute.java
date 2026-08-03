package com.phone2pro.camera.core;

import java.util.Objects;

/**
 * Describes a physical field-of-view target independently of any Camera2 ID.
 *
 * <p>Concrete endpoint IDs belong exclusively to backend route tables.</p>
 */
public final class OpticalRoute {
    public static final OpticalRoute ULTRAWIDE = new OpticalRoute(
            "ultrawide",
            "0.6×",
            1.64f,
            15,
            3264,
            2448
    );

    public static final OpticalRoute MAIN = new OpticalRoute(
            "main",
            "1×",
            5.56f,
            24,
            4080,
            3072
    );

    public static final OpticalRoute TELEPHOTO = new OpticalRoute(
            "telephoto",
            "2×",
            7.10f,
            50,
            4096,
            3072
    );

    private final String id;
    private final String label;
    private final float physicalFocalLengthMm;
    private final int equivalentFocalLengthMm;
    private final int verifiedWidth;
    private final int verifiedHeight;

    public OpticalRoute(
            String id,
            String label,
            float physicalFocalLengthMm,
            int equivalentFocalLengthMm,
            int verifiedWidth,
            int verifiedHeight
    ) {
        this.id = Objects.requireNonNull(id, "id");
        this.label = Objects.requireNonNull(label, "label");
        this.physicalFocalLengthMm = physicalFocalLengthMm;
        this.equivalentFocalLengthMm = equivalentFocalLengthMm;
        this.verifiedWidth = verifiedWidth;
        this.verifiedHeight = verifiedHeight;
    }

    public String id() {
        return id;
    }

    public String label() {
        return label;
    }

    public float physicalFocalLengthMm() {
        return physicalFocalLengthMm;
    }

    public int equivalentFocalLengthMm() {
        return equivalentFocalLengthMm;
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
        return label + " (" + equivalentFocalLengthMm + " mm equivalent)";
    }
}
