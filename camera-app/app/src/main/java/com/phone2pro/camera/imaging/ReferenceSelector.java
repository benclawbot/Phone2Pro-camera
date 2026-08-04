package com.phone2pro.camera.imaging;

import java.util.Map;

/** Chooses the alignment reference independently from the scoring implementation. */
public interface ReferenceSelector {
    AlgorithmDescriptor descriptor();

    BurstFrame select(BurstSequence sequence, Map<String, FrameScore> scoresByFrameId);
}
