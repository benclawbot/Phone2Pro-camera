package com.phone2pro.camera.vendor;

/** Result of applying and validating a planned vendor configuration. */
public enum VendorExecutionStatus {
    APPLIED_AND_VERIFIED,
    REJECTED,
    TIMEOUT,
    VALUE_MISMATCH,
    INEFFECTIVE,
    ERROR
}
