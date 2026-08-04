package com.phone2pro.camera.ui;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.DeviceCapabilitySnapshot;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.RouteDecision;
import com.phone2pro.camera.core.RouteMechanism;
import com.phone2pro.camera.core.RouteRendering;
import com.phone2pro.camera.core.RouteSupport;

import org.junit.Test;

import java.util.Collections;

public final class CameraUiArchitectureTest {
    private final CameraUiReducer reducer = new CameraUiReducer();

    @Test
    public void uiEventsDoNotMutateBackendSnapshot() {
        CameraBackendSnapshot backend = readyBackend(
                OpticalRoute.MAIN,
                RouteRendering.OPTICAL
        );
        CameraUiState initial = CameraUiState.initial();
        CameraUiState rotated = reducer.reduce(
                initial,
                UiEvent.orientation(PreviewOrientation.LANDSCAPE_90)
        );

        CameraScreenModel screen = new CameraScreenModel(backend, rotated);
        assertSame(backend, screen.backend());
        assertEquals(PreviewOrientation.LANDSCAPE_90, screen.ui().orientation());
        assertEquals(OpticalRoute.MAIN, screen.backend().selectedRoute());
        assertTrue(screen.backend().sessionReady());
    }

    @Test
    public void opticalInSensorAndDigitalRoutesRemainTransparent() {
        RoutePresentation optical = RoutePresentation.from(decision(
                OpticalRoute.MAIN,
                RouteRendering.OPTICAL
        ));
        RoutePresentation inSensor = RoutePresentation.from(decision(
                OpticalRoute.TELEPHOTO,
                RouteRendering.IN_SENSOR
        ));
        RoutePresentation digital = RoutePresentation.from(decision(
                OpticalRoute.TELEPHOTO,
                RouteRendering.DIGITAL
        ));

        assertEquals("Optical", optical.renderingLabel());
        assertEquals("In-sensor", inSensor.renderingLabel());
        assertEquals("Digital", digital.renderingLabel());
        assertTrue(digital.controlLabel().contains("Digital"));
        assertFalse(digital.controlLabel().contains("Optical"));
        assertTrue(digital.accessibilityLabel().toLowerCase().contains("digital"));
    }

    @Test
    public void unavailableRouteShowsExactReason() {
        RouteDecision unavailable = new RouteDecision(
                OpticalRoute.ULTRAWIDE,
                "none",
                RouteSupport.unavailable("System camera access is not authorized.")
        );
        DeviceCapabilitySnapshot capabilities = capabilities();
        CameraBackendSnapshot backend = new CameraBackendSnapshot(
                capabilities,
                OpticalRoute.ULTRAWIDE,
                unavailable,
                PreviewState.STOPPED,
                false,
                null
        );
        CameraScreenModel screen = new CameraScreenModel(backend, CameraUiState.initial());

        assertEquals(RouteRendering.UNAVAILABLE, screen.route().rendering());
        assertTrue(screen.statusMessage().contains("not authorized"));
        assertFalse(screen.shutterEnabled());
    }

    @Test
    public void persistedCaptureCanResumeWhileProcessingContinues() {
        CameraUiState state = CameraUiState.initial();
        state = reducer.reduce(state, UiEvent.captureStarted());
        state = reducer.reduce(state, UiEvent.captureSaving());
        state = reducer.reduce(state, UiEvent.processingStarted());
        state = reducer.reduce(state, UiEvent.capturePersisted("content://photo/1"));

        CameraScreenModel screen = new CameraScreenModel(
                readyBackend(OpticalRoute.MAIN, RouteRendering.OPTICAL),
                state
        );

        assertEquals(CaptureFeedback.SAVED, state.captureFeedback());
        assertEquals(1, state.processingJobCount());
        assertTrue(state.processingInBackground());
        assertTrue(screen.shutterEnabled());
        assertTrue(screen.shutterAccessibilityLabel().contains("processing on device"));

        CameraUiState completed = reducer.reduce(state, UiEvent.processingFinished());
        assertEquals(0, completed.processingJobCount());
        assertTrue(new CameraScreenModel(
                readyBackend(OpticalRoute.MAIN, RouteRendering.OPTICAL),
                completed
        ).shutterEnabled());
    }

