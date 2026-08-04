package com.phone2pro.camera.vendor;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.phone2pro.camera.core.EvidenceConfidence;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.RouteRendering;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;

public final class VendorExtensionAdapterTest {
    private static final String FEATURE = "mediatek.test.feature";
    private static final VendorBuildIdentity BUILD = new VendorBuildIdentity(
            "Nothing",
            "A001",
            "Galaga",
            "Nothing/GalagaEEA/Galaga:16/test:user/release-keys"
    );
    private static final PublicFallbackConfiguration FALLBACK =
            PublicFallbackConfiguration.galagaMain();

    @Test
    public void exactBuildAndVerifiedProbeEnableVendorConfiguration() {
        VendorExtensionPlanner planner = planner();
        VendorExtensionPlan plan = planner.plan(FEATURE, BUILD, supportedProbe());

        assertEquals(VendorPlanOutcome.VENDOR_ENABLED, plan.outcome());
        assertTrue(plan.vendorPolicy().isPresent());
        assertEquals("0", plan.fallback().cameraId());
        assertEquals(OpticalRoute.MAIN, plan.fallback().route());
        assertEquals(RouteRendering.OPTICAL, plan.fallback().rendering());
    }

    @Test
    public void missingPolicyBuildOrProbeAlwaysUsesPublicFallback() {
        VendorExtensionPlanner planner = planner();
        VendorBuildIdentity otherBuild = new VendorBuildIdentity(
                "Nothing",
                "A001",
                "Galaga",
                "Nothing/GalagaEEA/Galaga:16/other:user/release-keys"
        );

        assertFallback(planner.plan("unknown.feature", BUILD, null));
        assertFallback(planner.plan(FEATURE, otherBuild, supportedProbe()));
        assertFallback(planner.plan(FEATURE, BUILD, null));
        assertFallback(planner.plan(
                FEATURE,
                BUILD,
                new VendorProbeResult(
                        FEATURE,
                        otherBuild,
                        VendorProbeStatus.VERIFIED_SUPPORTED,
                        EvidenceConfidence.VERIFIED,
                        "different build"
                )
        ));
    }

    @Test
    public void everyNonVerifiedProbeStatusFallsBack() {
        VendorExtensionPlanner planner = planner();
        for (VendorProbeStatus status : VendorProbeStatus.values()) {
            if (status == VendorProbeStatus.VERIFIED_SUPPORTED) {
                continue;
            }
            VendorExtensionPlan plan = planner.plan(
                    FEATURE,
                    BUILD,
                    new VendorProbeResult(
                            FEATURE,
                            BUILD,
                            status,
                            EvidenceConfidence.UNKNOWN,
                            "probe result " + status
                    )
            );
            assertFallback(plan);
            assertTrue(plan.reason().contains(status.name()));
        }
    }

    @Test
    public void verifiedSupportedRequiresVerifiedEvidence() {
        expectIllegalArgument(() -> new VendorProbeResult(
                FEATURE,
                BUILD,
                VendorProbeStatus.VERIFIED_SUPPORTED,
                EvidenceConfidence.PARTIALLY_VERIFIED,
                "insufficient evidence"
        ));
    }

    @Test
    public void sessionAndPerFrameScopesCannotBeMixed() {
        VendorSetting<Integer> session = new VendorSetting<>(
                "com.mediatek.session.mode",
                Integer.class,
                1,
                VendorSettingScope.SESSION
        );
        VendorSetting<Integer> perFrame = new VendorSetting<>(
                "com.mediatek.request.mode",
                Integer.class,
                2,
                VendorSettingScope.PER_FRAME
        );
        VendorConfiguration configuration = new VendorConfiguration(
                Collections.singletonList(session),
                Collections.singletonList(perFrame)
        );
        assertEquals(
                Collections.singletonList(session),
                configuration.settingsFor(VendorSettingScope.SESSION)
        );
        assertEquals(
                Collections.singletonList(perFrame),
                configuration.settingsFor(VendorSettingScope.PER_FRAME)
        );

        expectIllegalArgument(() -> new VendorConfiguration(
                Collections.singletonList(perFrame),
                Collections.emptyList()
        ));
        expectIllegalArgument(() -> new VendorConfiguration(
                Collections.emptyList(),
                Collections.singletonList(session)
        ));
    }

