package com.phone2pro.camera.vendor;

import com.phone2pro.camera.core.EvidenceConfidence;

import java.util.Objects;

/** Build-scoped result from an isolated vendor-feature probe. */
public final class VendorProbeResult {
    private final String featureId;
    private final VendorBuildIdentity build;
    private final VendorProbeStatus status;
    private final EvidenceConfidence confidence;
    private final String evidence;

    public VendorProbeResult(
            String featureId,
            VendorBuildIdentity build,
            VendorProbeStatus status,
            EvidenceConfidence confidence,
            String evidence
    ) {
        this.featureId = requireText(featureId, "featureId");
        this.build = Objects.requireNonNull(build, "build");
        this.status = Objects.requireNonNull(status, "status");
        this.confidence = Objects.requireNonNull(confidence, "confidence");
        this.evidence = requireText(evidence, "evidence");
        if (status == VendorProbeStatus.VERIFIED_SUPPORTED
                && confidence != EvidenceConfidence.VERIFIED) {
            throw new IllegalArgumentException(
                    "VERIFIED_SUPPORTED requires VERIFIED evidence confidence"
            );
        }
    }

    public String featureId() { return featureId; }
    public VendorBuildIdentity build() { return build; }
    public VendorProbeStatus status() { return status; }
    public EvidenceConfidence confidence() { return confidence; }
    public String evidence() { return evidence; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
