package com.phone2pro.camera.vendor;

/** Result of an isolated one-variable vendor capability probe. */
public enum VendorProbeStatus {
    VERIFIED_SUPPORTED,
    REJECTED,
    TIMEOUT,
    VALUE_MISMATCH,
    INEFFECTIVE,
    UNKNOWN
}
