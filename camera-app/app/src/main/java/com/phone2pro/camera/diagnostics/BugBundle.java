package com.phone2pro.camera.diagnostics;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Reproducible diagnostic bundle containing configuration and timing, never photos. */
public final class BugBundle {
    private final String bundleId;
    private final String protocolVersion;
    private final List<CaptureDiagnosticReport> captures;
    private final List<FeatureFlagReport> featureFlags;

    public BugBundle(
            String bundleId,
            String protocolVersion,
            List<CaptureDiagnosticReport> captures,
            List<FeatureFlagReport> featureFlags
    ) {
        this.bundleId = requireText(bundleId, "bundleId");
        this.protocolVersion = requireText(protocolVersion, "protocolVersion");
        this.captures = immutableCopy(captures, "captures");
        this.featureFlags = immutableCopy(featureFlags, "featureFlags");
        if (this.captures.isEmpty() && this.featureFlags.isEmpty()) {
            throw new IllegalArgumentException("bug bundle must contain diagnostic evidence");
        }
        for (CaptureDiagnosticReport report : this.captures) {
            if (report.containsUserPixels()) {
                throw new IllegalArgumentException("bug bundle cannot contain user pixels");
            }
        }
    }

    public String bundleId() { return bundleId; }
    public String protocolVersion() { return protocolVersion; }
    public List<CaptureDiagnosticReport> captures() { return captures; }
    public List<FeatureFlagReport> featureFlags() { return featureFlags; }
    public boolean containsUserPixels() { return false; }

    private static <T> List<T> immutableCopy(List<T> values, String name) {
        Objects.requireNonNull(values, name);
        List<T> copy = new ArrayList<>(values.size());
        for (T value : values) {
            copy.add(Objects.requireNonNull(value, name + " entry"));
        }
        return Collections.unmodifiableList(copy);
    }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
