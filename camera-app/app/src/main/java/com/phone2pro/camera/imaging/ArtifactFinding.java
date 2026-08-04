package com.phone2pro.camera.imaging;

import java.util.Objects;
import java.util.Optional;

/** One detected artefact with normalized severity and an optional local mask. */
public final class ArtifactFinding {
    private final ArtifactType type;
    private final double severity;
    private final ConfidenceMask affectedRegion;
    private final String evidence;

    public ArtifactFinding(
            ArtifactType type,
            double severity,
            ConfidenceMask affectedRegion,
            String evidence
    ) {
        this.type = Objects.requireNonNull(type, "type");
        if (!Double.isFinite(severity) || severity < 0.0 || severity > 1.0) {
            throw new IllegalArgumentException("severity must be finite and within [0, 1]");
        }
        this.severity = severity;
        this.affectedRegion = affectedRegion;
        this.evidence = Objects.requireNonNull(evidence, "evidence");
    }

    public ArtifactType type() { return type; }
    public double severity() { return severity; }
    public Optional<ConfidenceMask> affectedRegion() { return Optional.ofNullable(affectedRegion); }
    public String evidence() { return evidence; }
}
