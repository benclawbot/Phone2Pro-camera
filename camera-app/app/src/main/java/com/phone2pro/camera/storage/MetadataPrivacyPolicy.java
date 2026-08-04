package com.phone2pro.camera.storage;

/** Explicit metadata privacy choices applied before an asset becomes visible. */
public final class MetadataPrivacyPolicy {
    private final boolean includeLocation;
    private final boolean includeDeviceIdentity;
    private final boolean includeDiagnosticMetadata;
    private final boolean includeProcessingXmp;

    public MetadataPrivacyPolicy(
            boolean includeLocation,
            boolean includeDeviceIdentity,
            boolean includeDiagnosticMetadata,
            boolean includeProcessingXmp
    ) {
        this.includeLocation = includeLocation;
        this.includeDeviceIdentity = includeDeviceIdentity;
        this.includeDiagnosticMetadata = includeDiagnosticMetadata;
        this.includeProcessingXmp = includeProcessingXmp;
    }

    public static MetadataPrivacyPolicy privateByDefault() {
        return new MetadataPrivacyPolicy(false, false, false, false);
    }

    public boolean includeLocation() { return includeLocation; }
    public boolean includeDeviceIdentity() { return includeDeviceIdentity; }
    public boolean includeDiagnosticMetadata() { return includeDiagnosticMetadata; }
    public boolean includeProcessingXmp() { return includeProcessingXmp; }
}
