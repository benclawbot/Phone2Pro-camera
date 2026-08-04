package com.phone2pro.camera.imaging;

import java.util.Objects;

/** One image and its normalized metadata within a capture burst. */
public final class BurstFrame implements AutoCloseable {
    private final String id;
    private final FrameBuffer buffer;
    private final FrameMetadata metadata;

    public BurstFrame(String id, FrameBuffer buffer, FrameMetadata metadata) {
        this.id = Objects.requireNonNull(id, "id");
        if (id.isEmpty()) {
            throw new IllegalArgumentException("id must not be empty");
        }
        this.buffer = Objects.requireNonNull(buffer, "buffer");
        this.metadata = Objects.requireNonNull(metadata, "metadata");
    }

    public String id() { return id; }
    public FrameBuffer buffer() { return buffer; }
    public FrameMetadata metadata() { return metadata; }

    @Override
    public void close() {
        buffer.close();
    }
}
