package com.phone2pro.camera.core;

import java.util.Objects;
import java.util.Optional;

/** Result of negotiating one requested optical route against installed backends. */
public final class RouteDecision {
    private final OpticalRoute route;
    private final String backendId;
    private final RouteSupport support;
    private final ResolvedCameraEndpoint endpoint;

    public RouteDecision(OpticalRoute route, String backendId, RouteSupport support) {
        this(route, backendId, support, null);
    }

    public RouteDecision(
            OpticalRoute route,
            String backendId,
            RouteSupport support,
            ResolvedCameraEndpoint endpoint
    ) {
        this.route = Objects.requireNonNull(route, "route");
        this.backendId = Objects.requireNonNull(backendId, "backendId");
        this.support = Objects.requireNonNull(support, "support");
        if (!support.isAvailable() && endpoint != null) {
            throw new IllegalArgumentException("Unavailable route cannot have an endpoint");
        }
        this.endpoint = endpoint;
    }

    public OpticalRoute route() {
        return route;
    }

    public String backendId() {
        return backendId;
    }

    public RouteSupport support() {
        return support;
    }

    public RouteRendering rendering() {
        return support.rendering();
    }

    public Optional<ResolvedCameraEndpoint> endpoint() {
        return Optional.ofNullable(endpoint);
    }
}
