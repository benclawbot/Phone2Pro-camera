package com.phone2pro.camera.core;

/** Why a requested capture budget was reduced or blocked. */
public enum BudgetDegradationReason {
    THERMAL_WARM,
    THERMAL_HOT,
    THERMAL_CRITICAL,
    BATTERY_LOW,
    BATTERY_CRITICAL,
    MEMORY_HEADROOM,
    CAPTURE_BLOCKED
}