    @Test
    public void allRuntimeFailuresFallBackToKnownPublicConfiguration() {
        VendorExtensionPlan plan = planner().plan(FEATURE, BUILD, supportedProbe());
        VendorFallbackPolicy fallbackPolicy = new VendorFallbackPolicy();
        for (VendorExecutionStatus status : VendorExecutionStatus.values()) {
            if (status == VendorExecutionStatus.APPLIED_AND_VERIFIED) {
                continue;
            }
            VendorRuntimeDecision decision = fallbackPolicy.decide(
                    plan,
                    new VendorExecutionResult(status, 100L, "runtime " + status)
            );
            assertFalse(decision.vendorActive());
            assertEquals("public-main-camera2", decision.fallback().backendId());
            assertEquals("0", decision.fallback().cameraId());
            assertFalse(decision.activePolicy().isPresent());
        }
    }

    @Test
    public void timeoutFallsBackEvenWhenVendorReportedSuccess() {
        VendorExtensionPlan plan = planner().plan(FEATURE, BUILD, supportedProbe());
        VendorRuntimeDecision decision = new VendorFallbackPolicy().decide(
                plan,
                new VendorExecutionResult(
                        VendorExecutionStatus.APPLIED_AND_VERIFIED,
                        501L,
                        "late result"
                )
        );

        assertFalse(decision.vendorActive());
        assertTrue(decision.reason().contains("exceeded"));
    }

    @Test
    public void verifiedRuntimeWithinTimeoutKeepsVendorActive() {
        VendorExtensionPlan plan = planner().plan(FEATURE, BUILD, supportedProbe());
        VendorRuntimeDecision decision = new VendorFallbackPolicy().decide(
                plan,
                new VendorExecutionResult(
                        VendorExecutionStatus.APPLIED_AND_VERIFIED,
                        250L,
                        "expected result metadata observed"
                )
        );

        assertTrue(decision.vendorActive());
        assertTrue(decision.activePolicy().isPresent());
        assertEquals(FEATURE, decision.activePolicy().get().featureId());
    }

    @Test
    public void alreadyFallbackPlanNeverRequiresRuntimeResult() {
        VendorExtensionPlan plan = planner().plan(FEATURE, BUILD, null);
        VendorRuntimeDecision decision = new VendorFallbackPolicy().decide(plan, null);

        assertFalse(decision.vendorActive());
        assertEquals("0", decision.fallback().cameraId());
    }

    private static VendorExtensionPlanner planner() {
        VendorSetting<Integer> session = new VendorSetting<>(
                "com.mediatek.session.mode",
                Integer.class,
                1,
                VendorSettingScope.SESSION
        );
        VendorSetting<Integer> request = new VendorSetting<>(
                "com.mediatek.request.mode",
                Integer.class,
                2,
                VendorSettingScope.PER_FRAME
        );
        VendorFeaturePolicy policy = new VendorFeaturePolicy(
                FEATURE,
                Collections.singletonList(BUILD),
                new VendorConfiguration(
                        Collections.singletonList(session),
                        Collections.singletonList(request)
                ),
                500L
        );
        return new VendorExtensionPlanner(
                Arrays.asList(policy),
                FALLBACK
        );
    }

    private static VendorProbeResult supportedProbe() {
        return new VendorProbeResult(
                FEATURE,
                BUILD,
                VendorProbeStatus.VERIFIED_SUPPORTED,
                EvidenceConfidence.VERIFIED,
                "isolated positive and negative probe with effective result"
        );
    }

    private static void assertFallback(VendorExtensionPlan plan) {
        assertEquals(VendorPlanOutcome.PUBLIC_FALLBACK, plan.outcome());
        assertFalse(plan.vendorPolicy().isPresent());
        assertEquals("public-main-camera2", plan.fallback().backendId());
        assertEquals("0", plan.fallback().cameraId());
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
