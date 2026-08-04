package com.phone2pro.camera.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class RouteSupportTest {
    @Test
    public void unavailableDecisionClearsMechanismAndRendering() {
        RouteSupport support = RouteSupport.unavailable("No verified route");

        assertFalse(support.isAvailable());
        assertEquals(RouteMechanism.UNAVAILABLE, support.mechanism());
        assertEquals(RouteRendering.UNAVAILABLE, support.rendering());
    }

    @Test
    public void availableDecisionKeepsTransportAndRenderingIndependent() {
        RouteSupport support = RouteSupport.available(
                RouteMechanism.PUBLIC_VENDOR_SAT,
                RouteRendering.IN_SENSOR,
                "Verified in-sensor route"
        );

        assertTrue(support.isAvailable());
        assertEquals(RouteMechanism.PUBLIC_VENDOR_SAT, support.mechanism());
        assertEquals(RouteRendering.IN_SENSOR, support.rendering());
    }

    @Test(expected = IllegalArgumentException.class)
    public void availableRouteCannotUseUnavailableRendering() {
        RouteSupport.available(
                RouteMechanism.PUBLIC_CAMERA,
                RouteRendering.UNAVAILABLE,
                "Invalid"
        );
    }

    @Test(expected = IllegalArgumentException.class)
    public void availableRouteCannotUseUnavailableMechanism() {
        RouteSupport.available(
                RouteMechanism.UNAVAILABLE,
                RouteRendering.OPTICAL,
                "Invalid"
        );
    }
}
