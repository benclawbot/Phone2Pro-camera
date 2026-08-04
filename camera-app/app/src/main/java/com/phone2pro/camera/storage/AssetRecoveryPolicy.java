package com.phone2pro.camera.storage;

import java.util.Objects;

/** Deterministic startup recovery for pending, processing and terminal assets. */
public final class AssetRecoveryPolicy {
    private final long staleAfterMillis;

    public AssetRecoveryPolicy(long staleAfterMillis) {
        if (staleAfterMillis <= 0) {
            throw new IllegalArgumentException("staleAfterMillis must be positive");
        }
        this.staleAfterMillis = staleAfterMillis;
    }

    public RecoveryDecision decide(CaptureAssetRecord record, long nowEpochMillis) {
        Objects.requireNonNull(record, "record");
        if (nowEpochMillis < record.updatedAtEpochMillis()) {
            throw new IllegalArgumentException("recovery clock predates journal record");
        }
        boolean stale = nowEpochMillis - record.updatedAtEpochMillis() >= staleAfterMillis;
        switch (record.lifecycle()) {
            case PUBLISHED:
                return decision(record, RecoveryAction.KEEP_PUBLISHED, "Asset is already visible and complete.");
            case READY_TO_PUBLISH:
                if (record.durableSourceAvailable()) {
                    return decision(
                            record,
                            RecoveryAction.PUBLISH_READY_ASSET,
                            "Complete durable bytes exist; finalize metadata and clear pending state."
                    );
                }
                return decision(
                        record,
                        RecoveryAction.DELETE_PENDING_ROW,
                        "Ready state without durable bytes is inconsistent and must not become visible."
                );
            case PROCESSING:
            case WRITING:
                if (record.durableSourceAvailable()) {
                    return decision(
                            record,
                            RecoveryAction.RESUME_PROCESSING,
                            "Durable source exists and processing can resume after process termination."
                    );
                }
                if (stale) {
                    return decision(
                            record,
                            RecoveryAction.DELETE_PENDING_ROW,
                            "Stale pending row has no recoverable durable source."
                    );
                }
                return decision(
                        record,
                        RecoveryAction.WAIT_FOR_ACTIVE_WRITER,
                        "Recent pending row may still belong to an active writer."
                );
            case RESERVED_PENDING:
                return decision(
                        record,
                        stale
                                ? RecoveryAction.DELETE_PENDING_ROW
                                : RecoveryAction.WAIT_FOR_ACTIVE_WRITER,
                        stale
                                ? "Reserved row was never written and is stale."
                                : "Recent reservation may still be active."
                );
            case FAILED:
            case ABANDONED:
                return decision(
                        record,
                        RecoveryAction.REMOVE_TERMINAL_JOURNAL_RECORD,
                        "Terminal failed or abandoned work must not remain in the active journal."
                );
            default:
                throw new IllegalStateException("Unhandled lifecycle: " + record.lifecycle());
        }
    }

    public long staleAfterMillis() {
        return staleAfterMillis;
    }

    private static RecoveryDecision decision(
            CaptureAssetRecord record,
            RecoveryAction action,
            String reason
    ) {
        return new RecoveryDecision(record.assetId(), action, reason);
    }
}
