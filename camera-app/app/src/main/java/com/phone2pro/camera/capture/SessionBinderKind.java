package com.phone2pro.camera.capture;

/** Android binding strategy kept outside the portable session plan. */
public enum SessionBinderKind {
    /** CameraX preview/still binder for verified public configurations. */
    CAMERAX_PUBLIC,
    /** Direct Camera2 CameraDevice/CameraCaptureSession binder. */
    CAMERA2_DIRECT,
    /** Direct Camera2 binder with an isolated verified vendor adapter. */
    CAMERA2_VENDOR_ADAPTER
}
