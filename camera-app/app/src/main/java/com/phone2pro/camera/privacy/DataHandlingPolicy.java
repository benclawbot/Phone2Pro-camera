package com.phone2pro.camera.privacy;

import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;
import java.util.Objects;

/** Immutable lifetime and export policy for every sensitive camera data class. */
public final class DataHandlingPolicy {
    private final Map<SensitiveDataKind, RetentionRule> rules;

    public DataHandlingPolicy(Map<SensitiveDataKind, RetentionRule> rules) {
        Objects.requireNonNull(rules, "rules");
        EnumMap<SensitiveDataKind, RetentionRule> copy = new EnumMap<>(SensitiveDataKind.class);
        copy.putAll(rules);
        for (SensitiveDataKind kind : SensitiveDataKind.values()) {
            RetentionRule rule = copy.get(kind);
            if (rule == null || rule.kind() != kind) {
                throw new IllegalArgumentException("missing or mismatched rule for " + kind);
            }
        }
        this.rules = Collections.unmodifiableMap(copy);
    }

    public static DataHandlingPolicy privateByDefault() {
        EnumMap<SensitiveDataKind, RetentionRule> rules = new EnumMap<>(SensitiveDataKind.class);
        rules.put(SensitiveDataKind.PREVIEW_FRAME, rule(
                SensitiveDataKind.PREVIEW_FRAME,
                RetentionRule.LifetimeBoundary.FRAME_CONSUMED,
                false,
                false,
                "Preview pixels are transient and must be released immediately after display or analysis."
        ));
        rules.put(SensitiveDataKind.CAPTURE_FRAME, rule(
                SensitiveDataKind.CAPTURE_FRAME,
                RetentionRule.LifetimeBoundary.CAPTURE_COMPLETED,
                false,
                false,
                "Source frames are retained only until the capture transaction owns a durable result."
        ));
        rules.put(SensitiveDataKind.PROCESSING_INTERMEDIATE, rule(
                SensitiveDataKind.PROCESSING_INTERMEDIATE,
                RetentionRule.LifetimeBoundary.PROCESSING_COMPLETED,
                false,
                false,
                "Intermediates are private working data and are destroyed when processing finishes or fails."
        ));
        rules.put(SensitiveDataKind.FINAL_IMAGE, rule(
                SensitiveDataKind.FINAL_IMAGE,
                RetentionRule.LifetimeBoundary.USER_DELETES_ASSET,
                true,
                false,
                "Only the user-visible final asset is persistently stored by default."
        ));
        rules.put(SensitiveDataKind.LOCATION, rule(
                SensitiveDataKind.LOCATION,
                RetentionRule.LifetimeBoundary.NEVER_COLLECT,
                false,
                false,
                "Location is disabled unless the user explicitly enables a separate location policy."
        ));
        rules.put(SensitiveDataKind.CAMERA_METADATA, rule(
                SensitiveDataKind.CAMERA_METADATA,
                RetentionRule.LifetimeBoundary.CAPTURE_COMPLETED,
                false,
                true,
                "Non-content metadata may enter an opt-in redacted diagnostic bundle."
        ));
        rules.put(SensitiveDataKind.DEVICE_IDENTITY, rule(
                SensitiveDataKind.DEVICE_IDENTITY,
                RetentionRule.LifetimeBoundary.APP_SESSION_END,
                false,
                false,
                "Raw device identifiers are not exported; diagnostics use an allowlisted build description."
        ));
        rules.put(SensitiveDataKind.DIAGNOSTIC_EVENT, rule(
                SensitiveDataKind.DIAGNOSTIC_EVENT,
                RetentionRule.LifetimeBoundary.APP_SESSION_END,
                false,
                true,
                "Opt-in diagnostics may retain redacted events until the bundle is written or discarded."
        ));
        rules.put(SensitiveDataKind.CRASH_CONTEXT, rule(
                SensitiveDataKind.CRASH_CONTEXT,
                RetentionRule.LifetimeBoundary.APP_SESSION_END,
                false,
                true,
                "Crash context excludes pixels, URIs, locations and arbitrary metadata values."
        ));
        return new DataHandlingPolicy(rules);
    }

    public RetentionRule rule(SensitiveDataKind kind) {
        return rules.get(Objects.requireNonNull(kind, "kind"));
    }

    public Map<SensitiveDataKind, RetentionRule> rules() { return rules; }

    private static RetentionRule rule(
            SensitiveDataKind kind,
            RetentionRule.LifetimeBoundary boundary,
            boolean persistent,
            boolean diagnostics,
            String reason
    ) {
        return new RetentionRule(kind, boundary, persistent, diagnostics, reason);
    }
}
