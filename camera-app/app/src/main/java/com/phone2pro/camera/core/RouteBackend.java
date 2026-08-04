package com.phone2pro.camera.core;

import java.util.Optional;

/**
 * Capability side of a pluggable camera backend.
 *
 * <p>Session binding is intentionally kept out of this pure contract so route selection can be unit
 * tested without Android framework objects.</p>
 */
public interface RouteBackend {
    String backendId();

    int priority();

    /** Shared lifecycle, error and normalized metadata semantics. */
    default CameraBackendContract contract() {
        return CameraBackendContract.standard(backendId());
    }

    RouteSupport evaluate(OpticalRoute route, DeviceCapabilitySnapshot capabilities);

    /** Resolve a concrete endpoint only when this backend can safely bind one. */
    default Optional<ResolvedCameraEndpoint> resolve(
            OpticalRoute route,
            DeviceCapabilitySnapshot capabilities
    ) {
        return Optional.empty();
    }
}
