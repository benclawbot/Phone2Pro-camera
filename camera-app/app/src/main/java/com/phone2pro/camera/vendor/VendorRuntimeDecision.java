package com.phone2pro.camera.vendor;

import java.util.Objects;
import java.util.Optional;

/** Final runtime choice after applying or abandoning a planned vendor feature. */
public final class VendorRuntimeDecision {
    private final boolean vendorActive;
    private final VendorFeaturePolicy activePolicy;
    private final PublicFallbackConfiguration fallback;
    private final String reason;

    private VendorRuntimeDecision(
            boolean vendorActive,
            VendorFeaturePolicy activePolicy,
            PublicFallbackConfiguration fallback,
            String reason
    ) {
        this.vendorActive = vendorActive;
        this.activePolicy = activePolicy;
        this.fallback = Objects.requireNonNull(fallback, "fallback");
        this.reason = Objects.requireNonNull(reason, "reason");
        if (vendorActive && activePolicy == null) {
            throw new IllegalArgumentException("active vendor decision requires a policy");
        }
        if (!vendorActive && activePolicy != null) {
            throw new IllegalArgumentException("fallback decision cannot retain vendor settings");
        }
    }

    public static VendorRuntimeDecision active(
            VendorFeaturePolicy policy,
            PublicFallbackConfiguration fallback,
            String reason
    ) {
        return new VendorRuntimeDecision(true, policy, fallback, reason);
    }

    public static VendorRuntimeDecision fallback(
            PublicFallbackConfiguration fallback,
            String reason
    ) {
        return new VendorRuntimeDecision(false, null, fallback, reason);
    }

    public boolean vendorActive() { return vendorActive; }
    public Optional<VendorFeaturePolicy> activePolicy() { return Optional.ofNullable(activePolicy); }
    public PublicFallbackConfiguration fallback() { return fallback; }
    public String reason() { return reason; }
}
