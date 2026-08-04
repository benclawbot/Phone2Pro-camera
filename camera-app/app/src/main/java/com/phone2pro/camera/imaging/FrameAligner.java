package com.phone2pro.camera.imaging;

/** Replaceable multi-scale alignment implementation. */
public interface FrameAligner {
    AlgorithmDescriptor descriptor();

    AlignmentResult align(
            BurstFrame reference,
            BurstFrame candidate,
            BurstSequence sequence,
            AlignmentRequest request
    );
}
