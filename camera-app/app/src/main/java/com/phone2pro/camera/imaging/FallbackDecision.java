package com.phone2pro.camera.imaging;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Objects;
import java.util.Set;

/** Result of evaluating artefacts against conservative rendering policy. */
public final class FallbackDecision {
    private final Set<FallbackAction> actions;
    private final String reason;

    public FallbackDecision(Set<FallbackAction> actions, String reason) {
        Objects.requireNonNull(actions, "actions");
        if (actions.isEmpty()) {
            throw new IllegalArgumentException("at least one fallback action is required");
        }
        EnumSet<FallbackAction> copy = EnumSet.copyOf(actions);
        if (copy.contains(FallbackAction.KEEP_RESULT) && copy.size() > 1) {
            throw new IllegalArgumentException("KEEP_RESULT cannot be combined with fallbacks");
        }
        if (copy.contains(FallbackAction.USE_REFERENCE_FRAME_ONLY) && copy.size() > 1) {
            copy = EnumSet.of(FallbackAction.USE_REFERENCE_FRAME_ONLY);
        }
        this.actions = Collections.unmodifiableSet(copy);
        this.reason = Objects.requireNonNull(reason, "reason");
    }

    public Set<FallbackAction> actions() { return actions; }
    public String reason() { return reason; }
    public boolean usesReferenceOnly() {
        return actions.contains(FallbackAction.USE_REFERENCE_FRAME_ONLY);
    }
}
