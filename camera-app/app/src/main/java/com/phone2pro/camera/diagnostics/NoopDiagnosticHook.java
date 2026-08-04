package com.phone2pro.camera.diagnostics;

/** Default production hook when the user has not enabled diagnostics. */
public final class NoopDiagnosticHook implements DiagnosticHook {
    @Override
    public void onCaptureReport(CaptureDiagnosticReport report) {
        // Deliberately discard.
    }

    @Override
    public void onFeatureFlag(FeatureFlagReport featureFlag) {
        // Deliberately discard.
    }
}
