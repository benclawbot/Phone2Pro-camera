package com.phone2pro.camera.ui;

import java.util.Objects;
import java.util.Optional;

/** UI-visible focus/metering gesture and result state. */
public final class FocusMeteringState {
    public enum Status {
        IDLE,
        REQUESTED,
        LOCKED,
        FAILED,
        CANCELLED
    }

    private final Status status;
    private final MeteringPoint point;
    private final String message;

    private FocusMeteringState(Status status, MeteringPoint point, String message) {
        this.status = Objects.requireNonNull(status, "status");
        if ((status == Status.REQUESTED || status == Status.LOCKED || status == Status.FAILED)
                && point == null) {
            throw new IllegalArgumentException(status + " requires a metering point");
        }
        this.point = point;
        this.message = Objects.requireNonNull(message, "message");
    }

    public static FocusMeteringState idle() {
        return new FocusMeteringState(Status.IDLE, null, "Tap the preview to focus and meter.");
    }

    public static FocusMeteringState requested(MeteringPoint point) {
        return new FocusMeteringState(Status.REQUESTED, point, "Focusing at selected point.");
    }

    public FocusMeteringState locked() {
        if (point == null) {
            throw new IllegalStateException("No metering point is active");
        }
        return new FocusMeteringState(Status.LOCKED, point, "Focus and exposure locked.");
    }

    public FocusMeteringState failed(String reason) {
        if (point == null) {
            throw new IllegalStateException("No metering point is active");
        }
        return new FocusMeteringState(Status.FAILED, point, reason);
    }

    public FocusMeteringState cancelled() {
        return new FocusMeteringState(Status.CANCELLED, null, "Focus request cancelled.");
    }

    public Status status() { return status; }
    public Optional<MeteringPoint> point() { return Optional.ofNullable(point); }
    public String message() { return message; }
}
