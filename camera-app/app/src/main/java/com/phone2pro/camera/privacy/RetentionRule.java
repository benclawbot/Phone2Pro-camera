package com.phone2pro.camera.privacy;

import java.util.Objects;

/** Maximum lifetime and persistence rule for one sensitive data class. */
public final class RetentionRule {
    public enum LifetimeBoundary {
        FRAME_CONSUMED,
        CAPTURE_COMPLETED,
        PROCESSING_COMPLETED,
        USER_DELETES_ASSET,
        APP_SESSION_END,
        NEVER_COLLECT
    }

    private final SensitiveDataKind kind;
    private final LifetimeBoundary boundary;
    private final boolean persistentStorageAllowed;
    private final boolean diagnosticExportAllowed;
    private final String reason;

    public RetentionRule(
            SensitiveDataKind kind,
            LifetimeBoundary boundary,
            boolean persistentStorageAllowed,
            boolean diagnosticExportAllowed,
            String reason
    ) {
        this.kind = Objects.requireNonNull(kind, "kind");
        this.boundary = Objects.requireNonNull(boundary, "boundary");
        this.reason = Objects.requireNonNull(reason, "reason");
        if (reason.isEmpty()) {
            throw new IllegalArgumentException("reason must not be empty");
        }
        if (boundary == LifetimeBoundary.NEVER_COLLECT
                && (persistentStorageAllowed || diagnosticExportAllowed)) {
            throw new IllegalArgumentException("never-collected data cannot be stored or exported");
        }
        this.persistentStorageAllowed = persistentStorageAllowed;
        this.diagnosticExportAllowed = diagnosticExportAllowed;
    }

    public SensitiveDataKind kind() { return kind; }
    public LifetimeBoundary boundary() { return boundary; }
    public boolean persistentStorageAllowed() { return persistentStorageAllowed; }
    public boolean diagnosticExportAllowed() { return diagnosticExportAllowed; }
    public String reason() { return reason; }
}
