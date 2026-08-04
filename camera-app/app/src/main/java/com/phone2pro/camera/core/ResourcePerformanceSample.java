package com.phone2pro.camera.core;

/** One measured capture used to compare runtime behavior with an effective budget. */
public final class ResourcePerformanceSample {
    private final int frameCount;
    private final int peakInFlightBuffers;
    private final long peakWorkingSetBytes;
    private final int queuedCaptures;
    private final int shutterLatencyMs;
    private final int processingLatencyMs;
    private final int capturesInLastMinute;

    public ResourcePerformanceSample(
            int frameCount,
            int peakInFlightBuffers,
            long peakWorkingSetBytes,
            int queuedCaptures,
            int shutterLatencyMs,
            int processingLatencyMs,
            int capturesInLastMinute
    ) {
        if (frameCount <= 0 || peakInFlightBuffers <= 0 || peakWorkingSetBytes < 0
                || queuedCaptures < 0 || shutterLatencyMs < 0 || processingLatencyMs < 0
                || capturesInLastMinute < 0) {
            throw new IllegalArgumentException("performance sample values are invalid");
        }
        this.frameCount = frameCount;
        this.peakInFlightBuffers = peakInFlightBuffers;
        this.peakWorkingSetBytes = peakWorkingSetBytes;
        this.queuedCaptures = queuedCaptures;
        this.shutterLatencyMs = shutterLatencyMs;
        this.processingLatencyMs = processingLatencyMs;
        this.capturesInLastMinute = capturesInLastMinute;
    }

    public int frameCount() { return frameCount; }
    public int peakInFlightBuffers() { return peakInFlightBuffers; }
    public long peakWorkingSetBytes() { return peakWorkingSetBytes; }
    public int queuedCaptures() { return queuedCaptures; }
    public int shutterLatencyMs() { return shutterLatencyMs; }
    public int processingLatencyMs() { return processingLatencyMs; }
    public int capturesInLastMinute() { return capturesInLastMinute; }
}
