package com.phone2pro.camera.diagnostics;

import com.phone2pro.camera.core.EvidenceConfidence;

import java.util.Objects;

/** One feature decision with build/capability evidence. */
public final class FeatureFlagReport {
    private final String featureId;
    private final FeatureFlagState state;
    private final EvidenceConfidence confidence;
    private final String reason;

    public FeatureFlagReport(
            String featureId,
            FeatureFlagState state,
            EvidenceConfidence confidence,
            String reason
    ) {
        this.featureId = requireText(featureId, "featureId");
        this.state = Objects.requireNonNull(state, "state");
        this.confidence = Objects.requireNonNull(confidence, "confidence");
        this.reason = requireText(reason, "reason");
        if (state == FeatureFlagState.ENABLED && confidence == EvidenceConfidence.UNKNOWN) {
            throw new IllegalArgumentException("enabled feature cannot have UNKNOWN confidence");
        }
    }

    public String featureId() { return featureId; }
    public FeatureFlagState state() { return state; }
    public EvidenceConfidence confidence() { return confidence; }
    public String reason() { return reason; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
