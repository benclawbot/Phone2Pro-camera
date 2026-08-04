package com.phone2pro.camera.imaging;

/** Canonical stage order for the independent on-device still-image pipeline. */
public enum RenderStage {
    INPUT_NORMALIZATION(10),
    DEMOSAIC(20),
    ALIGNMENT(30),
    ROBUST_MERGE(40),
    SUPER_RESOLUTION(50),
    DENOISE(60),
    COLOR_TRANSFORM(70),
    TONE_MAPPING(80),
    SHARPENING(90),
    ENCODING(100);

    private final int order;

    RenderStage(int order) {
        this.order = order;
    }

    public int order() {
        return order;
    }

    public boolean requiresLinearHighPrecisionInput() {
        switch (this) {
            case ALIGNMENT:
            case ROBUST_MERGE:
            case SUPER_RESOLUTION:
            case DENOISE:
            case COLOR_TRANSFORM:
                return true;
            default:
                return false;
        }
    }
}
