package com.phone2pro.camera.ui;

import com.phone2pro.camera.core.CaptureProfile;

import java.util.Objects;

/** Pure reducer for UI-owned state. It never mutates camera/backend state. */
public final class CameraUiReducer {
    public CameraUiState reduce(CameraUiState state, UiEvent event) {
        Objects.requireNonNull(state, "state");
        Objects.requireNonNull(event, "event");

        AppLifecycleState lifecycle = state.lifecycle();
        PreviewOrientation orientation = state.orientation();
        FocusMeteringState focus = state.focusMetering();
        CaptureFeedback feedback = state.captureFeedback();
        int processingJobs = state.processingJobCount();
        CaptureProfile profile = state.selectedProfile();
        boolean settingsVisible = state.settingsVisible();
        String status = state.statusMessage();
        String latestAsset = state.latestAssetId().orElse(null);

        switch (event.type()) {
            case LIFECYCLE_CHANGED:
                lifecycle = event.value(AppLifecycleState.class);
                if (lifecycle != AppLifecycleState.FOREGROUND) {
                    settingsVisible = false;
                    focus = focus.cancelled();
                }
                status = lifecycle == AppLifecycleState.FOREGROUND
                        ? "Camera active."
                        : "Camera paused while the app is not in the foreground.";
                break;
            case ORIENTATION_CHANGED:
                orientation = event.value(PreviewOrientation.class);
                break;
            case FOCUS_REQUESTED:
                focus = FocusMeteringState.requested(event.value(MeteringPoint.class));
                feedback = CaptureFeedback.FOCUSING;
                status = focus.message();
                break;
            case FOCUS_LOCKED:
                focus = focus.locked();
                feedback = CaptureFeedback.READY;
                status = focus.message();
                break;
            case FOCUS_FAILED:
                focus = focus.failed(event.message());
                feedback = CaptureFeedback.READY;
                status = event.message();
                break;
            case FOCUS_CANCELLED:
                focus = focus.cancelled();
                if (feedback == CaptureFeedback.FOCUSING) {
                    feedback = CaptureFeedback.READY;
                }
                status = focus.message();
                break;
            case CAPTURE_STARTED:
                if (feedback == CaptureFeedback.CAPTURING
                        || feedback == CaptureFeedback.SAVING) {
                    throw new IllegalStateException("a capture is already in progress");
                }
                feedback = CaptureFeedback.CAPTURING;
                status = "Capturing on device…";
                break;
            case CAPTURE_SAVING:
                if (feedback != CaptureFeedback.CAPTURING) {
                    throw new IllegalStateException("capture must start before saving");
                }
                feedback = CaptureFeedback.SAVING;
                status = "Saving capture…";
                break;
            case CAPTURE_PERSISTED:
                if (feedback != CaptureFeedback.CAPTURING
                        && feedback != CaptureFeedback.SAVING) {
                    throw new IllegalStateException("no capture is awaiting persistence");
                }
                latestAsset = event.value(String.class);
                feedback = CaptureFeedback.SAVED;
                status = processingJobs > 0
                        ? "Saved. Processing continues on device."
                        : "Saved on device.";
                break;
            case CAPTURE_FAILED:
                feedback = CaptureFeedback.ERROR;
                status = event.message();
                break;
            case PROCESSING_STARTED:
                processingJobs = Math.addExact(processingJobs, 1);
                status = "Processing " + processingJobs + " capture"
                        + (processingJobs == 1 ? "" : "s") + " on device.";
                break;
            case PROCESSING_FINISHED:
                if (processingJobs == 0) {
                    throw new IllegalStateException("no background processing job is active");
                }
                processingJobs -= 1;
                status = processingJobs == 0
                        ? "On-device processing complete."
                        : "Processing " + processingJobs + " captures on device.";
                break;
            case PROFILE_SELECTED:
                profile = event.value(CaptureProfile.class);
                status = profile.implementationStatus();
                break;
            case SETTINGS_VISIBILITY_CHANGED:
                settingsVisible = event.value(Boolean.class);
                break;
            case STATUS_CHANGED:
                status = event.message();
                break;
            default:
                throw new IllegalStateException("Unhandled UI event: " + event.type());
        }

        return new CameraUiState(
                lifecycle,
                orientation,
                focus,
                feedback,
                processingJobs,
                profile,
                settingsVisible,
                status,
                latestAsset
        );
    }
}
