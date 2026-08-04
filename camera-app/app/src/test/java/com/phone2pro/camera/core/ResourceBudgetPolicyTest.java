package com.phone2pro.camera.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class ResourceBudgetPolicyTest {
    private static final long MIB = 1024L * 1024L;
    private final ResourceBudgetPolicy policy = new ResourceBudgetPolicy();

    @Test
    public void baseBudgetsDefineAllRequiredLimits() {
        CaptureResourceBudget quick = policy.baseBudget(CaptureProfile.QUICK);
        CaptureResourceBudget auto = policy.baseBudget(CaptureProfile.AUTO);
        CaptureResourceBudget max = policy.baseBudget(CaptureProfile.MAX_DETAIL);

        assertEquals(1, quick.maxFrames());
        assertEquals(6, auto.maxFrames());
        assertEquals(12, max.maxFrames());
        assertTrue(quick.maxInFlightBuffers() >= quick.maxFrames());
        assertTrue(auto.maxInFlightBuffers() >= auto.maxFrames());
        assertTrue(max.maxInFlightBuffers() >= max.maxFrames());
        assertTrue(quick.maxFrameBytes() > 0);
        assertTrue(auto.maxIntermediateBytes() > quick.maxIntermediateBytes());
        assertTrue(max.maxIntermediateBytes() > auto.maxIntermediateBytes());
        assertTrue(quick.shutterLatencyTargetMs() < auto.shutterLatencyTargetMs());
        assertTrue(auto.processingLatencyTargetMs() < max.processingLatencyTargetMs());
        assertTrue(quick.sustainedCapturesPerMinute() > auto.sustainedCapturesPerMinute());
        assertTrue(auto.sustainedCapturesPerMinute() > max.sustainedCapturesPerMinute());
        assertEquals(EvidenceConfidence.HYPOTHESIS, max.confidence());
    }

    @Test
    public void nominalResourcesPreserveRequestedModes() {
        for (CaptureProfile profile : CaptureProfile.values()) {
            ResourceBudgetDecision decision = policy.decide(
                    profile,
                    state(CaptureEnvironment.Thermal.NOMINAL, BatteryState.NORMAL, 4_096)
            );
            assertTrue(decision.captureAllowed());
            assertEquals(profile, decision.effectiveBudget().profile());
            assertFalse(decision.degraded());
        }
    }

    @Test
    public void thermalAndBatteryLadderIsDeterministic() {
        ResourceBudgetDecision warmMax = policy.decide(
                CaptureProfile.MAX_DETAIL,
                state(CaptureEnvironment.Thermal.WARM, BatteryState.NORMAL, 4_096)
        );
        assertEquals(CaptureProfile.AUTO, warmMax.effectiveBudget().profile());
        assertTrue(warmMax.degradations().contains(BudgetDegradationReason.THERMAL_WARM));
        assertTrue(warmMax.effectiveBudget().cooldownAfterBurstMs() >= 3_000);

        ResourceBudgetDecision hotMax = policy.decide(
                CaptureProfile.MAX_DETAIL,
                state(CaptureEnvironment.Thermal.HOT, BatteryState.NORMAL, 4_096)
        );
        assertEquals(CaptureProfile.QUICK, hotMax.effectiveBudget().profile());
        assertTrue(hotMax.effectiveBudget().sustainedCapturesPerMinute() <= 2);

        ResourceBudgetDecision lowBattery = policy.decide(
                CaptureProfile.MAX_DETAIL,
                state(CaptureEnvironment.Thermal.NOMINAL, BatteryState.LOW, 4_096)
        );
        assertEquals(CaptureProfile.AUTO, lowBattery.effectiveBudget().profile());
        assertTrue(lowBattery.degradations().contains(BudgetDegradationReason.BATTERY_LOW));

        ResourceBudgetDecision criticalBattery = policy.decide(
                CaptureProfile.AUTO,
                state(CaptureEnvironment.Thermal.NOMINAL, BatteryState.CRITICAL, 4_096)
        );
        assertEquals(CaptureProfile.QUICK, criticalBattery.effectiveBudget().profile());
        assertEquals(1, criticalBattery.effectiveBudget().sustainedCapturesPerMinute());
        assertTrue(criticalBattery.effectiveBudget().cooldownAfterBurstMs() >= 30_000);
    }

    @Test
    public void memoryHeadroomDegradesBeforeBlocking() {
        ResourceBudgetDecision maxToAuto = policy.decide(
                CaptureProfile.MAX_DETAIL,
                state(CaptureEnvironment.Thermal.NOMINAL, BatteryState.NORMAL, 900)
        );
        assertEquals(CaptureProfile.AUTO, maxToAuto.effectiveBudget().profile());
        assertTrue(maxToAuto.captureAllowed());
        assertTrue(maxToAuto.degradations().contains(BudgetDegradationReason.MEMORY_HEADROOM));

        ResourceBudgetDecision autoToQuick = policy.decide(
                CaptureProfile.AUTO,
                state(CaptureEnvironment.Thermal.NOMINAL, BatteryState.NORMAL, 300)
        );
        assertEquals(CaptureProfile.QUICK, autoToQuick.effectiveBudget().profile());
        assertTrue(autoToQuick.captureAllowed());

        ResourceBudgetDecision blocked = policy.decide(
                CaptureProfile.QUICK,
                state(CaptureEnvironment.Thermal.NOMINAL, BatteryState.NORMAL, 100)
        );
        assertFalse(blocked.captureAllowed());
        assertTrue(blocked.degradations().contains(BudgetDegradationReason.CAPTURE_BLOCKED));
        assertTrue(blocked.userSummary().contains("insufficient memory"));
    }

    @Test
    public void everyProfileAndResourceCombinationRespectsInvariants() {
        for (CaptureProfile profile : CaptureProfile.values()) {
            for (CaptureEnvironment.Thermal thermal : CaptureEnvironment.Thermal.values()) {
                for (BatteryState battery : BatteryState.values()) {
                    for (long memoryMib : new long[]{100, 300, 900, 4_096}) {
                        ResourceBudgetDecision decision = policy.decide(
                                profile,
                                state(thermal, battery, memoryMib)
                        );
                        CaptureResourceBudget budget = decision.effectiveBudget();
                        assertTrue(budget.maxFrames() > 0);
                        assertTrue(budget.maxInFlightBuffers() >= budget.maxFrames());
                        assertTrue(budget.maximumWorkingSetBytes() > 0);
                        assertTrue(budget.shutterLatencyTargetMs() > 0);
                        assertTrue(budget.processingLatencyTargetMs() > 0);
                        assertTrue(budget.sustainedCapturesPerMinute() > 0);
                        assertFalse(decision.userSummary().isEmpty());
                        if (!decision.captureAllowed()) {
                            assertTrue(decision.degradations().contains(
                                    BudgetDegradationReason.CAPTURE_BLOCKED
                            ));
                        }
                    }
                }
            }
        }
    }

    @Test
    public void performanceSampleAtLimitsPasses() {
        CaptureResourceBudget budget = policy.baseBudget(CaptureProfile.AUTO);
        ResourcePerformanceSample sample = new ResourcePerformanceSample(
                budget.maxFrames(),
                budget.maxInFlightBuffers(),
                budget.maximumWorkingSetBytes(),
                budget.maxQueuedCaptures(),
                budget.shutterLatencyTargetMs(),
                budget.processingLatencyTargetMs(),
                budget.sustainedCapturesPerMinute()
        );

        ResourceBudgetCompliance compliance = ResourceBudgetCompliance.evaluate(budget, sample);
        assertTrue(compliance.passes());
        assertTrue(compliance.violations().isEmpty());
    }

    @Test
    public void performanceViolationsAreReportedIndependently() {
        CaptureResourceBudget budget = policy.baseBudget(CaptureProfile.QUICK);
        ResourcePerformanceSample sample = new ResourcePerformanceSample(
                budget.maxFrames() + 1,
                budget.maxInFlightBuffers() + 1,
                budget.maximumWorkingSetBytes() + 1,
                budget.maxQueuedCaptures() + 1,
                budget.shutterLatencyTargetMs() + 1,
                budget.processingLatencyTargetMs() + 1,
                budget.sustainedCapturesPerMinute() + 1
        );

        ResourceBudgetCompliance compliance = ResourceBudgetCompliance.evaluate(budget, sample);
        assertFalse(compliance.passes());
        assertEquals(ResourceBudgetViolation.values().length, compliance.violations().size());
        for (ResourceBudgetViolation violation : ResourceBudgetViolation.values()) {
            assertTrue(compliance.violations().contains(violation));
        }
    }

    private static ResourceState state(
            CaptureEnvironment.Thermal thermal,
            BatteryState battery,
            long memoryMib
    ) {
        return new ResourceState(thermal, battery, memoryMib * MIB);
    }
}
