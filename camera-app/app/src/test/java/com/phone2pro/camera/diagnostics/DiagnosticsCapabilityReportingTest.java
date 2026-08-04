package com.phone2pro.camera.diagnostics;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.EvidenceConfidence;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.RouteMechanism;
import com.phone2pro.camera.core.RouteRendering;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.EnumSet;

public final class DiagnosticsCapabilityReportingTest {
    @Test
    public void captureReportIncludesRequiredConfigurationWithoutPixels() {
        CaptureDiagnosticReport report = report(null);
        assertEquals("public-main-camera2", report.backendId());
        assertEquals(OpticalRoute.MAIN, report.route());
        assertEquals(RouteRendering.OPTICAL, report.rendering());
        assertEquals(1, report.streams().size());
        assertEquals(2, report.configuration().size());
        assertEquals(60L, report.timings().totalMs());
        assertFalse(report.containsUserPixels());
        assertFalse(report.error().isPresent());
    }

    @Test
    public void privateUriAndPathCannotEnterConfigurationSummary() {
        expectIllegalArgument(() -> new ConfigurationEntryReport(
                ConfigurationEntryReport.Scope.SESSION,
                "example.key",
                "String",
                "content://private/image/1"
        ));
        expectIllegalArgument(() -> new ConfigurationEntryReport(
                ConfigurationEntryReport.Scope.STILL_REQUEST,
                "example.key",
                "String",
                "/storage/emulated/0/DCIM/private.jpg"
        ));
    }

    @Test
    public void unavailableReportRequiresTypedError() {
        expectIllegalArgument(() -> new CaptureDiagnosticReport(
                "report-2",
                "build",
                "1.0",
                "none",
                OpticalRoute.TELEPHOTO,
                RouteMechanism.UNAVAILABLE,
                RouteRendering.UNAVAILABLE,
                CaptureProfile.AUTO,
                Collections.emptyList(),
                Collections.emptyList(),
                new TimingReport(0, 0, 0, 0, 0, 0),
                null
        ));
        UserFacingError error = new UserFacingError(
                UserErrorCategory.UNSUPPORTED_FEATURE,
                "Telephoto is unavailable for this application build.",
                false
        );
        CaptureDiagnosticReport report = new CaptureDiagnosticReport(
                "report-2",
                "build",
                "1.0",
                "none",
                OpticalRoute.TELEPHOTO,
                RouteMechanism.UNAVAILABLE,
                RouteRendering.UNAVAILABLE,
                CaptureProfile.AUTO,
                Collections.emptyList(),
                Collections.emptyList(),
                new TimingReport(0, 0, 0, 0, 0, 0),
                error
        );
        assertEquals(UserErrorCategory.UNSUPPORTED_FEATURE, report.error().get().category());
    }

    @Test
    public void enabledFeatureCannotHaveUnknownEvidence() {
        expectIllegalArgument(() -> new FeatureFlagReport(
                "vendor-route",
                FeatureFlagState.ENABLED,
                EvidenceConfidence.UNKNOWN,
                "unknown"
        ));
        FeatureFlagReport disabled = new FeatureFlagReport(
                "vendor-route",
                FeatureFlagState.BLOCKED_BY_PROBE,
                EvidenceConfidence.UNKNOWN,
                "No verified probe result."
        );
        assertEquals(FeatureFlagState.BLOCKED_BY_PROBE, disabled.state());
    }

    @Test
    public void bugBundleIsReproducibleAndPixelFree() {
        BugBundle bundle = new BugBundle(
                "bundle-1",
                "cam-bug-v1",
                Collections.singletonList(report(null)),
                Collections.singletonList(new FeatureFlagReport(
                        "public-main",
                        FeatureFlagState.ENABLED,
                        EvidenceConfidence.VERIFIED,
                        "Camera2 ID 0 is publicly available."
                ))
        );
        assertEquals("cam-bug-v1", bundle.protocolVersion());
        assertFalse(bundle.containsUserPixels());
    }

    @Test
    public void safeFirmwarePlanExcludesRiskyModules() {
        FirmwareValidationPlan plan = FirmwareValidationPlan.safeBaseline("build");
        assertFalse(plan.explicitRiskConsent());
        assertTrue(plan.modules().contains(FirmwareValidationModule.PUBLIC_CAPABILITY_INVENTORY));
        assertTrue(plan.modules().contains(FirmwareValidationModule.BOUNDED_BURST_BENCHMARK));
        assertFalse(plan.modules().contains(FirmwareValidationModule.GUARDED_VENDOR_WRITE_PROBE));
        assertFalse(plan.modules().contains(FirmwareValidationModule.SYSTEM_CAMERA_OPEN_PROBE));
    }

    @Test
    public void riskyFirmwareModuleRequiresExplicitConsent() {
        expectIllegalArgument(() -> new FirmwareValidationPlan(
                "build",
                EnumSet.of(FirmwareValidationModule.GUARDED_VENDOR_WRITE_PROBE),
                false
        ));
        FirmwareValidationPlan plan = new FirmwareValidationPlan(
                "build",
                EnumSet.of(
                        FirmwareValidationModule.PUBLIC_CAPABILITY_INVENTORY,
                        FirmwareValidationModule.GUARDED_VENDOR_WRITE_PROBE
                ),
                true
        );
        assertTrue(plan.explicitRiskConsent());
    }

    @Test
    public void noopHookDoesNotRetainReports() {
        NoopDiagnosticHook hook = new NoopDiagnosticHook();
        hook.onCaptureReport(report(null));
        hook.onFeatureFlag(new FeatureFlagReport(
                "public-main",
                FeatureFlagState.ENABLED,
                EvidenceConfidence.VERIFIED,
                "verified"
        ));
    }

    private static CaptureDiagnosticReport report(UserFacingError error) {
        return new CaptureDiagnosticReport(
                "report-1",
                "Nothing/GalagaEEA/Galaga:16/build:user/release-keys",
                "0.1.0",
                "public-main-camera2",
                OpticalRoute.MAIN,
                RouteMechanism.PUBLIC_CAMERA,
                RouteRendering.OPTICAL,
                CaptureProfile.AUTO,
                Collections.singletonList(new StreamConfigurationReport(
                        "preview",
                        "PRIVATE",
                        1920,
                        1080,
                        3
                )),
                Arrays.asList(
                        new ConfigurationEntryReport(
                                ConfigurationEntryReport.Scope.SESSION,
                                "android.control.aeTargetFpsRange",
                                "Range<Integer>",
                                "present; value redacted"
                        ),
                        new ConfigurationEntryReport(
                                ConfigurationEntryReport.Scope.STILL_REQUEST,
                                "android.jpeg.quality",
                                "Byte",
                                "quality tier: high"
                        )
                ),
                new TimingReport(1, 2, 3, 4, 20, 30),
                error
        );
    }

    private static void expectIllegalArgument(Runnable work) {
        try {
            work.run();
            throw new AssertionError("Expected IllegalArgumentException");
        } catch (IllegalArgumentException expected) {
            // Expected.
        }
    }
}
