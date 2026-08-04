package com.phone2pro.camera.imaging;

/** Replaceable detector run after merge, super-resolution, tone mapping or sharpening. */
public interface ArtifactDetector {
    AlgorithmDescriptor descriptor();

    ArtifactReport inspect(RenderStage completedStage, RenderImage image);
}
