package com.phone2pro.camera.ui;

import com.phone2pro.camera.core.CaptureProfile;

import java.util.Objects;
import java.util.Optional;

/** UI-owned state. Camera/backend lifecycle is intentionally stored elsewhere. */
public final class CameraUiState {
    private final AppLifecycleState lifecycle;
    private final PreviewOrientation orientation;
    private final FocusMeteringState focusMetering;
    private final CaptureFeedback captureFeedback;
    private final int processingJobCount;
    private final CaptureProfile selectedProfile;
    private final boolean settingsVisible;
    private final String statusMessage;
    private final String latestAssetId;

    CameraUiState(
            AppLifecycleState lifecycle,
            PreviewOrientation orientation,
            FocusMeteringState focusMetering,
            CaptureFeedback captureFeedback,
            int processingJobCount,
            CaptureProfile selectedProfile,
            boolean settingsVisible,
            String statusMessage,
            String latestAssetId
    ) {
        this.lifecycle = Objects.requireNonNull(lifecycle, "lifecycle");
        this.orientation = Objects.requireNonNull(orientation, "orientation");
        this.focusMetering = Objects.requireNonNull(focusMetering, "focusMetering");
        this.captureFeedback = Objects.requireNonNull(captureFeedback, "captureFeedback");
        if (processingJobCount < 0) {
            throw new IllegalArgumentException("processingJobCount must be non-negative");
        }
        this.processingJobCount = processingJobCount;
        this.selectedProfile = Objects.requireNonNull(selectedProfile, "selectedProfile");
        this.settingsVisible = settingsVisible;
        this.statusMessage = Objects.requireNonNull(statusMessage, "statusMessage");
        this.latestAssetId = latestAssetId;
    }

    public static CameraUiState initial() {
        return new CameraUiState(
                AppLifecycleState.FOREGROUND,
                PreviewOrientation.PORTRAIT_0,
                FocusMeteringState.idle(),
                CaptureFeedback.READY,
                0,
                CaptureProfile.AUTO,
                false,
                "Initializing on-device camera…",
                null
        );
    }

    public AppLifecycleState lifecycle() { return lifecycle; }
    public PreviewOrientation orientation() { return orientation; }
    public FocusMeteringState focusMetering() { return focusMetering; }
    public CaptureFeedback captureFeedback() { return captureFeedback; }
    public int processingJobCount() { return processingJobCount; }
    public CaptureProfile selectedProfile() { return selectedProfile; }
    public boolean settingsVisible() { return settingsVisible; }
    public String statusMessage() { return statusMessage; }
    public Optional<String> latestAssetId() { return Optional.ofNullable(latestAssetId); }

    public boolean processingInBackground() {
        return processingJobCount > 0;
    }
}
