package com.phone2pro.camera.core;

import java.util.EnumSet;
import java.util.Objects;

/** Executable product contract for Quick, Auto and Max Detail capture modes. */
public final class CaptureModePolicy {
    private static final CaptureModePolicy QUICK = new CaptureModePolicy(
            CaptureProfile.QUICK,
            1,
            1,
            350,
            1500
    );
    private static final CaptureModePolicy AUTO = new CaptureModePolicy(
            CaptureProfile.AUTO,
            1,
            6,
            500,
            5000
    );
    private static final CaptureModePolicy MAX_DETAIL = new CaptureModePolicy(
            CaptureProfile.MAX_DETAIL,
            1,
            12,
            800,
            12000
    );

    private final CaptureProfile profile;
    private final int minFrames;
    private final int maxFrames;
    private final int shutterLatencyTargetMs;
    private final int processingLatencyTargetMs;

    private CaptureModePolicy(
            CaptureProfile profile,
            int minFrames,
            int maxFrames,
            int shutterLatencyTargetMs,
            int processingLatencyTargetMs
    ) {
        this.profile = Objects.requireNonNull(profile, "profile");
        if (minFrames <= 0 || maxFrames < minFrames) {
            throw new IllegalArgumentException("Invalid frame bounds");
        }
        if (shutterLatencyTargetMs <= 0 || processingLatencyTargetMs <= 0) {
            throw new IllegalArgumentException("Latency targets must be positive");
        }
        this.minFrames = minFrames;
        this.maxFrames = maxFrames;
        this.shutterLatencyTargetMs = shutterLatencyTargetMs;
        this.processingLatencyTargetMs = processingLatencyTargetMs;
    }

    public static CaptureModePolicy forProfile(CaptureProfile profile) {
        Objects.requireNonNull(profile, "profile");
        switch (profile) {
            case QUICK:
                return QUICK;
            case AUTO:
                return AUTO;
            case MAX_DETAIL:
                return MAX_DETAIL;
            default:
                throw new IllegalArgumentException("Unknown capture profile: " + profile);
        }
    }

    public CaptureProfile profile() {
        return profile;
    }

    public int minFrames() {
        return minFrames;
    }

    public int maxFrames() {
        return maxFrames;
    }

    public int shutterLatencyTargetMs() {
        return shutterLatencyTargetMs;
    }

    public int processingLatencyTargetMs() {
        return processingLatencyTargetMs;
    }

    /** Design target pending device benchmarks, not a measured performance claim. */
    public EvidenceConfidence latencyConfidence() {
        return EvidenceConfidence.HYPOTHESIS;
    }

    public CapturePlan plan(CaptureEnvironment environment) {
        Objects.requireNonNull(environment, "environment");

        EnumSet<DegradationReason> degradations = EnumSet.noneOf(DegradationReason.class);
        addResourceDegradations(environment, degradations);
        addMotionDegradations(environment, degradations);

        if (environment.thermal() == CaptureEnvironment.Thermal.CRITICAL
                || environment.memory() == CaptureEnvironment.Memory.CRITICAL) {
            return quickPlan(
                    profile,
                    degradations,
                    "Quick fallback: capture resources are critically constrained."
            );
        }

        switch (profile) {
            case QUICK:
                return quickPlan(
                        profile,
                        degradations,
                        quickSummary(environment, degradations)
                );
            case AUTO:
                return autoPlan(environment, degradations, profile);
            case MAX_DETAIL:
                return maxDetailPlan(environment, degradations);
            default:
                throw new IllegalStateException("Unhandled capture profile: " + profile);
        }
    }

