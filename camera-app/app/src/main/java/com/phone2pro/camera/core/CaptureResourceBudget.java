package com.phone2pro.camera.core;

import java.util.Objects;

/** Testable per-mode limits for capture, queueing and processing. */
public final class CaptureResourceBudget {
    private final CaptureProfile profile;
    private final int maxFrames;
    private final int maxInFlightBuffers;
    private final long maxFrameBytes;
    private final long maxIntermediateBytes;
    private final int maxQueuedCaptures;
    private final int shutterLatencyTargetMs;
    private final int processingLatencyTargetMs;
    private final int sustainedCapturesPerMinute;
    private final int cooldownAfterBurstMs;
    private final EvidenceConfidence confidence;

    public CaptureResourceBudget(
            CaptureProfile profile,
            int maxFrames,
            int maxInFlightBuffers,
            long maxFrameBytes,
            long maxIntermediateBytes,
            int maxQueuedCaptures,
            int shutterLatencyTargetMs,
            int processingLatencyTargetMs,
            int sustainedCapturesPerMinute,
            int cooldownAfterBurstMs,
            EvidenceConfidence confidence
    ) {
        this.profile = Objects.requireNonNull(profile, "profile");
        if (maxFrames <= 0 || maxInFlightBuffers <= 0 || maxFrameBytes <= 0
                || maxIntermediateBytes <= 0 || maxQueuedCaptures <= 0
                || shutterLatencyTargetMs <= 0 || processingLatencyTargetMs <= 0
                || sustainedCapturesPerMinute <= 0 || cooldownAfterBurstMs < 0) {
            throw new IllegalArgumentException("resource budget values are invalid");
        }
        if (maxInFlightBuffers < maxFrames) {
            throw new IllegalArgumentException("buffer budget must hold the planned burst");
        }
        this.maxFrames = maxFrames;
        this.maxInFlightBuffers = maxInFlightBuffers;
        this.maxFrameBytes = maxFrameBytes;
        this.maxIntermediateBytes = maxIntermediateBytes;
        this.maxQueuedCaptures = maxQueuedCaptures;
        this.shutterLatencyTargetMs = shutterLatencyTargetMs;
        this.processingLatencyTargetMs = processingLatencyTargetMs;
        this.sustainedCapturesPerMinute = sustainedCapturesPerMinute;
        this.cooldownAfterBurstMs = cooldownAfterBurstMs;
        this.confidence = Objects.requireNonNull(confidence, "confidence");
    }

    public CaptureProfile profile() { return profile; }
    public int maxFrames() { return maxFrames; }
    public int maxInFlightBuffers() { return maxInFlightBuffers; }
    public long maxFrameBytes() { return maxFrameBytes; }
    public long maxIntermediateBytes() { return maxIntermediateBytes; }
    public int maxQueuedCaptures() { return maxQueuedCaptures; }
    public int shutterLatencyTargetMs() { return shutterLatencyTargetMs; }
    public int processingLatencyTargetMs() { return processingLatencyTargetMs; }
    public int sustainedCapturesPerMinute() { return sustainedCapturesPerMinute; }
    public int cooldownAfterBurstMs() { return cooldownAfterBurstMs; }
    public EvidenceConfidence confidence() { return confidence; }

    public long maximumWorkingSetBytes() {
        return Math.addExact(
                Math.multiplyExact(maxFrameBytes, maxInFlightBuffers),
                maxIntermediateBytes
        );
    }
}
