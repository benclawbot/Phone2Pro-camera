package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Output image and artefact assessment from one rendering stage. */
public final class RenderStageResult {
    private final RenderImage image;
    private final ArtifactReport artifactReport;

    public RenderStageResult(RenderImage image, ArtifactReport artifactReport) {
        this.image = Objects.requireNonNull(image, "image");
        this.artifactReport = Objects.requireNonNull(artifactReport, "artifactReport");
    }

    public RenderImage image() { return image; }
    public ArtifactReport artifactReport() { return artifactReport; }
}
