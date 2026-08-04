package com.phone2pro.camera.core;

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Objects;

/** Executable MT6878-oriented resource targets pending physical benchmark calibration. */
public final class ResourceBudgetPolicy {
    private static final long MIB = 1024L * 1024L;
    private static final double MEMORY_HEADROOM_FRACTION = 0.60;

    private final Map<CaptureProfile, CaptureResourceBudget> baseBudgets =
            new EnumMap<>(CaptureProfile.class);

    public ResourceBudgetPolicy() {
        baseBudgets.put(CaptureProfile.QUICK, new CaptureResourceBudget(
                CaptureProfile.QUICK,
                1,
                3,
                32L * MIB,
                48L * MIB,
                4,
                350,
                1500,
                20,
                0,
                EvidenceConfidence.HYPOTHESIS
        ));
        baseBudgets.put(CaptureProfile.AUTO, new CaptureResourceBudget(
                CaptureProfile.AUTO,
                6,
                8,
                32L * MIB,
                192L * MIB,
                3,
                500,
                5000,
                8,
                1000,
                EvidenceConfidence.HYPOTHESIS
        ));
        baseBudgets.put(CaptureProfile.MAX_DETAIL, new CaptureResourceBudget(
                CaptureProfile.MAX_DETAIL,
                12,
                14,
                32L * MIB,
                384L * MIB,
                1,
                800,
                12000,
                3,
                5000,
                EvidenceConfidence.HYPOTHESIS
        ));
    }

    public CaptureResourceBudget baseBudget(CaptureProfile profile) {
        CaptureResourceBudget budget = baseBudgets.get(Objects.requireNonNull(profile, "profile"));
        if (budget == null) {
            throw new IllegalArgumentException("No resource budget for " + profile);
        }
        return budget;
    }

    public ResourceBudgetDecision decide(
            CaptureProfile requestedProfile,
            ResourceState state
    ) {
        Objects.requireNonNull(requestedProfile, "requestedProfile");
        Objects.requireNonNull(state, "state");
        EnumSet<BudgetDegradationReason> reasons = EnumSet.noneOf(
                BudgetDegradationReason.class
        );
        CaptureProfile effectiveProfile = requestedProfile;

        switch (state.thermal()) {
            case WARM:
                reasons.add(BudgetDegradationReason.THERMAL_WARM);
                if (effectiveProfile == CaptureProfile.MAX_DETAIL) {
                    effectiveProfile = CaptureProfile.AUTO;
                }
                break;
            case HOT:
                reasons.add(BudgetDegradationReason.THERMAL_HOT);
                effectiveProfile = CaptureProfile.QUICK;
                break;
            case CRITICAL:
                reasons.add(BudgetDegradationReason.THERMAL_CRITICAL);
                effectiveProfile = CaptureProfile.QUICK;
                break;
            case NOMINAL:
                break;
            default:
                throw new IllegalStateException("Unhandled thermal state");
        }

        switch (state.battery()) {
            case LOW:
                reasons.add(BudgetDegradationReason.BATTERY_LOW);
                if (effectiveProfile == CaptureProfile.MAX_DETAIL) {
                    effectiveProfile = CaptureProfile.AUTO;
                }
                break;
            case CRITICAL:
                reasons.add(BudgetDegradationReason.BATTERY_CRITICAL);
                effectiveProfile = CaptureProfile.QUICK;
                break;
            case CHARGING:
            case NORMAL:
                break;
            default:
                throw new IllegalStateException("Unhandled battery state");
        }

        CaptureResourceBudget budget = baseBudget(effectiveProfile);
        while (!fitsMemoryHeadroom(budget, state.availableMemoryBytes())
                && effectiveProfile != CaptureProfile.QUICK) {
            reasons.add(BudgetDegradationReason.MEMORY_HEADROOM);
            effectiveProfile = lower(effectiveProfile);
            budget = baseBudget(effectiveProfile);
        }

        boolean allowed = fitsMemoryHeadroom(budget, state.availableMemoryBytes());
        if (!allowed) {
            reasons.add(BudgetDegradationReason.MEMORY_HEADROOM);
            reasons.add(BudgetDegradationReason.CAPTURE_BLOCKED);
        }

        budget = applySustainedLimits(budget, state);
        String summary;
        if (!allowed) {
            summary = "Capture paused: insufficient memory headroom for the Quick budget.";
        } else if (effectiveProfile != requestedProfile) {
            summary = requestedProfile.label() + " reduced to " + effectiveProfile.label()
                    + " to protect device resources.";
        } else if (!reasons.isEmpty()) {
            summary = effectiveProfile.label()
                    + " remains available with a reduced sustained-capture rate.";
        } else {
            summary = effectiveProfile.label() + " resource budget available.";
        }
        return new ResourceBudgetDecision(
                requestedProfile,
                budget,
                allowed,
                reasons,
                summary
        );
    }

    private static boolean fitsMemoryHeadroom(
            CaptureResourceBudget budget,
            long availableMemoryBytes
    ) {
        return budget.maximumWorkingSetBytes()
                <= Math.floor(availableMemoryBytes * MEMORY_HEADROOM_FRACTION);
    }

    private static CaptureProfile lower(CaptureProfile profile) {
        switch (profile) {
            case MAX_DETAIL:
                return CaptureProfile.AUTO;
            case AUTO:
            case QUICK:
                return CaptureProfile.QUICK;
            default:
                throw new IllegalStateException("Unhandled profile: " + profile);
        }
    }

    private static CaptureResourceBudget applySustainedLimits(
            CaptureResourceBudget budget,
            ResourceState state
    ) {
        int rate = budget.sustainedCapturesPerMinute();
        int cooldown = budget.cooldownAfterBurstMs();
        switch (state.thermal()) {
            case WARM:
                rate = Math.min(rate, 4);
                cooldown = Math.max(cooldown, 3000);
                break;
            case HOT:
                rate = Math.min(rate, 2);
                cooldown = Math.max(cooldown, 10000);
                break;
            case CRITICAL:
                rate = 1;
                cooldown = Math.max(cooldown, 30000);
                break;
            case NOMINAL:
                break;
            default:
                throw new IllegalStateException("Unhandled thermal state");
        }
        if (state.battery() == BatteryState.LOW) {
            rate = Math.min(rate, 4);
            cooldown = Math.max(cooldown, 5000);
        } else if (state.battery() == BatteryState.CRITICAL) {
            rate = 1;
            cooldown = Math.max(cooldown, 30000);
        }
        return new CaptureResourceBudget(
                budget.profile(),
                budget.maxFrames(),
                budget.maxInFlightBuffers(),
                budget.maxFrameBytes(),
                budget.maxIntermediateBytes(),
                budget.maxQueuedCaptures(),
                budget.shutterLatencyTargetMs(),
                budget.processingLatencyTargetMs(),
                rate,
                cooldown,
                budget.confidence()
        );
    }
}
