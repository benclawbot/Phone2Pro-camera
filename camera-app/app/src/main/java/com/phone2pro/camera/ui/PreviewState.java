package com.phone2pro.camera.ui;

/** Preview lifecycle kept independent from backend implementation details. */
public enum PreviewState {
    STOPPED,
    STARTING,
    STREAMING,
    PAUSED,
    ERROR
}
