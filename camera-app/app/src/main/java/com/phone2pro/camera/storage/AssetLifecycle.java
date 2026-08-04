package com.phone2pro.camera.storage;

/** Persisted still-image lifecycle; only PUBLISHED assets may be shown outside the app. */
public enum AssetLifecycle {
    RESERVED_PENDING,
    WRITING,
    PROCESSING,
    READY_TO_PUBLISH,
    PUBLISHED,
    FAILED,
    ABANDONED;

    public boolean visibleToOtherApps() {
        return this == PUBLISHED;
    }

    public boolean terminal() {
        return this == PUBLISHED || this == FAILED || this == ABANDONED;
    }
}
