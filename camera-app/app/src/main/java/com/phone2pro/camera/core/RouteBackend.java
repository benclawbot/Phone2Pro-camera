package com.phone2pro.camera.core;

/**
 * Capability side of a pluggable camera backend.
 *
 * <p>Session binding is intentionally kept out of this pure contract so route selection can be unit
 * tested without Android framework objects.</p>
 */
public interface RouteBackend {
    String backendId();

    int priority();

    RouteSupport evaluate(OpticalRoute route, DeviceCapabilitySnapshot capabilities);
}
