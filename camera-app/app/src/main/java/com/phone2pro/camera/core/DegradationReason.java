package com.phone2pro.camera.core;

/** Explicit reason why a capture plan performs less work than its nominal mode. */
public enum DegradationReason {
    HIGH_MOTION,
    MODERATE_MOTION,
    THERMAL_WARM,
    THERMAL_HOT,
    THERMAL_CRITICAL,
    MEMORY_CONSTRAINED,
    MEMORY_CRITICAL
}
