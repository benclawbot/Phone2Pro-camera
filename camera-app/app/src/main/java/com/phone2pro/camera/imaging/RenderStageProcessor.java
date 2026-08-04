package com.phone2pro.camera.imaging;

/** Replaceable implementation of one typed rendering stage. */
public interface RenderStageProcessor {
    AlgorithmDescriptor descriptor();

    RenderStageSpec spec();

    RenderStageResult process(RenderImage input);
}
