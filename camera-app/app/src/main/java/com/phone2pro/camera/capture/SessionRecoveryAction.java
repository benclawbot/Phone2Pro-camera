package com.phone2pro.camera.capture;

/** Portable recovery action chosen after a capture/session failure. */
public enum SessionRecoveryAction {
    RETRY_REQUEST,
    RECREATE_SESSION,
    REOPEN_CAMERA,
    WAIT_FOR_RESOURCE,
    FAIL_PERMANENT,
    CANCELLED
}
