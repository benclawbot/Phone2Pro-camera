package com.phone2pro.camera.imaging;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Aggregate artefact findings produced after any risky rendering stage. */
public final class ArtifactReport {
    private final RenderStage stage;
    private final List<ArtifactFinding> findings;

    public ArtifactReport(RenderStage stage, List<ArtifactFinding> findings) {
        this.stage = Objects.requireNonNull(stage, "stage");
        this.findings = Collections.unmodifiableList(
                new ArrayList<>(Objects.requireNonNull(findings, "findings"))
        );
    }

    public static ArtifactReport clean(RenderStage stage) {
        return new ArtifactReport(stage, Collections.emptyList());
    }

    public RenderStage stage() { return stage; }
    public List<ArtifactFinding> findings() { return findings; }

    public double maximumSeverity() {
        double maximum = 0.0;
        for (ArtifactFinding finding : findings) {
            maximum = Math.max(maximum, finding.severity());
        }
        return maximum;
    }

    public boolean contains(ArtifactType type, double minimumSeverity) {
        for (ArtifactFinding finding : findings) {
            if (finding.type() == type && finding.severity() >= minimumSeverity) {
                return true;
            }
        }
        return false;
    }
}
