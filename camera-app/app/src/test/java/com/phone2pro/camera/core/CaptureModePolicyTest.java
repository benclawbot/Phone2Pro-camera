package com.phone2pro.camera.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class CaptureModePolicyTest {
    @Test
    public void policiesExposeDeterministicFrameAndLatencyBounds() {
        assertPolicy(CaptureProfile.QUICK, 1, 1, 350, 1500);
        assertPolicy(CaptureProfile.AUTO, 1, 6, 500, 5000);
        assertPolicy(CaptureProfile.MAX_DETAIL, 1, 12, 800, 12000);
    }

    @Test
    public void everyEnvironmentProducesWorkWithinRequestedBounds() {
        for (CaptureProfile profile : CaptureProfile.values()) {
            CaptureModePolicy policy = profile.policy();
            for (CaptureEnvironment.Motion motion : CaptureEnvironment.Motion.values()) {
                for (CaptureEnvironment.Light light : CaptureEnvironment.Light.values()) {
                    for (CaptureEnvironment.Thermal thermal : CaptureEnvironment.Thermal.values()) {
                        for (CaptureEnvironment.Memory memory : CaptureEnvironment.Memory.values()) {
                            CapturePlan plan = profile.plan(new CaptureEnvironment(
                                    motion,
                                    light,
                                    thermal,
                                    memory
                            ));
                            assertTrue(plan.frameCount() >= policy.minFrames());
                            assertTrue(plan.frameCount() <= policy.maxFrames());
                            assertEquals(EvidenceConfidence.HYPOTHESIS, plan.latencyConfidence());
                            assertTrue(plan.stages().contains(CaptureStage.JPEG_ENCODING));
                            assertEquals(
                                    RenderingConstraint.values().length,
                                    plan.renderingConstraints().size()
                            );
                        }
                    }
                }
            }
        }
    }

    @Test
    public void quickAlwaysUsesOnePredictableFrame() {
        CapturePlan plan = CaptureProfile.QUICK.plan(new CaptureEnvironment(
                CaptureEnvironment.Motion.HIGH,
                CaptureEnvironment.Light.LOW,
                CaptureEnvironment.Thermal.HOT,
                CaptureEnvironment.Memory.CONSTRAINED
        ));

        assertEquals(CaptureProfile.QUICK, plan.effectiveProfile());
        assertEquals(1, plan.frameCount());
        assertEquals(ExposureStrategy.SINGLE_AUTO, plan.exposureStrategy());
        assertFalse(plan.stages().contains(CaptureStage.ALIGNMENT));
        assertFalse(plan.stages().contains(CaptureStage.HDR_MERGE));
        assertFalse(plan.stages().contains(CaptureStage.SUPER_RESOLUTION));
        assertTrue(plan.isDegraded());
    }

    @Test
    public void autoLowLightUsesBoundedAlignedBracket() {
        CapturePlan plan = CaptureProfile.AUTO.plan(new CaptureEnvironment(
                CaptureEnvironment.Motion.LOW,
                CaptureEnvironment.Light.LOW,
                CaptureEnvironment.Thermal.NOMINAL,
                CaptureEnvironment.Memory.NORMAL
        ));

        assertEquals(CaptureProfile.AUTO, plan.effectiveProfile());
        assertEquals(6, plan.frameCount());
        assertEquals(ExposureStrategy.LOW_LIGHT_BRACKET, plan.exposureStrategy());
        assertTrue(plan.stages().contains(CaptureStage.FRAME_SCORING));
        assertTrue(plan.stages().contains(CaptureStage.ALIGNMENT));
        assertTrue(plan.stages().contains(CaptureStage.HDR_MERGE));
        assertFalse(plan.stages().contains(CaptureStage.SUPER_RESOLUTION));
        assertFalse(plan.isDegraded());
    }

    @Test
    public void highMotionMaxDetailFallsBackToAutoCompatiblePlan() {
        CapturePlan plan = CaptureProfile.MAX_DETAIL.plan(new CaptureEnvironment(
                CaptureEnvironment.Motion.HIGH,
                CaptureEnvironment.Light.BRIGHT,
                CaptureEnvironment.Thermal.NOMINAL,
                CaptureEnvironment.Memory.NORMAL
        ));

        assertEquals(CaptureProfile.MAX_DETAIL, plan.requestedProfile());
        assertEquals(CaptureProfile.AUTO, plan.effectiveProfile());
        assertEquals(2, plan.frameCount());
        assertEquals(ExposureStrategy.SHORT_EXPOSURE_BURST, plan.exposureStrategy());
        assertTrue(plan.degradationReasons().contains(DegradationReason.HIGH_MOTION));
        assertFalse(plan.stages().contains(CaptureStage.HDR_MERGE));
        assertFalse(plan.stages().contains(CaptureStage.SUPER_RESOLUTION));
        assertTrue(plan.userSummary().contains("Auto-compatible"));
    }

    @Test
    public void nominalMaxDetailEnablesConservativeSuperResolution() {
        CapturePlan plan = CaptureProfile.MAX_DETAIL.plan(CaptureEnvironment.nominal());

        assertEquals(CaptureProfile.MAX_DETAIL, plan.effectiveProfile());
        assertEquals(10, plan.frameCount());
        assertEquals(ExposureStrategy.DETAIL_BURST, plan.exposureStrategy());
        assertTrue(plan.stages().contains(CaptureStage.SUPER_RESOLUTION));
        assertTrue(plan.stages().contains(CaptureStage.HDR_MERGE));
        assertFalse(plan.isDegraded());
        assertTrue(
                plan.renderingConstraints().contains(
                        RenderingConstraint.PREFER_DEGHOSTING_OVER_DETAIL
                )
        );
        assertTrue(
                plan.renderingConstraints().contains(
                        RenderingConstraint.AVOID_SYNTHETIC_TEXTURE
                )
        );
    }

    @Test
    public void hotOrMemoryConstrainedMaxDetailCapsWorkAndDisablesSuperResolution() {
        CapturePlan hot = CaptureProfile.MAX_DETAIL.plan(new CaptureEnvironment(
                CaptureEnvironment.Motion.LOW,
                CaptureEnvironment.Light.NORMAL,
                CaptureEnvironment.Thermal.HOT,
                CaptureEnvironment.Memory.NORMAL
        ));
        CapturePlan constrained = CaptureProfile.MAX_DETAIL.plan(new CaptureEnvironment(
                CaptureEnvironment.Motion.LOW,
                CaptureEnvironment.Light.NORMAL,
                CaptureEnvironment.Thermal.NOMINAL,
                CaptureEnvironment.Memory.CONSTRAINED
        ));

        assertEquals(CaptureProfile.AUTO, hot.effectiveProfile());
        assertEquals(3, hot.frameCount());
        assertTrue(hot.degradationReasons().contains(DegradationReason.THERMAL_HOT));
        assertFalse(hot.stages().contains(CaptureStage.SUPER_RESOLUTION));

        assertEquals(CaptureProfile.AUTO, constrained.effectiveProfile());
        assertEquals(4, constrained.frameCount());
        assertTrue(
                constrained.degradationReasons().contains(
                        DegradationReason.MEMORY_CONSTRAINED
                )
        );
        assertFalse(constrained.stages().contains(CaptureStage.SUPER_RESOLUTION));
    }

    @Test
    public void criticalResourcesAlwaysFallBackToQuick() {
        CapturePlan thermal = CaptureProfile.MAX_DETAIL.plan(new CaptureEnvironment(
                CaptureEnvironment.Motion.LOW,
                CaptureEnvironment.Light.LOW,
                CaptureEnvironment.Thermal.CRITICAL,
                CaptureEnvironment.Memory.NORMAL
        ));
        CapturePlan memory = CaptureProfile.AUTO.plan(new CaptureEnvironment(
                CaptureEnvironment.Motion.LOW,
                CaptureEnvironment.Light.NORMAL,
                CaptureEnvironment.Thermal.NOMINAL,
                CaptureEnvironment.Memory.CRITICAL
        ));

        assertQuickFallback(thermal, DegradationReason.THERMAL_CRITICAL);
        assertQuickFallback(memory, DegradationReason.MEMORY_CRITICAL);
    }

    @Test
    public void planningIsDeterministicForIdenticalInputs() {
        CaptureEnvironment environment = new CaptureEnvironment(
                CaptureEnvironment.Motion.MODERATE,
                CaptureEnvironment.Light.LOW,
                CaptureEnvironment.Thermal.WARM,
                CaptureEnvironment.Memory.CONSTRAINED
        );

        CapturePlan first = CaptureProfile.MAX_DETAIL.plan(environment);
        CapturePlan second = CaptureProfile.MAX_DETAIL.plan(environment);

        assertEquals(first.effectiveProfile(), second.effectiveProfile());
        assertEquals(first.frameCount(), second.frameCount());
        assertEquals(first.exposureStrategy(), second.exposureStrategy());
        assertEquals(first.stages(), second.stages());
        assertEquals(first.degradationReasons(), second.degradationReasons());
        assertEquals(first.userSummary(), second.userSummary());
    }

    private static void assertPolicy(
            CaptureProfile profile,
            int minimum,
            int maximum,
            int shutterLatencyMs,
            int processingLatencyMs
    ) {
        CaptureModePolicy policy = profile.policy();
        assertEquals(minimum, policy.minFrames());
        assertEquals(maximum, policy.maxFrames());
        assertEquals(shutterLatencyMs, policy.shutterLatencyTargetMs());
        assertEquals(processingLatencyMs, policy.processingLatencyTargetMs());
        assertEquals(EvidenceConfidence.HYPOTHESIS, policy.latencyConfidence());
    }

    private static void assertQuickFallback(
            CapturePlan plan,
            DegradationReason reason
    ) {
        assertEquals(CaptureProfile.QUICK, plan.effectiveProfile());
        assertEquals(1, plan.frameCount());
        assertEquals(ExposureStrategy.SINGLE_AUTO, plan.exposureStrategy());
        assertTrue(plan.degradationReasons().contains(reason));
        assertTrue(plan.isDegraded());
    }
}
