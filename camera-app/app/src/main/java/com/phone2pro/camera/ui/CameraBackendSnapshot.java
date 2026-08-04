package com.phone2pro.camera.ui;

import com.phone2pro.camera.core.DeviceCapabilitySnapshot;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.RouteDecision;

import java.util.Objects;
import java.util.Optional;

/**
 * Read-only camera/backend state supplied to the UI.
 *
 * <p>The UI reducer never mutates this object; camera controllers replace it with a new snapshot.</p>
 */
public final class CameraBackendSnapshot {
    private final DeviceCapabilitySnapshot capabilities;
    private final OpticalRoute selectedRoute;
    private final RouteDecision routeDecision;
    private final PreviewState previewState;
    private final boolean sessionReady;
    private final String errorMessage;

    public CameraBackendSnapshot(
            DeviceCapabilitySnapshot capabilities,
            OpticalRoute selectedRoute,
            RouteDecision routeDecision,
            PreviewState previewState,
            boolean sessionReady,
            String errorMessage
    ) {
        this.capabilities = Objects.requireNonNull(capabilities, "capabilities");
        this.selectedRoute = Objects.requireNonNull(selectedRoute, "selectedRoute");
        this.routeDecision = Objects.requireNonNull(routeDecision, "routeDecision");
        this.previewState = Objects.requireNonNull(previewState, "previewState");
        if (!selectedRoute.equals(routeDecision.route())) {
            throw new IllegalArgumentException("route decision must describe selectedRoute");
        }
        if (sessionReady && (!routeDecision.support().isAvailable()
                || previewState != PreviewState.STREAMING)) {
            throw new IllegalArgumentException(
                    "a ready session requires an available route and streaming preview"
            );
        }
        this.sessionReady = sessionReady;
        this.errorMessage = errorMessage;
    }

    public DeviceCapabilitySnapshot capabilities() { return capabilities; }
    public OpticalRoute selectedRoute() { return selectedRoute; }
    public RouteDecision routeDecision() { return routeDecision; }
    public PreviewState previewState() { return previewState; }
    public boolean sessionReady() { return sessionReady; }
    public Optional<String> errorMessage() { return Optional.ofNullable(errorMessage); }
}
