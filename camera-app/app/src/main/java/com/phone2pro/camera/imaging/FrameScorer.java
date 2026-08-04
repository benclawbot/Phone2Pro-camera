package com.phone2pro.camera.imaging;

/** Replaceable quality scorer for one frame in a calibrated burst. */
public interface FrameScorer {
    AlgorithmDescriptor descriptor();

    FrameScore score(BurstFrame frame, BurstSequence sequence);
}
