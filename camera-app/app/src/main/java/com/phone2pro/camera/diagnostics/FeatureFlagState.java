package com.phone2pro.camera.diagnostics;

/** Runtime feature flag outcome reported to diagnostics and UI. */
public enum FeatureFlagState {
    ENABLED,
    DISABLED,
    BLOCKED_BY_BUILD,
    BLOCKED_BY_CAPABILITY,
    BLOCKED_BY_PROBE,
    BLOCKED_BY_RESOURCE
}
