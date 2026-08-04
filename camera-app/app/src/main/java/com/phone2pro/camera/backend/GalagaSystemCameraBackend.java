package com.phone2pro.camera.backend;

import com.phone2pro.camera.core.DeviceCapabilitySnapshot;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.ResolvedCameraEndpoint;
import com.phone2pro.camera.core.RouteBackend;
import com.phone2pro.camera.core.RouteMechanism;
import com.phone2pro.camera.core.RouteRendering;
import com.phone2pro.camera.core.RouteSupport;

import java.util.Objects;
import java.util.Optional;

/** Capability-gated backend for the statically recovered Galaga manual endpoint table. */
public final class GalagaSystemCameraBackend implements RouteBackend {
    public static final String BACKEND_ID = "galaga-system-camera2";
    private static final String ROUTE_EVIDENCE =
            "Nothing Camera 16.1.01.93.20 Galaga manual route table";

    private final GalagaManualRouteTable routeTable;
    private final SystemEndpointAccess endpointAccess;

    public GalagaSystemCameraBackend(SystemEndpointAccess endpointAccess) {
        this(new GalagaManualRouteTable(), endpointAccess);
    }

    GalagaSystemCameraBackend(
            GalagaManualRouteTable routeTable,
            SystemEndpointAccess endpointAccess
    ) {
        this.routeTable = Objects.requireNonNull(routeTable, "routeTable");
        this.endpointAccess = Objects.requireNonNull(endpointAccess, "endpointAccess");
    }

    @Override
    public String backendId() {
        return BACKEND_ID;
    }

    @Override
    public int priority() {
        return 500;
    }

    @Override
    public RouteSupport evaluate(
            OpticalRoute route,
            DeviceCapabilitySnapshot capabilities
    ) {
        Objects.requireNonNull(route, "route");
        Objects.requireNonNull(capabilities, "capabilities");

        if (!capabilities.isGalaga()) {
            return RouteSupport.unavailable("The recovered endpoint table is Galaga-specific.");
        }

        Optional<String> cameraId = routeTable.cameraIdFor(route);
        if (!cameraId.isPresent()) {
            return RouteSupport.unavailable("No recovered Galaga endpoint exists for " + route.id() + ".");
        }

        if (!endpointAccess.canOpen(cameraId.get(), capabilities)) {
            return RouteSupport.unavailable(
                    "System camera ID " + cameraId.get() + " is statically mapped but access is "
                            + "not verified: " + endpointAccess.evidence()
            );
        }

        return RouteSupport.available(
                RouteMechanism.SYSTEM_CAMERA,
                RouteRendering.OPTICAL,
                "Authorized direct endpoint " + cameraId.get() + ". " + ROUTE_EVIDENCE + "."
        );
    }

    @Override
    public Optional<ResolvedCameraEndpoint> resolve(
            OpticalRoute route,
            DeviceCapabilitySnapshot capabilities
    ) {
        RouteSupport support = evaluate(route, capabilities);
        if (!support.isAvailable()) {
            return Optional.empty();
        }
        String cameraId = routeTable.cameraIdFor(route).orElseThrow(
                () -> new IllegalStateException("Available route has no Galaga endpoint")
        );
        return Optional.of(new ResolvedCameraEndpoint(
                cameraId,
                RouteMechanism.SYSTEM_CAMERA,
                ROUTE_EVIDENCE + "; access evidence: " + endpointAccess.evidence()
        ));
    }
}
