package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Color-space, transfer-function and precision contract for one pipeline image. */
public final class ImageEncoding {
    private final ColorSpace colorSpace;
    private final TransferFunction transferFunction;
    private final int bitDepth;
    private final boolean floatingPoint;

    public ImageEncoding(
            ColorSpace colorSpace,
            TransferFunction transferFunction,
            int bitDepth,
            boolean floatingPoint
    ) {
        this.colorSpace = Objects.requireNonNull(colorSpace, "colorSpace");
        this.transferFunction = Objects.requireNonNull(
                transferFunction,
                "transferFunction"
        );
        if (bitDepth < 8 || bitDepth > 32) {
            throw new IllegalArgumentException("bitDepth must be between 8 and 32");
        }
        if (colorSpace.isLinear() && transferFunction != TransferFunction.LINEAR) {
            throw new IllegalArgumentException("linear color spaces require a linear transfer function");
        }
        if (!colorSpace.isLinear() && transferFunction == TransferFunction.LINEAR) {
            throw new IllegalArgumentException("nonlinear output color spaces require a nonlinear transfer function");
        }
        if (floatingPoint && bitDepth < 16) {
            throw new IllegalArgumentException("floating-point encodings require at least 16 bits");
        }
        this.bitDepth = bitDepth;
        this.floatingPoint = floatingPoint;
    }

    public static ImageEncoding sensorLinear16() {
        return new ImageEncoding(ColorSpace.SENSOR_NATIVE, TransferFunction.LINEAR, 16, false);
    }

    public static ImageEncoding linearSrgb16() {
        return new ImageEncoding(ColorSpace.LINEAR_SRGB, TransferFunction.LINEAR, 16, false);
    }

    public static ImageEncoding srgb8() {
        return new ImageEncoding(ColorSpace.SRGB, TransferFunction.SRGB, 8, false);
    }

    public ColorSpace colorSpace() { return colorSpace; }
    public TransferFunction transferFunction() { return transferFunction; }
    public int bitDepth() { return bitDepth; }
    public boolean floatingPoint() { return floatingPoint; }

    public boolean isLinearHighPrecision() {
        return colorSpace.isLinear() && bitDepth >= 12;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof ImageEncoding)) {
            return false;
        }
        ImageEncoding encoding = (ImageEncoding) other;
        return colorSpace == encoding.colorSpace
                && transferFunction == encoding.transferFunction
                && bitDepth == encoding.bitDepth
                && floatingPoint == encoding.floatingPoint;
    }

    @Override
    public int hashCode() {
        return Objects.hash(colorSpace, transferFunction, bitDepth, floatingPoint);
    }

    @Override
    public String toString() {
        return colorSpace + "/" + transferFunction + "/" + bitDepth
                + (floatingPoint ? "f" : "u");
    }
}
