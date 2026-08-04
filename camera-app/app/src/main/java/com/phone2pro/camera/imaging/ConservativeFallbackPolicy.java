package com.phone2pro.camera.imaging;

import java.util.EnumSet;
import java.util.Objects;

/** Deterministic policy that prefers a natural reference frame over unstable synthesis. */
public final class ConservativeFallbackPolicy {
    private static final double MODERATE = 0.35;
    private static final double SEVERE = 0.70;

    public FallbackDecision decide(ArtifactReport report) {
        Objects.requireNonNull(report, "report");

        if (report.contains(ArtifactType.MISALIGNMENT, SEVERE)
                || report.contains(ArtifactType.GHOSTING, SEVERE)) {
            return new FallbackDecision(
                    EnumSet.of(FallbackAction.USE_REFERENCE_FRAME_ONLY),
                    "Severe motion or alignment failure makes synthesized detail unreliable."
            );
        }

        EnumSet<FallbackAction> actions = EnumSet.noneOf(FallbackAction.class);
        if (report.contains(ArtifactType.MISALIGNMENT, MODERATE)
                || report.contains(ArtifactType.GHOSTING, MODERATE)) {
            actions.add(FallbackAction.MASK_UNRELIABLE_REGIONS);
        }
        if (report.contains(ArtifactType.SYNTHETIC_TEXTURE, MODERATE)) {
            actions.add(FallbackAction.DISABLE_SUPER_RESOLUTION);
        }
        if (report.contains(ArtifactType.HALO, MODERATE)
                || report.contains(ArtifactType.RINGING, MODERATE)) {
            actions.add(FallbackAction.DISABLE_SHARPENING);
        }
        if (report.contains(ArtifactType.NOISE_AMPLIFICATION, MODERATE)) {
            actions.add(FallbackAction.REDUCE_DENOISE_STRENGTH);
        }
        if (report.contains(ArtifactType.HIGHLIGHT_CLIPPING, MODERATE)) {
            actions.add(FallbackAction.PROTECT_HIGHLIGHTS);
        }
        if (report.contains(ArtifactType.COLOR_SHIFT, SEVERE)) {
            return new FallbackDecision(
                    EnumSet.of(FallbackAction.USE_REFERENCE_FRAME_ONLY),
                    "Severe color instability cannot be corrected safely by the current result."
            );
        }
        if (actions.isEmpty()) {
            actions.add(FallbackAction.KEEP_RESULT);
            return new FallbackDecision(actions, "No material rendering artefact was detected.");
        }
        return new FallbackDecision(
                actions,
                "Risky detail stages are reduced before natural color or scene structure is altered."
        );
    }
}
