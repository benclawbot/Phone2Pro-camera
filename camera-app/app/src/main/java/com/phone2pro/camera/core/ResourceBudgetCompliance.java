package com.phone2pro.camera.core;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Objects;
import java.util.Set;

/** Comparison of a measured capture against the effective resource budget. */
public final class ResourceBudgetCompliance {
    private final Set<ResourceBudgetViolation> violations;

    private ResourceBudgetCompliance(Set<ResourceBudgetViolation> violations) {
        this.violations = Collections.unmodifiableSet(
                violations.isEmpty()
                        ? EnumSet.noneOf(ResourceBudgetViolation.class)
                        : EnumSet.copyOf(violations)
        );
    }

    public static ResourceBudgetCompliance evaluate(
            CaptureResourceBudget budget,
            ResourcePerformanceSample sample
    ) {
        Objects.requireNonNull(budget, "budget");
        Objects.requireNonNull(sample, "sample");
        EnumSet<ResourceBudgetViolation> violations = EnumSet.noneOf(
                ResourceBudgetViolation.class
        );
        if (sample.frameCount() > budget.maxFrames()) {
            violations.add(ResourceBudgetViolation.FRAME_COUNT);
        }
        if (sample.peakInFlightBuffers() > budget.maxInFlightBuffers()) {
            violations.add(ResourceBudgetViolation.IN_FLIGHT_BUFFERS);
        }
        if (sample.peakWorkingSetBytes() > budget.maximumWorkingSetBytes()) {
            violations.add(ResourceBudgetViolation.WORKING_SET_MEMORY);
        }
        if (sample.queuedCaptures() > budget.maxQueuedCaptures()) {
            violations.add(ResourceBudgetViolation.QUEUE_DEPTH);
        }
        if (sample.shutterLatencyMs() > budget.shutterLatencyTargetMs()) {
            violations.add(ResourceBudgetViolation.SHUTTER_LATENCY);
        }
        if (sample.processingLatencyMs() > budget.processingLatencyTargetMs()) {
            violations.add(ResourceBudgetViolation.PROCESSING_LATENCY);
        }
        if (sample.capturesInLastMinute() > budget.sustainedCapturesPerMinute()) {
            violations.add(ResourceBudgetViolation.SUSTAINED_CAPTURE_RATE);
        }
        return new ResourceBudgetCompliance(violations);
    }

    public Set<ResourceBudgetViolation> violations() { return violations; }
    public boolean passes() { return violations.isEmpty(); }
}
