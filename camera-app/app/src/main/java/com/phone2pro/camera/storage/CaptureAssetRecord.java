package com.phone2pro.camera.storage;

import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.OpticalRoute;

import java.util.Objects;
import java.util.Optional;

/** Durable journal record for one pending or published capture asset. */
public final class CaptureAssetRecord {
    private final String assetId;
    private final String contentUri;
    private final String displayName;
    private final String mimeType;
    private final OpticalRoute route;
    private final CaptureProfile profile;
    private final int orientationDegrees;
    private final AssetLifecycle lifecycle;
    private final boolean durableSourceAvailable;
    private final long updatedAtEpochMillis;
    private final String failureReason;

    public CaptureAssetRecord(
            String assetId,
            String contentUri,
            String displayName,
            String mimeType,
            OpticalRoute route,
            CaptureProfile profile,
            int orientationDegrees,
            AssetLifecycle lifecycle,
            boolean durableSourceAvailable,
            long updatedAtEpochMillis,
            String failureReason
    ) {
        this.assetId = requireText(assetId, "assetId");
        this.contentUri = requireText(contentUri, "contentUri");
        this.displayName = requireText(displayName, "displayName");
        this.mimeType = requireText(mimeType, "mimeType");
        this.route = Objects.requireNonNull(route, "route");
        this.profile = Objects.requireNonNull(profile, "profile");
        if (orientationDegrees != 0 && orientationDegrees != 90
                && orientationDegrees != 180 && orientationDegrees != 270) {
            throw new IllegalArgumentException("orientation must be 0, 90, 180 or 270 degrees");
        }
        this.lifecycle = Objects.requireNonNull(lifecycle, "lifecycle");
        if (updatedAtEpochMillis < 0) {
            throw new IllegalArgumentException("updatedAtEpochMillis must be non-negative");
        }
        if (lifecycle == AssetLifecycle.FAILED && (failureReason == null || failureReason.isEmpty())) {
            throw new IllegalArgumentException("failed asset requires a failure reason");
        }
        if (lifecycle != AssetLifecycle.FAILED && failureReason != null) {
            throw new IllegalArgumentException("failure reason is only valid for FAILED assets");
        }
        this.orientationDegrees = orientationDegrees;
        this.durableSourceAvailable = durableSourceAvailable;
        this.updatedAtEpochMillis = updatedAtEpochMillis;
        this.failureReason = failureReason;
    }

    public static CaptureAssetRecord reserved(
            String assetId,
            String contentUri,
            String displayName,
            String mimeType,
            OpticalRoute route,
            CaptureProfile profile,
            int orientationDegrees,
            long nowEpochMillis
    ) {
        return new CaptureAssetRecord(
                assetId,
                contentUri,
                displayName,
                mimeType,
                route,
                profile,
                orientationDegrees,
                AssetLifecycle.RESERVED_PENDING,
                false,
                nowEpochMillis,
                null
        );
    }

    public CaptureAssetRecord transition(
            AssetLifecycle next,
            boolean hasDurableSource,
            long nowEpochMillis,
            String reason
    ) {
        return new CaptureAssetRecord(
                assetId,
                contentUri,
                displayName,
                mimeType,
                route,
                profile,
                orientationDegrees,
                next,
                hasDurableSource,
                nowEpochMillis,
                reason
        );
    }

    public String assetId() { return assetId; }
    public String contentUri() { return contentUri; }
    public String displayName() { return displayName; }
    public String mimeType() { return mimeType; }
    public OpticalRoute route() { return route; }
    public CaptureProfile profile() { return profile; }
    public int orientationDegrees() { return orientationDegrees; }
    public AssetLifecycle lifecycle() { return lifecycle; }
    public boolean durableSourceAvailable() { return durableSourceAvailable; }
    public long updatedAtEpochMillis() { return updatedAtEpochMillis; }
    public Optional<String> failureReason() { return Optional.ofNullable(failureReason); }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
