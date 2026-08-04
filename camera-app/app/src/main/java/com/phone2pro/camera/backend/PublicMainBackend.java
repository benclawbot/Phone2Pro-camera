package com.phone2pro.camera.backend;

import com.phone2pro.camera.core.DeviceCapabilitySnapshot;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.ResolvedCameraEndpoint;
import com.phone2pro.camera.core.RouteBackend;
import com.phone2pro.camera.core.RouteMechanism;
import com.phone2pro.camera.core.RouteRendering;
import com.phone2pro.camera.core.RouteSupport;

import java.util.Optional;

/** Ordinary-app backend for the verified public rear main camera. */
public final class PublicMainBackend implements RouteBackend {
    public static final String BACKEND_ID = "public-main-camera2";
    public static final String GALAGA_PUBLIC_REAR_ID = "0";

    @Override
    public String backendId() {
        return BACKEND_ID;
    }

    @Override
    public int priority() {
        return 100;
    }

    @Override
    public RouteSupport evaluate(
            OpticalRoute route,
            DeviceCapabilitySnapshot capabilities
    ) {
        if (!OpticalRoute.MAIN.equals(route)) {
            return RouteSupport.unavailable(
                    "The public backend exposes only the verified 24 mm main route. "
                            + "It will not represent a digital crop as an optical auxiliary lens."
            );
        }
        if (!capabilities.hasPublicCameraId(GALAGA_PUBLIC_REAR_ID)) {
            return RouteSupport.unavailable("Public rear camera ID 0 is not available.");
        }
        return RouteSupport.available(
                RouteMechanism.PUBLIC_CAMERA,
                RouteRendering.OPTICAL,
                "Verified public Camera2 ID 0 main-camera route."
        );
    }

    @Override
    public Optional<ResolvedCameraEndpoint> resolve(
            OpticalRoute route,
            DeviceCapabilitySnapshot capabilities
    ) {
        if (!evaluate(route, capabilities).isAvailable()) {
            return Optional.empty();
        }
        return Optional.of(new ResolvedCameraEndpoint(
                GALAGA_PUBLIC_REAR_ID,
                RouteMechanism.PUBLIC_CAMERA,
                "Public Camera2 capability snapshot contains rear camera ID 0."
        ));
    }
}
