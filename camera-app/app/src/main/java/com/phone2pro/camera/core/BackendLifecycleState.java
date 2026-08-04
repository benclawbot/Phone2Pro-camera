package com.phone2pro.camera.core;

/** Portable backend lifecycle independent of CameraX and Camera2 object types. */
public enum BackendLifecycleState {
    IDLE,
    DISCOVERING,
    READY,
    OPENING,
    OPEN,
    CONFIGURING,
    STREAMING,
    CAPTURING,
    RECOVERING,
    CLOSING,
    CLOSED,
    ERROR
}
