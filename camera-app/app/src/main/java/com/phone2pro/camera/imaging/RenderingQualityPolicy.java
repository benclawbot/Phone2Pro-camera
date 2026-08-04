package com.phone2pro.camera.imaging;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Set;

/** Immutable mandatory quality goals shared by every product capture mode. */
public final class RenderingQualityPolicy {
    private final Set<RenderingQualityGoal> goals;
    private final double maximumAcceptedArtifactSeverity;

    public RenderingQualityPolicy(
            Set<RenderingQualityGoal> goals,
            double maximumAcceptedArtifactSeverity
    ) {
        if (goals == null || goals.isEmpty()) {
            throw new IllegalArgumentException("at least one rendering quality goal is required");
        }
        if (!Double.isFinite(maximumAcceptedArtifactSeverity)
                || maximumAcceptedArtifactSeverity < 0.0
                || maximumAcceptedArtifactSeverity > 1.0) {
            throw new IllegalArgumentException(
                    "maximumAcceptedArtifactSeverity must be within [0, 1]"
            );
        }
        this.goals = Collections.unmodifiableSet(EnumSet.copyOf(goals));
        this.maximumAcceptedArtifactSeverity = maximumAcceptedArtifactSeverity;
    }

    public static RenderingQualityPolicy naturalStill() {
        return new RenderingQualityPolicy(
                EnumSet.allOf(RenderingQualityGoal.class),
                0.35
        );
    }

    public Set<RenderingQualityGoal> goals() { return goals; }
    public double maximumAcceptedArtifactSeverity() {
        return maximumAcceptedArtifactSeverity;
    }

    public boolean accepts(ArtifactReport report) {
        return report.maximumSeverity() < maximumAcceptedArtifactSeverity;
    }
}
