package com.phone2pro.camera.core;

import java.util.Objects;

/** A backend's explicit support decision for one optical route. */
public final class RouteSupport {
    private final boolean available;
    private final RouteMechanism mechanism;
    private final RouteRendering rendering;
    private final String reason;

    private RouteSupport(
            boolean available,
            RouteMechanism mechanism,
            RouteRendering rendering,
            String reason
    ) {
        this.available = available;
        this.mechanism = Objects.requireNonNull(mechanism, "mechanism");
        this.rendering = Objects.requireNonNull(rendering, "rendering");
        this.reason = Objects.requireNonNull(reason, "reason");
    }

    public static RouteSupport available(
            RouteMechanism mechanism,
            RouteRendering rendering,
            String reason
    ) {
        if (mechanism == RouteMechanism.UNAVAILABLE) {
            throw new IllegalArgumentException("Available route cannot use UNAVAILABLE mechanism");
        }
        if (rendering == RouteRendering.UNAVAILABLE) {
            throw new IllegalArgumentException("Available route cannot use UNAVAILABLE rendering");
        }
        return new RouteSupport(true, mechanism, rendering, reason);
    }

    public static RouteSupport unavailable(String reason) {
        return new RouteSupport(
                false,
                RouteMechanism.UNAVAILABLE,
                RouteRendering.UNAVAILABLE,
                reason
        );
    }

    public boolean isAvailable() {
        return available;
    }

    public RouteMechanism mechanism() {
        return mechanism;
    }

    public RouteRendering rendering() {
        return rendering;
    }

    public String reason() {
        return reason;
    }
}
