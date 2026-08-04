package com.phone2pro.camera.core;

import java.util.Objects;
import java.util.Optional;

/** One immutable backend lifecycle observation with an optional normalized error. */
public final class BackendStatusSnapshot {
    private final String backendId;
    private final BackendLifecycleState state;
    private final BackendErrorCategory errorCategory;
    private final String detail;
    private final long monotonicTimestampNs;

    public BackendStatusSnapshot(
            String backendId,
            BackendLifecycleState state,
            BackendErrorCategory errorCategory,
            String detail,
            long monotonicTimestampNs
    ) {
        this.backendId = Objects.requireNonNull(backendId, "backendId");
        this.state = Objects.requireNonNull(state, "state");
        this.detail = Objects.requireNonNull(detail, "detail");
        if (backendId.isEmpty() || detail.isEmpty()) {
            throw new IllegalArgumentException("backendId and detail must not be empty");
        }
        if (monotonicTimestampNs < 0) {
            throw new IllegalArgumentException("monotonicTimestampNs must be non-negative");
        }
        if (state == BackendLifecycleState.ERROR && errorCategory == null) {
            throw new IllegalArgumentException("ERROR state requires an error category");
        }
        if (state != BackendLifecycleState.ERROR && errorCategory != null) {
            throw new IllegalArgumentException("error category is only valid in ERROR state");
        }
        this.errorCategory = errorCategory;
        this.monotonicTimestampNs = monotonicTimestampNs;
    }

    public String backendId() { return backendId; }
    public BackendLifecycleState state() { return state; }
    public Optional<BackendErrorCategory> errorCategory() {
        return Optional.ofNullable(errorCategory);
    }
    public String detail() { return detail; }
    public long monotonicTimestampNs() { return monotonicTimestampNs; }
}
