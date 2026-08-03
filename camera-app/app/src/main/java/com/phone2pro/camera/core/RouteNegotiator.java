package com.phone2pro.camera.core;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;

/** Chooses the highest-priority backend that explicitly supports the requested optical route. */
public final class RouteNegotiator {
    private static final String NO_BACKEND_ID = "none";

    private final List<RouteBackend> backends;

    public RouteNegotiator(List<RouteBackend> backends) {
        Objects.requireNonNull(backends, "backends");
        this.backends = new ArrayList<>(backends);
        this.backends.sort(Comparator.comparingInt(RouteBackend::priority).reversed());
    }

    public RouteDecision select(
            OpticalRoute route,
            DeviceCapabilitySnapshot capabilities
    ) {
        Objects.requireNonNull(route, "route");
        Objects.requireNonNull(capabilities, "capabilities");

        List<String> rejectionReasons = new ArrayList<>();
        for (RouteBackend backend : backends) {
            RouteSupport support = backend.evaluate(route, capabilities);
            if (support.isAvailable()) {
                ResolvedCameraEndpoint endpoint = backend.resolve(route, capabilities).orElse(null);
                return new RouteDecision(route, backend.backendId(), support, endpoint);
            }
            rejectionReasons.add(backend.backendId() + ": " + support.reason());
        }

        String reason = rejectionReasons.isEmpty()
                ? "No camera backend is installed."
                : String.join("; ", rejectionReasons);
        return new RouteDecision(route, NO_BACKEND_ID, RouteSupport.unavailable(reason));
    }
}
