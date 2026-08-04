package com.phone2pro.camera.core;

/** Measured runtime dimension that exceeded the effective resource budget. */
public enum ResourceBudgetViolation {
    FRAME_COUNT,
    IN_FLIGHT_BUFFERS,
    WORKING_SET_MEMORY,
    QUEUE_DEPTH,
    SHUTTER_LATENCY,
    PROCESSING_LATENCY,
    SUSTAINED_CAPTURE_RATE
}
