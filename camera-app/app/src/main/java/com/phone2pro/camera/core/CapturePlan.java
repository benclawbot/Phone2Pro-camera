package com.phone2pro.camera.core;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Objects;
import java.util.Set;

/** Immutable, deterministic work plan derived before capture begins. */
public final class CapturePlan {
    private final CaptureProfile requestedProfile;
    private final CaptureProfile effectiveProfile;
    private final int frameCount;
    private final ExposureStrategy exposureStrategy;
    private final Set<CaptureStage> stages;
    private final Set<RenderingConstraint> renderingConstraints;
    private final Set<DegradationReason> degradationReasons;
    private final int shutterLatencyTargetMs;
    private final int processingLatencyTargetMs;
    private final EvidenceConfidence latencyConfidence;
    private final String userSummary;

    public CapturePlan(
            CaptureProfile requestedProfile,
            CaptureProfile effectiveProfile,
            int frameCount,
            ExposureStrategy exposureStrategy,
            Set<CaptureStage> stages,
            Set<RenderingConstraint> renderingConstraints,
            Set<DegradationReason> degradationReasons,
            int shutterLatencyTargetMs,
            int processingLatencyTargetMs,
            EvidenceConfidence latencyConfidence,
            String userSummary
    ) {
        this.requestedProfile = Objects.requireNonNull(requestedProfile, "requestedProfile");
        this.effectiveProfile = Objects.requireNonNull(effectiveProfile, "effectiveProfile");
        if (frameCount <= 0) {
            throw new IllegalArgumentException("frameCount must be positive");
        }
        this.frameCount = frameCount;
        this.exposureStrategy = Objects.requireNonNull(exposureStrategy, "exposureStrategy");
        this.stages = immutableEnumSet(stages, CaptureStage.class, "stages");
        this.renderingConstraints = immutableEnumSet(
                renderingConstraints,
                RenderingConstraint.class,
                "renderingConstraints"
        );
        this.degradationReasons = immutableEnumSet(
                degradationReasons,
                DegradationReason.class,
                "degradationReasons"
        );
        if (shutterLatencyTargetMs <= 0 || processingLatencyTargetMs <= 0) {
            throw new IllegalArgumentException("Latency targets must be positive");
        }
        this.shutterLatencyTargetMs = shutterLatencyTargetMs;
        this.processingLatencyTargetMs = processingLatencyTargetMs;
        this.latencyConfidence = Objects.requireNonNull(latencyConfidence, "latencyConfidence");
        this.userSummary = Objects.requireNonNull(userSummary, "userSummary");
    }

    private static <E extends Enum<E>> Set<E> immutableEnumSet(
            Set<E> values,
            Class<E> type,
            String name
    ) {
        Objects.requireNonNull(values, name);
        EnumSet<E> copy = values.isEmpty()
                ? EnumSet.noneOf(type)
                : EnumSet.copyOf(values);
        return Collections.unmodifiableSet(copy);
    }

    public CaptureProfile requestedProfile() {
        return requestedProfile;
    }

    public CaptureProfile effectiveProfile() {
        return effectiveProfile;
    }

    public int frameCount() {
        return frameCount;
    }

    public ExposureStrategy exposureStrategy() {
        return exposureStrategy;
    }

    public Set<CaptureStage> stages() {
        return stages;
    }

    public Set<RenderingConstraint> renderingConstraints() {
        return renderingConstraints;
    }

    public Set<DegradationReason> degradationReasons() {
        return degradationReasons;
    }

    public boolean isDegraded() {
        return requestedProfile != effectiveProfile || !degradationReasons.isEmpty();
    }

    public int shutterLatencyTargetMs() {
        return shutterLatencyTargetMs;
    }

    public int processingLatencyTargetMs() {
        return processingLatencyTargetMs;
    }

    public EvidenceConfidence latencyConfidence() {
        return latencyConfidence;
    }

    public String userSummary() {
        return userSummary;
    }
}
