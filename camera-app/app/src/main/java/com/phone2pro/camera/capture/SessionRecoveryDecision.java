package com.phone2pro.camera.capture;

import java.util.Objects;

/** Deterministic recovery decision with a bounded retry delay. */
public final class SessionRecoveryDecision {
    private final SessionRecoveryAction action;
    private final long delayMs;
    private final boolean sessionRecreationRequired;

    public SessionRecoveryDecision(
            SessionRecoveryAction action,
            long delayMs,
            boolean sessionRecreationRequired
    ) {
        this.action = Objects.requireNonNull(action, "action");
        if (delayMs < 0) {
            throw new IllegalArgumentException("delayMs must be non-negative");
        }
        if (sessionRecreationRequired
                && action != SessionRecoveryAction.RECREATE_SESSION
                && action != SessionRecoveryAction.REOPEN_CAMERA) {
            throw new IllegalArgumentException(
                    "session recreation flag requires a recreation or reopen action"
            );
        }
        this.delayMs = delayMs;
        this.sessionRecreationRequired = sessionRecreationRequired;
    }

    public SessionRecoveryAction action() { return action; }
    public long delayMs() { return delayMs; }
    public boolean sessionRecreationRequired() { return sessionRecreationRequired; }
}
