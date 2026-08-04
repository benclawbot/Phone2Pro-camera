package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Declares one processor's stage, encoding transition and metadata behavior. */
public final class RenderStageSpec {
    private final RenderStage stage;
    private final ImageEncoding inputEncoding;
    private final ImageEncoding outputEncoding;
    private final boolean preservesAllMetadata;

    public RenderStageSpec(
            RenderStage stage,
            ImageEncoding inputEncoding,
            ImageEncoding outputEncoding,
            boolean preservesAllMetadata
    ) {
        this.stage = Objects.requireNonNull(stage, "stage");
        this.inputEncoding = Objects.requireNonNull(inputEncoding, "inputEncoding");
        this.outputEncoding = Objects.requireNonNull(outputEncoding, "outputEncoding");
        if (stage.requiresLinearHighPrecisionInput() && !inputEncoding.isLinearHighPrecision()) {
            throw new IllegalArgumentException(
                    stage + " requires linear input with at least 12-bit precision"
            );
        }
        if (!preservesAllMetadata) {
            throw new IllegalArgumentException(
                    "rendering stages must preserve existing metadata; additions are allowed"
            );
        }
        this.preservesAllMetadata = true;
    }

    public RenderStage stage() { return stage; }
    public ImageEncoding inputEncoding() { return inputEncoding; }
    public ImageEncoding outputEncoding() { return outputEncoding; }
    public boolean preservesAllMetadata() { return preservesAllMetadata; }
}
