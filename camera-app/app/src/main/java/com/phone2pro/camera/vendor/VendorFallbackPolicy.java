package com.phone2pro.camera.vendor;

import java.util.Objects;

/** Converts every non-verified runtime outcome into the known public configuration. */
public final class VendorFallbackPolicy {
    public VendorRuntimeDecision decide(
            VendorExtensionPlan plan,
            VendorExecutionResult result
    ) {
        Objects.requireNonNull(plan, "plan");
        if (plan.outcome() == VendorPlanOutcome.PUBLIC_FALLBACK) {
            return VendorRuntimeDecision.fallback(plan.fallback(), plan.reason());
        }
        Objects.requireNonNull(result, "result");
        VendorFeaturePolicy policy = plan.vendorPolicy().orElseThrow(
                () -> new IllegalStateException("vendor-enabled plan has no policy")
        );
        if (result.elapsedMillis() > policy.timeoutMillis()) {
            return VendorRuntimeDecision.fallback(
                    plan.fallback(),
                    "Vendor execution exceeded " + policy.timeoutMillis()
                            + " ms; public fallback selected."
            );
        }
        if (result.status() != VendorExecutionStatus.APPLIED_AND_VERIFIED) {
            return VendorRuntimeDecision.fallback(
                    plan.fallback(),
                    "Vendor execution was not verified: " + result.status()
                            + ". " + result.detail()
            );
        }
        return VendorRuntimeDecision.active(
                policy,
                plan.fallback(),
                "Vendor configuration applied within timeout and produced the expected result."
        );
    }
}
