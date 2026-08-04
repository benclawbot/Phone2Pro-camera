package com.phone2pro.camera.vendor;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** Enables vendor settings only after exact-build allowlisting and a verified probe. */
public final class VendorExtensionPlanner {
    private final Map<String, VendorFeaturePolicy> policies;
    private final PublicFallbackConfiguration fallback;

    public VendorExtensionPlanner(
            List<VendorFeaturePolicy> policies,
            PublicFallbackConfiguration fallback
    ) {
        Objects.requireNonNull(policies, "policies");
        this.fallback = Objects.requireNonNull(fallback, "fallback");
        this.policies = new LinkedHashMap<>();
        for (VendorFeaturePolicy policy : policies) {
            Objects.requireNonNull(policy, "policy");
            if (this.policies.put(policy.featureId(), policy) != null) {
                throw new IllegalArgumentException("duplicate feature policy: " + policy.featureId());
            }
        }
    }

    public VendorExtensionPlan plan(
            String featureId,
            VendorBuildIdentity currentBuild,
            VendorProbeResult probe
    ) {
        Objects.requireNonNull(featureId, "featureId");
        Objects.requireNonNull(currentBuild, "currentBuild");
        VendorFeaturePolicy policy = policies.get(featureId);
        if (policy == null) {
            return VendorExtensionPlan.fallback(
                    featureId,
                    fallback,
                    "No allowlisted vendor policy exists for this feature."
            );
        }
        if (!policy.allows(currentBuild)) {
            return VendorExtensionPlan.fallback(
                    featureId,
                    fallback,
                    "Current device build is not an exact member of the feature allowlist."
            );
        }
        if (probe == null) {
            return VendorExtensionPlan.fallback(
                    featureId,
                    fallback,
                    "No isolated probe result exists for the current build."
            );
        }
        if (!featureId.equals(probe.featureId())
                || !currentBuild.exactlyMatches(probe.build())) {
            return VendorExtensionPlan.fallback(
                    featureId,
                    fallback,
                    "Probe feature or build identity does not match the requested configuration."
            );
        }
        if (probe.status() != VendorProbeStatus.VERIFIED_SUPPORTED) {
            return VendorExtensionPlan.fallback(
                    featureId,
                    fallback,
                    "Probe did not verify effective support: " + probe.status() + "."
            );
        }
        return VendorExtensionPlan.enabled(
                policy,
                fallback,
                "Exact build allowlist and isolated effective probe both passed."
        );
    }
}
