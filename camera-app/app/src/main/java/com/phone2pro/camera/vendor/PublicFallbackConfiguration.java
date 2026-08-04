package com.phone2pro.camera.vendor;

import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.RouteRendering;

import java.util.Objects;

/** Known-safe public Camera2 configuration used after any vendor failure. */
public final class PublicFallbackConfiguration {
    private final String backendId;
    private final String cameraId;
    private final OpticalRoute route;
    private final RouteRendering rendering;
    private final String evidence;

    public PublicFallbackConfiguration(
            String backendId,
            String cameraId,
            OpticalRoute route,
            RouteRendering rendering,
            String evidence
    ) {
        this.backendId = requireText(backendId, "backendId");
        this.cameraId = requireText(cameraId, "cameraId");
        this.route = Objects.requireNonNull(route, "route");
        this.rendering = Objects.requireNonNull(rendering, "rendering");
        this.evidence = requireText(evidence, "evidence");
        if (rendering == RouteRendering.UNAVAILABLE) {
            throw new IllegalArgumentException("public fallback must be usable");
        }
    }

    public static PublicFallbackConfiguration galagaMain() {
        return new PublicFallbackConfiguration(
                "public-main-camera2",
                "0",
                OpticalRoute.MAIN,
                RouteRendering.OPTICAL,
                "Verified ordinary-app Camera2 ID 0 configuration on Galaga."
        );
    }

    public String backendId() { return backendId; }
    public String cameraId() { return cameraId; }
    public OpticalRoute route() { return route; }
    public RouteRendering rendering() { return rendering; }
    public String evidence() { return evidence; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
