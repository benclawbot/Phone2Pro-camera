package com.phone2pro.camera.capture;

import java.util.Objects;

/** Portable context supplied to backend-specific request modifiers. */
public final class CaptureRequestContext {
    private final CaptureSessionPlan sessionPlan;
    private final String captureId;
    private final String requestId;
    private final int sequenceIndex;
    private final CaptureRequestTemplate template;

    public CaptureRequestContext(
            CaptureSessionPlan sessionPlan,
            String captureId,
            String requestId,
            int sequenceIndex,
            CaptureRequestTemplate template
    ) {
        this.sessionPlan = Objects.requireNonNull(sessionPlan, "sessionPlan");
        this.captureId = requireText(captureId, "captureId");
        this.requestId = requireText(requestId, "requestId");
        if (sequenceIndex < 0) {
            throw new IllegalArgumentException("sequenceIndex must be non-negative");
        }
        this.sequenceIndex = sequenceIndex;
        this.template = Objects.requireNonNull(template, "template");
    }

    public CaptureSessionPlan sessionPlan() { return sessionPlan; }
    public String captureId() { return captureId; }
    public String requestId() { return requestId; }
    public int sequenceIndex() { return sequenceIndex; }
    public CaptureRequestTemplate template() { return template; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }
}
