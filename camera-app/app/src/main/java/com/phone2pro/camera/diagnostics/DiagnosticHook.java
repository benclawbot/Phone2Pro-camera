package com.phone2pro.camera.diagnostics;

/** Optional internal observer; production defaults to a no-op implementation. */
public interface DiagnosticHook {
    void onCaptureReport(CaptureDiagnosticReport report);

    void onFeatureFlag(FeatureFlagReport featureFlag);
}