    private CapturePlan autoPlan(
            CaptureEnvironment environment,
            EnumSet<DegradationReason> degradations,
            CaptureProfile requestedProfile
    ) {
        int frames;
        switch (environment.light()) {
            case BRIGHT:
                frames = 3;
                break;
            case NORMAL:
                frames = 4;
                break;
            case LOW:
                frames = 6;
                break;
            default:
                throw new IllegalStateException("Unhandled light state");
        }

        if (environment.motion() == CaptureEnvironment.Motion.HIGH) {
            frames = Math.min(frames, 2);
        } else if (environment.motion() == CaptureEnvironment.Motion.MODERATE) {
            frames = Math.min(frames, 3);
        }
        if (environment.thermal() == CaptureEnvironment.Thermal.WARM) {
            frames = Math.min(frames, 4);
        } else if (environment.thermal() == CaptureEnvironment.Thermal.HOT) {
            frames = Math.min(frames, 2);
        }
        if (environment.memory() == CaptureEnvironment.Memory.CONSTRAINED) {
            frames = Math.min(frames, 3);
        }
        frames = clamp(frames, AUTO.minFrames, AUTO.maxFrames);

        ExposureStrategy exposure = exposureFor(environment, false);
        EnumSet<CaptureStage> stages = commonStages();
        addMultiFrameStages(stages, frames);
        if (frames >= 3 && environment.motion() != CaptureEnvironment.Motion.HIGH) {
            stages.add(CaptureStage.HDR_MERGE);
        }

        return new CapturePlan(
                requestedProfile,
                CaptureProfile.AUTO,
                frames,
                exposure,
                stages,
                naturalRenderingConstraints(),
                degradations,
                AUTO.shutterLatencyTargetMs,
                AUTO.processingLatencyTargetMs,
                AUTO.latencyConfidence(),
                autoSummary(environment, frames, degradations)
        );
    }

    private CapturePlan maxDetailPlan(
            CaptureEnvironment environment,
            EnumSet<DegradationReason> degradations
    ) {
        int frames;
        switch (environment.light()) {
            case BRIGHT:
                frames = 8;
                break;
            case NORMAL:
                frames = 10;
                break;
            case LOW:
                frames = 12;
                break;
            default:
                throw new IllegalStateException("Unhandled light state");
        }

        CaptureProfile effectiveProfile = CaptureProfile.MAX_DETAIL;
        if (environment.motion() == CaptureEnvironment.Motion.HIGH) {
            frames = Math.min(frames, 2);
            effectiveProfile = CaptureProfile.AUTO;
        } else if (environment.motion() == CaptureEnvironment.Motion.MODERATE) {
            frames = Math.min(frames, 6);
        }
        if (environment.thermal() == CaptureEnvironment.Thermal.WARM) {
            frames = Math.min(frames, 8);
        } else if (environment.thermal() == CaptureEnvironment.Thermal.HOT) {
            frames = Math.min(frames, 3);
            effectiveProfile = CaptureProfile.AUTO;
        }
        if (environment.memory() == CaptureEnvironment.Memory.CONSTRAINED) {
            frames = Math.min(frames, 4);
            effectiveProfile = CaptureProfile.AUTO;
        }
        frames = clamp(frames, MAX_DETAIL.minFrames, MAX_DETAIL.maxFrames);

        ExposureStrategy exposure = exposureFor(environment, true);
        EnumSet<CaptureStage> stages = commonStages();
        addMultiFrameStages(stages, frames);
        if (frames >= 3 && environment.motion() != CaptureEnvironment.Motion.HIGH) {
            stages.add(CaptureStage.HDR_MERGE);
        }
        if (effectiveProfile == CaptureProfile.MAX_DETAIL
                && frames >= 6
                && environment.motion() != CaptureEnvironment.Motion.HIGH
                && environment.thermal() != CaptureEnvironment.Thermal.HOT
                && environment.memory() == CaptureEnvironment.Memory.NORMAL) {
            stages.add(CaptureStage.SUPER_RESOLUTION);
        }

        CaptureModePolicy effectivePolicy = forProfile(effectiveProfile);
        return new CapturePlan(
                CaptureProfile.MAX_DETAIL,
                effectiveProfile,
                frames,
                exposure,
                stages,
                naturalRenderingConstraints(),
                degradations,
                effectivePolicy.shutterLatencyTargetMs,
                effectivePolicy.processingLatencyTargetMs,
                effectivePolicy.latencyConfidence(),
                maxDetailSummary(environment, effectiveProfile, frames, degradations)
        );
    }

    private static CapturePlan quickPlan(
            CaptureProfile requestedProfile,
            EnumSet<DegradationReason> degradations,
            String summary
    ) {
        return new CapturePlan(
                requestedProfile,
                CaptureProfile.QUICK,
                1,
                ExposureStrategy.SINGLE_AUTO,
                commonStages(),
                naturalRenderingConstraints(),
                degradations,
                QUICK.shutterLatencyTargetMs,
                QUICK.processingLatencyTargetMs,
                QUICK.latencyConfidence(),
                summary
        );
    }

    private static ExposureStrategy exposureFor(
            CaptureEnvironment environment,
            boolean detailMode
    ) {
        if (environment.motion() == CaptureEnvironment.Motion.HIGH) {
            return ExposureStrategy.SHORT_EXPOSURE_BURST;
        }
        if (environment.light() == CaptureEnvironment.Light.LOW) {
            return ExposureStrategy.LOW_LIGHT_BRACKET;
        }
        return detailMode
                ? ExposureStrategy.DETAIL_BURST
                : ExposureStrategy.BALANCED_BRACKET;
    }

