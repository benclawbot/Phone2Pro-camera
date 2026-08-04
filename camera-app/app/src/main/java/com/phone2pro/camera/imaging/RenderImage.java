package com.phone2pro.camera.imaging;

import java.util.Objects;

/** One owned image plus its explicit encoding and immutable metadata. */
public final class RenderImage implements AutoCloseable {
    private final FrameBuffer buffer;
    private final ImageEncoding encoding;
    private final RenderMetadata metadata;

    public RenderImage(
            FrameBuffer buffer,
            ImageEncoding encoding,
            RenderMetadata metadata
    ) {
        this.buffer = Objects.requireNonNull(buffer, "buffer");
        this.encoding = Objects.requireNonNull(encoding, "encoding");
        this.metadata = Objects.requireNonNull(metadata, "metadata");
        if (buffer.bitDepth() != encoding.bitDepth()) {
            throw new IllegalArgumentException(
                    "buffer bit depth must match the declared image encoding"
            );
        }
    }

    public FrameBuffer buffer() { return buffer; }
    public ImageEncoding encoding() { return encoding; }
    public RenderMetadata metadata() { return metadata; }

    @Override
    public void close() {
        buffer.close();
    }
}
