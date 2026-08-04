package com.phone2pro.camera.imaging;

import java.nio.ByteBuffer;

/** Framework-independent, read-only image buffer supplied to imaging algorithms. */
public interface FrameBuffer extends AutoCloseable {
    enum Format {
        YUV_420,
        RAW_SENSOR,
        LINEAR_RGB,
        DISPLAY_RGB
    }

    int width();
    int height();
    int bitDepth();
    Format format();
    long sizeBytes();

    /** Returns a read-only view. Implementations retain ownership of the backing memory. */
    ByteBuffer readOnlyData();

    @Override
    void close();
}
