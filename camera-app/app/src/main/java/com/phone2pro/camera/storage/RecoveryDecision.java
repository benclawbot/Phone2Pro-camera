package com.phone2pro.camera.storage;

import java.util.Objects;

/** One journal-replay decision with an explicit reason. */
public final class RecoveryDecision {
    private final String assetId;
    private final RecoveryAction action;
    private final String reason;

    public RecoveryDecision(String assetId, RecoveryAction action, String reason) {
        this.assetId = Objects.requireNonNull(assetId, "assetId");
        this.action = Objects.requireNonNull(action, "action");
        this.reason = Objects.requireNonNull(reason, "reason");
        if (assetId.isEmpty() || reason.isEmpty()) {
            throw new IllegalArgumentException("assetId and reason must not be empty");
        }
    }

    public String assetId() { return assetId; }
    public RecoveryAction action() { return action; }
    public String reason() { return reason; }
}
