package com.phone2pro.camera.storage;

import java.util.Objects;

/** Gallery thumbnail target that can only be created for a published asset. */
public final class ThumbnailReference {
    private final String assetId;
    private final String contentUri;
    private final int orientationDegrees;
    private final String accessibilityLabel;

    private ThumbnailReference(
            String assetId,
            String contentUri,
            int orientationDegrees,
            String accessibilityLabel
    ) {
        this.assetId = assetId;
        this.contentUri = contentUri;
        this.orientationDegrees = orientationDegrees;
        this.accessibilityLabel = accessibilityLabel;
    }

    public static ThumbnailReference fromPublished(CaptureAssetRecord record) {
        Objects.requireNonNull(record, "record");
        if (record.lifecycle() != AssetLifecycle.PUBLISHED) {
            throw new IllegalStateException("thumbnail requires a published asset");
        }
        return new ThumbnailReference(
                record.assetId(),
                record.contentUri(),
                record.orientationDegrees(),
                "Open latest photo, " + record.route().label() + ", " + record.profile().label()
        );
    }

    public String assetId() { return assetId; }
    public String contentUri() { return contentUri; }
    public int orientationDegrees() { return orientationDegrees; }
    public String accessibilityLabel() { return accessibilityLabel; }
}
