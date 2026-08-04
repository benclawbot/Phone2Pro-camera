package com.phone2pro.camera.diagnostics;

import java.util.Objects;

/** Metadata-key description without raw private or vendor values. */
public final class ConfigurationEntryReport {
    public enum Scope {
        SESSION,
        REPEATING_REQUEST,
        STILL_REQUEST
    }

    private final Scope scope;
    private final String keyName;
    private final String valueType;
    private final String redactedSummary;

    public ConfigurationEntryReport(
            Scope scope,
            String keyName,
            String valueType,
            String redactedSummary
    ) {
        this.scope = Objects.requireNonNull(scope, "scope");
        this.keyName = requireText(keyName, "keyName");
        this.valueType = requireText(valueType, "valueType");
        this.redactedSummary = requireText(redactedSummary, "redactedSummary");
        if (redactedSummary.contains("content://")
                || redactedSummary.contains("file://")
                || redactedSummary.contains("/storage/")) {
            throw new IllegalArgumentException("configuration summary contains a private path or URI");
        }
    }

    public Scope scope() { return scope; }
    public String keyName() { return keyName; }
    public String valueType() { return valueType; }
    public String redactedSummary() { return redactedSummary; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
