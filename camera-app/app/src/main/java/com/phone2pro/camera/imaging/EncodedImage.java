package com.phone2pro.camera.imaging;

import java.util.Arrays;
import java.util.Objects;

/** Immutable encoded image bytes with the metadata used to create the asset. */
public final class EncodedImage {
    private final String mediaType;
    private final byte[] bytes;
    private final RenderMetadata metadata;

    public EncodedImage(String mediaType, byte[] bytes, RenderMetadata metadata) {
        this.mediaType = Objects.requireNonNull(mediaType, "mediaType");
        Objects.requireNonNull(bytes, "bytes");
        if (mediaType.isEmpty() || bytes.length == 0) {
            throw new IllegalArgumentException("encoded image type and bytes must not be empty");
        }
        this.bytes = Arrays.copyOf(bytes, bytes.length);
        this.metadata = Objects.requireNonNull(metadata, "metadata");
    }

    public String mediaType() { return mediaType; }
    public byte[] copyBytes() { return Arrays.copyOf(bytes, bytes.length); }
    public int sizeBytes() { return bytes.length; }
    public RenderMetadata metadata() { return metadata; }
}