    @Test
    public void captureAndBackgroundLifecycleDisableShutter() {
        CameraBackendSnapshot backend = readyBackend(
                OpticalRoute.MAIN,
                RouteRendering.OPTICAL
        );
        CameraUiState capturing = reducer.reduce(
                CameraUiState.initial(),
                UiEvent.captureStarted()
        );
        assertFalse(new CameraScreenModel(backend, capturing).shutterEnabled());

        CameraUiState background = reducer.reduce(
                CameraUiState.initial(),
                UiEvent.lifecycle(AppLifecycleState.BACKGROUND)
        );
        assertFalse(new CameraScreenModel(backend, background).shutterEnabled());
    }

    @Test
    public void focusMeteringAndOrientationAreNormalized() {
        CameraUiState state = reducer.reduce(
                CameraUiState.initial(),
                UiEvent.focusRequested(new MeteringPoint(0.25f, 0.75f))
        );
        assertEquals(FocusMeteringState.Status.REQUESTED, state.focusMetering().status());
        assertEquals(CaptureFeedback.FOCUSING, state.captureFeedback());

        state = reducer.reduce(state, UiEvent.focusLocked());
        assertEquals(FocusMeteringState.Status.LOCKED, state.focusMetering().status());
        assertEquals(CaptureFeedback.READY, state.captureFeedback());
        assertEquals(PreviewOrientation.LANDSCAPE_270, PreviewOrientation.fromClockwiseDegrees(-90));
        expectIllegalArgument(() -> new MeteringPoint(1.1f, 0.5f));
        expectIllegalArgument(() -> PreviewOrientation.fromClockwiseDegrees(45));
    }

    @Test
    public void settingsAndCaptureModeRemainUiOwned() {
        CameraUiState initial = CameraUiState.initial();
        CameraUiState changed = reducer.reduce(initial, UiEvent.settingsVisible(true));
        changed = reducer.reduce(changed, UiEvent.profileSelected(CaptureProfile.MAX_DETAIL));

        assertFalse(initial.settingsVisible());
        assertEquals(CaptureProfile.AUTO, initial.selectedProfile());
        assertTrue(changed.settingsVisible());
        assertEquals(CaptureProfile.MAX_DETAIL, changed.selectedProfile());
    }

    @Test
    public void invalidProcessingAndCaptureTransitionsFailClosed() {
        expectIllegalState(() -> reducer.reduce(
                CameraUiState.initial(),
                UiEvent.processingFinished()
        ));
        expectIllegalState(() -> reducer.reduce(
                CameraUiState.initial(),
                UiEvent.captureSaving()
        ));
    }

    private static CameraBackendSnapshot readyBackend(
            OpticalRoute route,
            RouteRendering rendering
    ) {
        return new CameraBackendSnapshot(
                capabilities(),
                route,
                decision(route, rendering),
                PreviewState.STREAMING,
                true,
                null
        );
    }

    private static RouteDecision decision(OpticalRoute route, RouteRendering rendering) {
        return new RouteDecision(
                route,
                "test-backend",
                RouteSupport.available(
                        RouteMechanism.PUBLIC_CAMERA,
                        rendering,
                        "Test route with explicit " + rendering + " rendering."
                )
        );
    }

    private static DeviceCapabilitySnapshot capabilities() {
        return new DeviceCapabilitySnapshot(
                "Nothing",
                "A001",
                "Galaga",
                Collections.singleton("0")
        );
    }

    private static void expectIllegalArgument(Runnable work) {
        try {
            work.run();
            throw new AssertionError("Expected IllegalArgumentException");
        } catch (IllegalArgumentException expected) {
            // Expected.
        }
    }

    private static void expectIllegalState(Runnable work) {
        try {
            work.run();
            throw new AssertionError("Expected IllegalStateException");
        } catch (IllegalStateException expected) {
            // Expected.
        }
    }
}
