package com.phone2pro.camera.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.phone2pro.camera.backend.PublicMainBackend;

import org.junit.Test;

import java.util.Collections;
import java.util.LinkedHashSet;

public final class RouteNegotiatorTest {
    private static DeviceCapabilitySnapshot galagaWithPublicMain() {
        return new DeviceCapabilitySnapshot(
                "Nothing",
                "A001",
                "Galaga",
                new LinkedHashSet<>(Collections.singletonList("0"))
        );
    }

    @Test
    public void mainRouteUsesVerifiedPublicCamera() {
        RouteNegotiator negotiator = new RouteNegotiator(
                Collections.singletonList(new PublicMainBackend())
        );

        RouteDecision decision = negotiator.select(
                OpticalRoute.MAIN,
                galagaWithPublicMain()
        );

        assertTrue(decision.support().isAvailable());
        assertEquals(PublicMainBackend.BACKEND_ID, decision.backendId());
        assertEquals(RouteMechanism.PUBLIC_CAMERA, decision.support().mechanism());
    }

    @Test
    public void ultrawideDoesNotFallBackToDigitalCrop() {
        RouteNegotiator negotiator = new RouteNegotiator(
                Collections.singletonList(new PublicMainBackend())
        );

        RouteDecision decision = negotiator.select(
                OpticalRoute.ULTRAWIDE,
                galagaWithPublicMain()
        );

        assertFalse(decision.support().isAvailable());
        assertEquals(RouteMechanism.UNAVAILABLE, decision.support().mechanism());
        assertTrue(decision.support().reason().contains("digital crop"));
    }

    @Test
    public void higherPriorityVerifiedBackendWins() {
        RouteBackend lowerPriority = new FakeBackend(
                "lower",
                10,
                RouteSupport.available(RouteMechanism.STOCK_CAMERA_HANDOFF, "handoff")
        );
        RouteBackend higherPriority = new FakeBackend(
                "higher",
                20,
                RouteSupport.available(RouteMechanism.PUBLIC_VENDOR_SAT, "verified vendor route")
        );
        RouteNegotiator negotiator = new RouteNegotiator(
                java.util.Arrays.asList(lowerPriority, higherPriority)
        );

        RouteDecision decision = negotiator.select(
                OpticalRoute.TELEPHOTO,
                galagaWithPublicMain()
        );

        assertEquals("higher", decision.backendId());
        assertEquals(RouteMechanism.PUBLIC_VENDOR_SAT, decision.support().mechanism());
    }

    private static final class FakeBackend implements RouteBackend {
        private final String id;
        private final int priority;
        private final RouteSupport support;

        private FakeBackend(String id, int priority, RouteSupport support) {
            this.id = id;
            this.priority = priority;
            this.support = support;
        }

        @Override
        public String backendId() {
            return id;
        }

        @Override
        public int priority() {
            return priority;
        }

        @Override
        public RouteSupport evaluate(
                OpticalRoute route,
                DeviceCapabilitySnapshot capabilities
        ) {
            return support;
        }
    }
}
