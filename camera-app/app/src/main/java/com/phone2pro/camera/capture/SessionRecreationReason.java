package com.phone2pro.camera.capture;

/** Why an active camera session must be closed and rebuilt. */
public enum SessionRecreationReason {
    NONE,
    BACKEND_CHANGED,
    BINDER_CHANGED,
    ENDPOINT_CHANGED,
    ROUTE_CHANGED,
    STREAMS_CHANGED,
    SESSION_PARAMETERS_CHANGED,
    TIMESTAMP_DOMAIN_CHANGED,
    TRANSIENT_RECOVERY
}
