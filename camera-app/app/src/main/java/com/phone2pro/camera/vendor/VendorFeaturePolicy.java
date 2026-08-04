package com.phone2pro.camera.vendor;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Exact-build allowlist and configuration for one isolated vendor feature. */
public final class VendorFeaturePolicy {
    private final String featureId;
    private final List<VendorBuildIdentity> allowedBuilds;
    private final VendorConfiguration configuration;
    private final long timeoutMillis;

    public VendorFeaturePolicy(
            String featureId,
            List<VendorBuildIdentity> allowedBuilds,
            VendorConfiguration configuration,
            long timeoutMillis
    ) {
        this.featureId = requireText(featureId, "featureId");
        Objects.requireNonNull(allowedBuilds, "allowedBuilds");
        if (allowedBuilds.isEmpty()) {
            throw new IllegalArgumentException("allowedBuilds must not be empty");
        }
        this.allowedBuilds = Collections.unmodifiableList(new ArrayList<>(allowedBuilds));
        this.configuration = Objects.requireNonNull(configuration, "configuration");
        if (timeoutMillis <= 0) {
            throw new IllegalArgumentException("timeoutMillis must be positive");
        }
        this.timeoutMillis = timeoutMillis;
    }

    public String featureId() { return featureId; }
    public List<VendorBuildIdentity> allowedBuilds() { return allowedBuilds; }
    public VendorConfiguration configuration() { return configuration; }
    public long timeoutMillis() { return timeoutMillis; }

    public boolean allows(VendorBuildIdentity build) {
        for (VendorBuildIdentity allowed : allowedBuilds) {
            if (allowed.exactlyMatches(build)) {
                return true;
            }
        }
        return false;
    }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
