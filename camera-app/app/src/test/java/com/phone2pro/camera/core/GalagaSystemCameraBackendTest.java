package com.phone2pro.camera.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.phone2pro.camera.backend.GalagaManualRouteTable;
import com.phone2pro.camera.backend.GalagaSystemCameraBackend;
import com.phone2pro.camera.backend.SystemEndpointAccess;
import com.phone2pro.camera.backend.UnverifiedSystemEndpointAccess;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;

public final class GalagaSystemCameraBackendTest {
    private static DeviceCapabilitySnapshot galaga() {
        return new DeviceCapabilitySnapshot(
                "Nothing",
                "A001",
                "Galaga",
                new LinkedHashSet<>(Collections.singletonList("0"))
        );
    }

    @Test
    public void recoveredRouteTableOwnsConcreteEndpointIds() {
        GalagaManualRouteTable table = new GalagaManualRouteTable();

        assertEquals("2", table.cameraIdFor(OpticalRoute.ULTRAWIDE).orElse(null));
        assertEquals("0", table.cameraIdFor(OpticalRoute.MAIN).orElse(null));
        assertEquals("3", table.cameraIdFor(OpticalRoute.TELEPHOTO).orElse(null));
    }

    @Test
    public void unverifiedAccessFailsClosedForSystemEndpoints() {
        GalagaSystemCameraBackend backend = new GalagaSystemCameraBackend(
                new UnverifiedSystemEndpointAccess("privilege unresolved")
        );

        RouteSupport support = backend.evaluate(OpticalRoute.TELEPHOTO, galaga());

        assertFalse(support.isAvailable());
        assertTrue(support.reason().contains("not verified"));
        assertFalse(backend.resolve(OpticalRoute.TELEPHOTO, galaga()).isPresent());
    }

    @Test
    public void authorizedProbeResolvesEveryRecoveredEndpoint() {
        SystemEndpointAccess authorized = new SystemEndpointAccess() {
            @Override
            public boolean canOpen(String cameraId, DeviceCapabilitySnapshot capabilities) {
                return capabilities.isGalaga() && Arrays.asList("0", "2", "3").contains(cameraId);
            }

            @Override
            public String evidence() {
                return "controlled privileged probe";
            }
        };
        GalagaSystemCameraBackend backend = new GalagaSystemCameraBackend(authorized);

        ResolvedCameraEndpoint ultrawide = backend.resolve(
                OpticalRoute.ULTRAWIDE,
                galaga()
        ).orElseThrow(AssertionError::new);
        ResolvedCameraEndpoint wide = backend.resolve(
                OpticalRoute.MAIN,
                galaga()
        ).orElseThrow(AssertionError::new);
        ResolvedCameraEndpoint telephoto = backend.resolve(
                OpticalRoute.TELEPHOTO,
                galaga()
        ).orElseThrow(AssertionError::new);

        assertEquals("2", ultrawide.cameraId());
        assertEquals("0", wide.cameraId());
        assertEquals("3", telephoto.cameraId());
        assertEquals(RouteMechanism.SYSTEM_CAMERA, telephoto.mechanism());
    }

    @Test
    public void systemBackendWinsOnlyAfterAuthorization() {
        SystemEndpointAccess authorized = new SystemEndpointAccess() {
            @Override
            public boolean canOpen(String cameraId, DeviceCapabilitySnapshot capabilities) {
                return true;
            }

            @Override
            public String evidence() {
                return "test authorization";
            }
        };
        RouteNegotiator negotiator = new RouteNegotiator(Arrays.asList(
                new com.phone2pro.camera.backend.PublicMainBackend(),
                new GalagaSystemCameraBackend(authorized)
        ));

        RouteDecision decision = negotiator.select(OpticalRoute.MAIN, galaga());

        assertEquals(GalagaSystemCameraBackend.BACKEND_ID, decision.backendId());
        assertEquals("0", decision.endpoint().orElseThrow(AssertionError::new).cameraId());
    }
}
