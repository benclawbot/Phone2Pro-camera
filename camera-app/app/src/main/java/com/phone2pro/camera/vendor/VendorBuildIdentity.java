package com.phone2pro.camera.vendor;

import java.util.Objects;

/** Exact device and firmware identity used by vendor allowlists. */
public final class VendorBuildIdentity {
    private final String manufacturer;
    private final String model;
    private final String device;
    private final String buildFingerprint;

    public VendorBuildIdentity(
            String manufacturer,
            String model,
            String device,
            String buildFingerprint
    ) {
        this.manufacturer = requireText(manufacturer, "manufacturer");
        this.model = requireText(model, "model");
        this.device = requireText(device, "device");
        this.buildFingerprint = requireText(buildFingerprint, "buildFingerprint");
    }

    public String manufacturer() { return manufacturer; }
    public String model() { return model; }
    public String device() { return device; }
    public String buildFingerprint() { return buildFingerprint; }

    public boolean exactlyMatches(VendorBuildIdentity other) {
        return other != null
                && manufacturer.equalsIgnoreCase(other.manufacturer)
                && model.equalsIgnoreCase(other.model)
                && device.equalsIgnoreCase(other.device)
                && buildFingerprint.equals(other.buildFingerprint);
    }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
