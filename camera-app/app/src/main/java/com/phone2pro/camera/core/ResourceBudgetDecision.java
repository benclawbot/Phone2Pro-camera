package com.phone2pro.camera.core;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Objects;
import java.util.Set;

/** Effective capture budget after thermal, battery and memory degradation. */
public final class ResourceBudgetDecision {
    private final CaptureProfile requestedProfile;
    private final CaptureResourceBudget effectiveBudget;
    private final boolean captureAllowed;
    private final Set<BudgetDegradationReason> degradations;
    private final String userSummary;

    public ResourceBudgetDecision(
            CaptureProfile requestedProfile,
            CaptureResourceBudget effectiveBudget,
            boolean captureAllowed,
            Set<BudgetDegradationReason> degradations,
            String userSummary
    ) {
        this.requestedProfile = Objects.requireNonNull(requestedProfile, "requestedProfile");
        this.effectiveBudget = Objects.requireNonNull(effectiveBudget, "effectiveBudget");
        Objects.requireNonNull(degradations, "degradations");
        EnumSet<BudgetDegradationReason> copy = degradations.isEmpty()
                ? EnumSet.noneOf(BudgetDegradationReason.class)
                : EnumSet.copyOf(degradations);
        if (!captureAllowed && !copy.contains(BudgetDegradationReason.CAPTURE_BLOCKED)) {
            throw new IllegalArgumentException("blocked capture must record CAPTURE_BLOCKED");
        }
        if (captureAllowed && copy.contains(BudgetDegradationReason.CAPTURE_BLOCKED)) {
            throw new IllegalArgumentException("allowed capture cannot record CAPTURE_BLOCKED");
        }
        this.captureAllowed = captureAllowed;
        this.degradations = Collections.unmodifiableSet(copy);
        this.userSummary = Objects.requireNonNull(userSummary, "userSummary");
        if (userSummary.isEmpty()) {
            throw new IllegalArgumentException("userSummary must not be empty");
        }
    }

    public CaptureProfile requestedProfile() { return requestedProfile; }
    public CaptureResourceBudget effectiveBudget() { return effectiveBudget; }
    public boolean captureAllowed() { return captureAllowed; }
    public Set<BudgetDegradationReason> degradations() { return degradations; }
    public String userSummary() { return userSummary; }

    public boolean degraded() {
        return effectiveBudget.profile() != requestedProfile || !degradations.isEmpty();
    }
}
