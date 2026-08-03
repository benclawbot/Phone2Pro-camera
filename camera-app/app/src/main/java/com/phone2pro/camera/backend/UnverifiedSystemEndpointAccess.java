package com.phone2pro.camera.backend;

import com.phone2pro.camera.core.DeviceCapabilitySnapshot;

import java.util.Objects;

/** Fail-closed policy used until a lawful, reproducible system-camera access path is verified. */
public final class UnverifiedSystemEndpointAccess implements SystemEndpointAccess {
    private final String reason;

    public UnverifiedSystemEndpointAccess(String reason) {
        this.reason = Objects.requireNonNull(reason, "reason");
    }

    @Override
    public boolean canOpen(String cameraId, DeviceCapabilitySnapshot capabilities) {
        return false;
    }

    @Override
    public String evidence() {
        return reason;
    }
}
