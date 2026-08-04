package com.phone2pro.camera.vendor;

import java.util.Objects;
import java.util.Optional;

/** Vendor-enabled plan or explicit public fallback, never an implicit partial state. */
public final class VendorExtensionPlan {
    private final String featureId;
    private final VendorPlanOutcome outcome;
    private final VendorFeaturePolicy vendorPolicy;
    private final PublicFallbackConfiguration fallback;
    private final String reason;

    private VendorExtensionPlan(
            String featureId,
            VendorPlanOutcome outcome,
            VendorFeaturePolicy vendorPolicy,
            PublicFallbackConfiguration fallback,
            String reason
    ) {
        this.featureId = Objects.requireNonNull(featureId, "featureId");
        this.outcome = Objects.requireNonNull(outcome, "outcome");
        this.vendorPolicy = vendorPolicy;
        this.fallback = Objects.requireNonNull(fallback, "fallback");
        this.reason = Objects.requireNonNull(reason, "reason");
        if (outcome == VendorPlanOutcome.VENDOR_ENABLED && vendorPolicy == null) {
            throw new IllegalArgumentException("vendor-enabled plan requires a policy");
        }
        if (outcome == VendorPlanOutcome.PUBLIC_FALLBACK && vendorPolicy != null) {
            throw new IllegalArgumentException("fallback plan cannot carry active vendor settings");
        }
    }

    public static VendorExtensionPlan enabled(
            VendorFeaturePolicy policy,
            PublicFallbackConfiguration fallback,
            String reason
    ) {
        return new VendorExtensionPlan(
                policy.featureId(),
                VendorPlanOutcome.VENDOR_ENABLED,
                policy,
                fallback,
                reason
        );
    }

    public static VendorExtensionPlan fallback(
            String featureId,
            PublicFallbackConfiguration fallback,
            String reason
    ) {
        return new VendorExtensionPlan(
                featureId,
                VendorPlanOutcome.PUBLIC_FALLBACK,
                null,
                fallback,
                reason
        );
    }

    public String featureId() { return featureId; }
    public VendorPlanOutcome outcome() { return outcome; }
    public Optional<VendorFeaturePolicy> vendorPolicy() { return Optional.ofNullable(vendorPolicy); }
    public PublicFallbackConfiguration fallback() { return fallback; }
    public String reason() { return reason; }
}
