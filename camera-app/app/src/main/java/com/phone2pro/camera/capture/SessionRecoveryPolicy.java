package com.phone2pro.camera.capture;

import java.util.Objects;

/** Bounded transient-failure policy that never retries permanent failures. */
public final class SessionRecoveryPolicy {
    private final int maxRequestRetries;
    private final int maxSessionRecreations;
    private final int maxCameraReopens;
    private final long baseDelayMs;

    public SessionRecoveryPolicy(
            int maxRequestRetries,
            int maxSessionRecreations,
            int maxCameraReopens,
            long baseDelayMs
    ) {
        if (maxRequestRetries < 0 || maxSessionRecreations < 0 || maxCameraReopens < 0) {
            throw new IllegalArgumentException("retry limits must be non-negative");
        }
        if (baseDelayMs <= 0) {
            throw new IllegalArgumentException("baseDelayMs must be positive");
        }
        this.maxRequestRetries = maxRequestRetries;
        this.maxSessionRecreations = maxSessionRecreations;
        this.maxCameraReopens = maxCameraReopens;
        this.baseDelayMs = baseDelayMs;
    }

    public SessionRecoveryDecision decide(
            TransientFailureCategory failure,
            int priorAttempts,
            boolean appForeground,
            CaptureCancellation cancellation
    ) {
        Objects.requireNonNull(failure, "failure");
        Objects.requireNonNull(cancellation, "cancellation");
        if (priorAttempts < 0) {
            throw new IllegalArgumentException("priorAttempts must be non-negative");
        }
        if (cancellation.isCancelled()) {
            return new SessionRecoveryDecision(
                    SessionRecoveryAction.CANCELLED,
                    0,
                    false
            );
        }
        switch (failure) {
            case PERMISSION_DENIED:
            case UNSUPPORTED_CONFIGURATION:
            case DEVICE_FATAL:
                return permanentFailure();
            case REQUEST_TIMEOUT:
            case CAPTURE_FAILED:
                if (priorAttempts < maxRequestRetries) {
                    return new SessionRecoveryDecision(
                            SessionRecoveryAction.RETRY_REQUEST,
                            delay(priorAttempts),
                            false
                    );
                }
                if (priorAttempts - maxRequestRetries < maxSessionRecreations) {
                    return new SessionRecoveryDecision(
                            SessionRecoveryAction.RECREATE_SESSION,
                            delay(priorAttempts),
                            true
                    );
                }
                return permanentFailure();
            case SESSION_CONFIGURE_FAILED:
                if (priorAttempts < maxSessionRecreations) {
                    return new SessionRecoveryDecision(
                            SessionRecoveryAction.RECREATE_SESSION,
                            delay(priorAttempts),
                            true
                    );
                }
                return permanentFailure();
            case CAMERA_DISCONNECTED:
                if (appForeground && priorAttempts < maxCameraReopens) {
                    return new SessionRecoveryDecision(
                            SessionRecoveryAction.REOPEN_CAMERA,
                            delay(priorAttempts),
                            true
                    );
                }
                return permanentFailure();
            case CAMERA_IN_USE:
                if (appForeground && priorAttempts < maxCameraReopens) {
                    return new SessionRecoveryDecision(
                            SessionRecoveryAction.WAIT_FOR_RESOURCE,
                            delay(priorAttempts),
                            false
                    );
                }
                return permanentFailure();
            default:
                throw new IllegalStateException("Unhandled failure category " + failure);
        }
    }

    private SessionRecoveryDecision permanentFailure() {
        return new SessionRecoveryDecision(
                SessionRecoveryAction.FAIL_PERMANENT,
                0,
                false
        );
    }

    private long delay(int attempt) {
        int exponent = Math.min(attempt, 5);
        return Math.min(baseDelayMs << exponent, 5_000L);
    }
}
