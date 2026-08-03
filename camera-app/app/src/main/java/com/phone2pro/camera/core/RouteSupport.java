package com.phone2pro.camera.core;

import java.util.Objects;

/** A backend's explicit support decision for one optical route. */
public final class RouteSupport {
    private final boolean available;
    private final RouteMechanism mechanism;
    private final String reason;

    private RouteSupport(boolean available, RouteMechanism mechanism, String reason) {
        this.available = available;
        this.mechanism = Objects.requireNonNull(mechanism, "mechanism");
        this.reason = Objects.requireNonNull(reason, "reason");
    }

    public static RouteSupport available(RouteMechanism mechanism, String reason) {
        if (mechanism == RouteMechanism.UNAVAILABLE) {
            throw new IllegalArgumentException("Available route cannot use UNAVAILABLE mechanism");
        }
        return new RouteSupport(true, mechanism, reason);
    }

    public static RouteSupport unavailable(String reason) {
        return new RouteSupport(false, RouteMechanism.UNAVAILABLE, reason);
    }

    public boolean isAvailable() {
        return available;
    }

    public RouteMechanism mechanism() {
        return mechanism;
    }

    public String reason() {
        return reason;
    }
}