    private static void addMultiFrameStages(EnumSet<CaptureStage> stages, int frames) {
        if (frames <= 1) {
            return;
        }
        stages.add(CaptureStage.FRAME_SCORING);
        stages.add(CaptureStage.MOTION_ESTIMATION);
        stages.add(CaptureStage.ALIGNMENT);
    }

    private static EnumSet<CaptureStage> commonStages() {
        return EnumSet.of(
                CaptureStage.DENOISE,
                CaptureStage.SHARPENING,
                CaptureStage.COLOR_RENDERING,
                CaptureStage.TONE_MAPPING,
                CaptureStage.JPEG_ENCODING
        );
    }

    private static EnumSet<RenderingConstraint> naturalRenderingConstraints() {
        return EnumSet.allOf(RenderingConstraint.class);
    }

    private static void addResourceDegradations(
            CaptureEnvironment environment,
            EnumSet<DegradationReason> degradations
    ) {
        switch (environment.thermal()) {
            case WARM:
                degradations.add(DegradationReason.THERMAL_WARM);
                break;
            case HOT:
                degradations.add(DegradationReason.THERMAL_HOT);
                break;
            case CRITICAL:
                degradations.add(DegradationReason.THERMAL_CRITICAL);
                break;
            case NOMINAL:
                break;
            default:
                throw new IllegalStateException("Unhandled thermal state");
        }
        switch (environment.memory()) {
            case CONSTRAINED:
                degradations.add(DegradationReason.MEMORY_CONSTRAINED);
                break;
            case CRITICAL:
                degradations.add(DegradationReason.MEMORY_CRITICAL);
                break;
            case NORMAL:
                break;
            default:
                throw new IllegalStateException("Unhandled memory state");
        }
    }

    private static void addMotionDegradations(
            CaptureEnvironment environment,
            EnumSet<DegradationReason> degradations
    ) {
        if (environment.motion() == CaptureEnvironment.Motion.HIGH) {
            degradations.add(DegradationReason.HIGH_MOTION);
        } else if (environment.motion() == CaptureEnvironment.Motion.MODERATE) {
            degradations.add(DegradationReason.MODERATE_MOTION);
        }
    }

    private static String quickSummary(
            CaptureEnvironment environment,
            EnumSet<DegradationReason> degradations
    ) {
        if (environment.light() == CaptureEnvironment.Light.LOW) {
            return "Quick: one-frame capture prioritizing shutter response over low-light detail.";
        }
        if (!degradations.isEmpty()) {
            return "Quick: one-frame capture with constrained-resource safeguards active.";
        }
        return "Quick: one-frame capture for the shortest predictable shutter path.";
    }

    private static String autoSummary(
            CaptureEnvironment environment,
            int frames,
            EnumSet<DegradationReason> degradations
    ) {
        if (environment.motion() == CaptureEnvironment.Motion.HIGH) {
            return "Auto: motion-limited " + frames
                    + "-frame burst prioritizing sharp subjects and deghosting.";
        }
        if (!degradations.isEmpty()) {
            return "Auto: " + frames
                    + " frames with thermal, memory or motion limits applied transparently.";
        }
        return "Auto: adaptive " + frames
                + "-frame capture balancing detail, dynamic range and latency.";
    }

    private static String maxDetailSummary(
            CaptureEnvironment environment,
            CaptureProfile effectiveProfile,
            int frames,
            EnumSet<DegradationReason> degradations
    ) {
        if (effectiveProfile != CaptureProfile.MAX_DETAIL) {
            return "Max Detail requested; using an Auto-compatible " + frames
                    + "-frame plan because motion or resources make super-resolution unreliable.";
        }
        if (!degradations.isEmpty()) {
            return "Max Detail: " + frames
                    + " aligned frames with explicit motion or thermal limits.";
        }
        if (environment.light() == CaptureEnvironment.Light.LOW) {
            return "Max Detail: " + frames
                    + " low-light frames with conservative merge and texture preservation.";
        }
        return "Max Detail: " + frames
                + " aligned frames with super-resolution and conservative natural rendering.";
    }

    private static int clamp(int value, int minimum, int maximum) {
        return Math.max(minimum, Math.min(maximum, value));
    }
}
