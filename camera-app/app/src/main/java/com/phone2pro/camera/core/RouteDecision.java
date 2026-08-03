package com.phone2pro.camera.core;

import java.util.Objects;

/** Result of negotiating one requested optical route against installed backends. */
public final class RouteDecision {
    private final OpticalRoute route;
    private final String backendId;
    private final RouteSupport support;

    public RouteDecision(OpticalRoute route, String backendId, RouteSupport support) {
        this.route = Objects.requireNonNull(route, "route");
        this.backendId = Objects.requireNonNull(backendId, "backendId");
        this.support = Objects.requireNonNull(support, "support");
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
}
