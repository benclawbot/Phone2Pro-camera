package com.phone2pro.camera.imaging;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Immutable, encoding-safe stage plan for one still-image rendering path. */
public final class RenderPipelinePlan {
    private final List<RenderStageSpec> stages;

    public RenderPipelinePlan(List<RenderStageSpec> stages) {
        Objects.requireNonNull(stages, "stages");
        if (stages.isEmpty()) {
            throw new IllegalArgumentException("rendering plan must contain at least one stage");
        }
        List<RenderStageSpec> copy = new ArrayList<>(stages);
        validate(copy);
        this.stages = Collections.unmodifiableList(copy);
    }

    public static RenderPipelinePlan naturalJpeg() {
        ImageEncoding sensor = ImageEncoding.sensorLinear16();
        ImageEncoding linearSrgb = ImageEncoding.linearSrgb16();
        ImageEncoding srgb = ImageEncoding.srgb8();
        List<RenderStageSpec> stages = new ArrayList<>();
        stages.add(new RenderStageSpec(RenderStage.INPUT_NORMALIZATION, sensor, sensor, true));
        stages.add(new RenderStageSpec(RenderStage.DEMOSAIC, sensor, sensor, true));
        stages.add(new RenderStageSpec(RenderStage.ALIGNMENT, sensor, sensor, true));
        stages.add(new RenderStageSpec(RenderStage.ROBUST_MERGE, sensor, sensor, true));
        stages.add(new RenderStageSpec(RenderStage.SUPER_RESOLUTION, sensor, sensor, true));
        stages.add(new RenderStageSpec(RenderStage.DENOISE, sensor, sensor, true));
        stages.add(new RenderStageSpec(RenderStage.COLOR_TRANSFORM, sensor, linearSrgb, true));
        stages.add(new RenderStageSpec(RenderStage.TONE_MAPPING, linearSrgb, srgb, true));
        stages.add(new RenderStageSpec(RenderStage.SHARPENING, srgb, srgb, true));
        stages.add(new RenderStageSpec(RenderStage.ENCODING, srgb, srgb, true));
        return new RenderPipelinePlan(stages);
    }

    public List<RenderStageSpec> stages() {
        return stages;
    }

    public RenderStageSpec first() {
        return stages.get(0);
    }

    public RenderStageSpec last() {
        return stages.get(stages.size() - 1);
    }

    public boolean includes(RenderStage stage) {
        for (RenderStageSpec spec : stages) {
            if (spec.stage() == stage) {
                return true;
            }
        }
        return false;
    }

    private static void validate(List<RenderStageSpec> stages) {
        RenderStageSpec previous = null;
        for (RenderStageSpec current : stages) {
            Objects.requireNonNull(current, "stage spec");
            if (previous != null) {
                if (current.stage().order() <= previous.stage().order()) {
                    throw new IllegalArgumentException("render stages must be strictly ordered");
                }
                if (!previous.outputEncoding().equals(current.inputEncoding())) {
                    throw new IllegalArgumentException(
                            "encoding mismatch between " + previous.stage() + " and " + current.stage()
                    );
                }
            }
            validateTransition(current);
            previous = current;
        }
        if (stages.get(stages.size() - 1).stage() != RenderStage.ENCODING) {
            throw new IllegalArgumentException("the final rendering stage must be ENCODING");
        }
        if (contains(stages, RenderStage.ROBUST_MERGE)
                && !containsBefore(stages, RenderStage.ALIGNMENT, RenderStage.ROBUST_MERGE)) {
            throw new IllegalArgumentException("robust merge requires an earlier alignment stage");
        }
    }

    private static void validateTransition(RenderStageSpec spec) {
        switch (spec.stage()) {
            case COLOR_TRANSFORM:
                if (!spec.outputEncoding().colorSpace().isLinear()) {
                    throw new IllegalArgumentException("color transform must remain scene-linear");
                }
                break;
            case TONE_MAPPING:
                if (!spec.inputEncoding().colorSpace().isLinear()
                        || spec.outputEncoding().colorSpace().isLinear()) {
                    throw new IllegalArgumentException(
                            "tone mapping must transition from linear scene data to nonlinear output"
                    );
                }
                break;
            case SHARPENING:
            case ENCODING:
                if (!spec.inputEncoding().equals(spec.outputEncoding())) {
                    throw new IllegalArgumentException(
                            spec.stage() + " must preserve the declared pixel encoding"
                    );
                }
                break;
            default:
                break;
        }
    }

    private static boolean contains(List<RenderStageSpec> stages, RenderStage stage) {
        for (RenderStageSpec spec : stages) {
            if (spec.stage() == stage) {
                return true;
            }
        }
        return false;
    }

    private static boolean containsBefore(
            List<RenderStageSpec> stages,
            RenderStage required,
            RenderStage dependent
    ) {
        int requiredIndex = -1;
        int dependentIndex = -1;
        for (int index = 0; index < stages.size(); index++) {
            RenderStage stage = stages.get(index).stage();
            if (stage == required) {
                requiredIndex = index;
            }
            if (stage == dependent) {
                dependentIndex = index;
            }
        }
        return requiredIndex >= 0 && dependentIndex > requiredIndex;
    }
}
