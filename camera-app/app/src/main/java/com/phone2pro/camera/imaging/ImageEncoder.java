package com.phone2pro.camera.imaging;

/** Replaceable final encoder for JPEG and future output formats. */
public interface ImageEncoder {
    AlgorithmDescriptor descriptor();

    EncodedImage encodeJpeg(RenderImage image, JpegEncodingOptions options);
}
