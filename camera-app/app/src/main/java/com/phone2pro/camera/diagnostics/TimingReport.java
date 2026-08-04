package com.phone2pro.camera.diagnostics;

/** Monotonic durations for one capture transaction. */
public final class TimingReport {
    private final long routeResolutionMs;
    private final long sessionConfigurationMs;
    private final long shutterMs;
    private final long imageAvailableMs;
    private final long processingMs;
    private final long persistenceMs;

    public TimingReport(
            long routeResolutionMs,
            long sessionConfigurationMs,
            long shutterMs,
            long imageAvailableMs,
            long processingMs,
            long persistenceMs
    ) {
        if (routeResolutionMs < 0 || sessionConfigurationMs < 0 || shutterMs < 0
                || imageAvailableMs < 0 || processingMs < 0 || persistenceMs < 0) {
            throw new IllegalArgumentException("timings must be non-negative");
        }
        this.routeResolutionMs = routeResolutionMs;
        this.sessionConfigurationMs = sessionConfigurationMs;
        this.shutterMs = shutterMs;
        this.imageAvailableMs = imageAvailableMs;
        this.processingMs = processingMs;
        this.persistenceMs = persistenceMs;
    }

    public long routeResolutionMs() { return routeResolutionMs; }
    public long sessionConfigurationMs() { return sessionConfigurationMs; }
    public long shutterMs() { return shutterMs; }
    public long imageAvailableMs() { return imageAvailableMs; }
    public long processingMs() { return processingMs; }
    public long persistenceMs() { return persistenceMs; }

    public long totalMs() {
        return Math.addExact(
                Math.addExact(routeResolutionMs, sessionConfigurationMs),
                Math.addExact(
                        Math.addExact(shutterMs, imageAvailableMs),
                        Math.addExact(processingMs, persistenceMs)
                )
        );
    }
}
