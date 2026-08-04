package com.phone2pro.camera.ui;

import com.phone2pro.camera.core.CaptureProfile;

import java.util.Objects;

/** Immutable event consumed by the pure camera UI reducer. */
public final class UiEvent {
    public enum Type {
        LIFECYCLE_CHANGED,
        ORIENTATION_CHANGED,
        FOCUS_REQUESTED,
        FOCUS_LOCKED,
        FOCUS_FAILED,
        FOCUS_CANCELLED,
        CAPTURE_STARTED,
        CAPTURE_SAVING,
        CAPTURE_PERSISTED,
        CAPTURE_FAILED,
        PROCESSING_STARTED,
        PROCESSING_FINISHED,
        PROFILE_SELECTED,
        SETTINGS_VISIBILITY_CHANGED,
        STATUS_CHANGED
    }

    private final Type type;
    private final Object value;
    private final String message;

    private UiEvent(Type type, Object value, String message) {
        this.type = Objects.requireNonNull(type, "type");
        this.value = value;
        this.message = message;
    }

    public static UiEvent lifecycle(AppLifecycleState state) {
        return new UiEvent(Type.LIFECYCLE_CHANGED, state, null);
    }

    public static UiEvent orientation(PreviewOrientation orientation) {
        return new UiEvent(Type.ORIENTATION_CHANGED, orientation, null);
    }

    public static UiEvent focusRequested(MeteringPoint point) {
        return new UiEvent(Type.FOCUS_REQUESTED, point, null);
    }

    public static UiEvent focusLocked() { return new UiEvent(Type.FOCUS_LOCKED, null, null); }
    public static UiEvent focusFailed(String reason) {
        return new UiEvent(Type.FOCUS_FAILED, null, Objects.requireNonNull(reason, "reason"));
    }
    public static UiEvent focusCancelled() { return new UiEvent(Type.FOCUS_CANCELLED, null, null); }
    public static UiEvent captureStarted() { return new UiEvent(Type.CAPTURE_STARTED, null, null); }
    public static UiEvent captureSaving() { return new UiEvent(Type.CAPTURE_SAVING, null, null); }
    public static UiEvent capturePersisted(String assetId) {
        return new UiEvent(
                Type.CAPTURE_PERSISTED,
                Objects.requireNonNull(assetId, "assetId"),
                null
        );
    }
    public static UiEvent captureFailed(String reason) {
        return new UiEvent(Type.CAPTURE_FAILED, null, Objects.requireNonNull(reason, "reason"));
    }
    public static UiEvent processingStarted() {
        return new UiEvent(Type.PROCESSING_STARTED, null, null);
    }
    public static UiEvent processingFinished() {
        return new UiEvent(Type.PROCESSING_FINISHED, null, null);
    }
    public static UiEvent profileSelected(CaptureProfile profile) {
        return new UiEvent(Type.PROFILE_SELECTED, profile, null);
    }
    public static UiEvent settingsVisible(boolean visible) {
        return new UiEvent(Type.SETTINGS_VISIBILITY_CHANGED, visible, null);
    }
    public static UiEvent status(String message) {
        return new UiEvent(Type.STATUS_CHANGED, null, Objects.requireNonNull(message, "message"));
    }

    public Type type() { return type; }
    public String message() { return message; }

    public <T> T value(Class<T> type) {
        Objects.requireNonNull(type, "type");
        if (value == null || !type.isInstance(value)) {
            throw new IllegalStateException("event payload does not contain " + type.getSimpleName());
        }
        return type.cast(value);
    }
}
