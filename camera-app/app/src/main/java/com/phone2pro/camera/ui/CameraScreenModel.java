package com.phone2pro.camera.ui;

import java.util.Objects;

/** Derived screen presentation combining, but not conflating, backend and UI state. */
public final class CameraScreenModel {
    private final CameraBackendSnapshot backend;
    private final CameraUiState ui;
    private final RoutePresentation route;

    public CameraScreenModel(CameraBackendSnapshot backend, CameraUiState ui) {
        this.backend = Objects.requireNonNull(backend, "backend");
        this.ui = Objects.requireNonNull(ui, "ui");
        this.route = RoutePresentation.from(backend.routeDecision());
    }

    public CameraBackendSnapshot backend() { return backend; }
    public CameraUiState ui() { return ui; }
    public RoutePresentation route() { return route; }

    /**
     * Background processing intentionally does not block the next shutter action.
     * Only lifecycle, active session and immediate capture state control readiness.
     */
    public boolean shutterEnabled() {
        if (ui.lifecycle() != AppLifecycleState.FOREGROUND || !backend.sessionReady()) {
            return false;
        }
        switch (ui.captureFeedback()) {
            case READY:
            case SAVED:
            case ERROR:
                return true;
            case FOCUSING:
            case CAPTURING:
            case SAVING:
                return false;
            default:
                throw new IllegalStateException(
                        "Unhandled capture feedback: " + ui.captureFeedback()
                );
        }
    }

    public String statusMessage() {
        if (backend.errorMessage().isPresent()) {
            return backend.errorMessage().get();
        }
        if (!route.available()) {
            return backend.selectedRoute().label() + " unavailable: "
                    + backend.routeDecision().support().reason();
        }
        return ui.statusMessage();
    }

    public String shutterAccessibilityLabel() {
        if (!shutterEnabled()) {
            return "Shutter unavailable. " + statusMessage();
        }
        if (ui.processingInBackground()) {
            return "Take photo. Previous captures are processing on device.";
        }
        return "Take photo.";
    }
}
