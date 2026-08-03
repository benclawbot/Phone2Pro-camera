package com.phone2pro.camera.core;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;

/** Immutable runtime capability snapshot used by route negotiation. */
public final class DeviceCapabilitySnapshot {
    private final String manufacturer;
    private final String model;
    private final String device;
    private final Set<String> publicCameraIds;

    public DeviceCapabilitySnapshot(
            String manufacturer,
            String model,
            String device,
            Set<String> publicCameraIds
    ) {
        this.manufacturer = Objects.requireNonNull(manufacturer, "manufacturer");
        this.model = Objects.requireNonNull(model, "model");
        this.device = Objects.requireNonNull(device, "device");
        this.publicCameraIds = Collections.unmodifiableSet(
                new LinkedHashSet<>(Objects.requireNonNull(publicCameraIds, "publicCameraIds"))
        );
    }

    public String manufacturer() {
        return manufacturer;
    }

    public String model() {
        return model;
    }

    public String device() {
        return device;
    }

    public Set<String> publicCameraIds() {
        return publicCameraIds;
    }

    public boolean hasPublicCameraId(String cameraId) {
        return publicCameraIds.contains(cameraId);
    }

    public boolean isGalaga() {
        return "galaga".equalsIgnoreCase(device) || "A001".equalsIgnoreCase(model);
    }
}
