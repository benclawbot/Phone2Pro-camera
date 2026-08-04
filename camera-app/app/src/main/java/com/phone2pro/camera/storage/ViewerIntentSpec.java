package com.phone2pro.camera.storage;

import java.util.Objects;

/** Platform-neutral specification for opening the exact published asset in a system viewer. */
public final class ViewerIntentSpec {
    public static final String ACTION_VIEW = "android.intent.action.VIEW";

    private final String action;
    private final String contentUri;
    private final String mimeType;
    private final boolean grantReadPermission;

    private ViewerIntentSpec(
            String action,
            String contentUri,
            String mimeType,
            boolean grantReadPermission
    ) {
        this.action = action;
        this.contentUri = contentUri;
        this.mimeType = mimeType;
        this.grantReadPermission = grantReadPermission;
    }

    public static ViewerIntentSpec forPublished(CaptureAssetRecord record) {
        Objects.requireNonNull(record, "record");
        if (record.lifecycle() != AssetLifecycle.PUBLISHED) {
            throw new IllegalStateException("system viewer requires a published asset");
        }
        return new ViewerIntentSpec(
                ACTION_VIEW,
                record.contentUri(),
                record.mimeType(),
                true
        );
    }

    public String action() { return action; }
    public String contentUri() { return contentUri; }
    public String mimeType() { return mimeType; }
    public boolean grantReadPermission() { return grantReadPermission; }
}
