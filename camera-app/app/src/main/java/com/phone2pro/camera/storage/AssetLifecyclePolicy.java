package com.phone2pro.camera.storage;

import java.util.EnumSet;
import java.util.Objects;
import java.util.Set;

/** Validates pending-write, processing, publication and cleanup transitions. */
public final class AssetLifecyclePolicy {
    public CaptureAssetRecord transition(
            CaptureAssetRecord record,
            AssetLifecycle next,
            boolean durableSourceAvailable,
            long nowEpochMillis,
            String failureReason
    ) {
        Objects.requireNonNull(record, "record");
        Objects.requireNonNull(next, "next");
        if (!allowedNext(record.lifecycle()).contains(next)) {
            throw new IllegalStateException(
                    "invalid asset transition " + record.lifecycle() + " -> " + next
            );
        }
        if (next == AssetLifecycle.PUBLISHED && !durableSourceAvailable) {
            throw new IllegalStateException("cannot publish without a complete durable source");
        }
        if (next == AssetLifecycle.READY_TO_PUBLISH && !durableSourceAvailable) {
            throw new IllegalStateException("ready-to-publish asset requires durable bytes");
        }
        if (next != AssetLifecycle.FAILED && failureReason != null) {
            throw new IllegalArgumentException("failure reason only applies to FAILED");
        }
        return record.transition(
                next,
                durableSourceAvailable,
                nowEpochMillis,
                failureReason
        );
    }

    private static Set<AssetLifecycle> allowedNext(AssetLifecycle current) {
        switch (current) {
            case RESERVED_PENDING:
                return EnumSet.of(AssetLifecycle.WRITING, AssetLifecycle.FAILED, AssetLifecycle.ABANDONED);
            case WRITING:
                return EnumSet.of(
                        AssetLifecycle.PROCESSING,
                        AssetLifecycle.READY_TO_PUBLISH,
                        AssetLifecycle.FAILED,
                        AssetLifecycle.ABANDONED
                );
            case PROCESSING:
                return EnumSet.of(
                        AssetLifecycle.READY_TO_PUBLISH,
                        AssetLifecycle.FAILED,
                        AssetLifecycle.ABANDONED
                );
            case READY_TO_PUBLISH:
                return EnumSet.of(AssetLifecycle.PUBLISHED, AssetLifecycle.FAILED, AssetLifecycle.ABANDONED);
            case PUBLISHED:
            case FAILED:
            case ABANDONED:
                return EnumSet.noneOf(AssetLifecycle.class);
            default:
                throw new IllegalStateException("Unhandled asset lifecycle: " + current);
        }
    }
}
