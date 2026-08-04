package com.phone2pro.camera.core;

/** Identifies how a backend reaches a route; rendering is reported separately. */
public enum RouteMechanism {
    PUBLIC_CAMERA,
    PUBLIC_VENDOR_SAT,
    SYSTEM_CAMERA,
    STOCK_CAMERA_HANDOFF,
    UNAVAILABLE
}
