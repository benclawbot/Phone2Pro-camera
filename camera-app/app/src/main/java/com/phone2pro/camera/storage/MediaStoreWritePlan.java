package com.phone2pro.camera.storage;

import java.util.Objects;

/** MediaStore transaction parameters for one still image. */
public final class MediaStoreWritePlan {
    private final String displayName;
    private final String mimeType;
    private final String relativePath;
    private final int orientationDegrees;
    private final MetadataPrivacyPolicy privacyPolicy;

    public MediaStoreWritePlan(
            String displayName,
            String mimeType,
            String relativePath,
            int orientationDegrees,
            MetadataPrivacyPolicy privacyPolicy
    ) {
        this.displayName = requireText(displayName, "displayName");
        this.mimeType = requireText(mimeType, "mimeType");
        this.relativePath = requireText(relativePath, "relativePath");
        if (orientationDegrees != 0 && orientationDegrees != 90
                && orientationDegrees != 180 && orientationDegrees != 270) {
            throw new IllegalArgumentException("orientation must be 0, 90, 180 or 270 degrees");
        }
        this.orientationDegrees = orientationDegrees;
        this.privacyPolicy = Objects.requireNonNull(privacyPolicy, "privacyPolicy");
    }

    public String displayName() { return displayName; }
    public String mimeType() { return mimeType; }
    public String relativePath() { return relativePath; }
    public int orientationDegrees() { return orientationDegrees; }
    public MetadataPrivacyPolicy privacyPolicy() { return privacyPolicy; }

    /** Android 10+ rows must remain hidden until the complete asset is finalized. */
    public boolean reserveAsPending() { return true; }

    /** Publication is the explicit IS_PENDING=0 transition after metadata is complete. */
    public boolean publishByClearingPending() { return true; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
