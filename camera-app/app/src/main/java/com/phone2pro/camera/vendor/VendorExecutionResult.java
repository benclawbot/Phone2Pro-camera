package com.phone2pro.camera.vendor;

import java.util.Objects;

/** Runtime outcome with elapsed time and a non-sensitive explanation. */
public final class VendorExecutionResult {
    private final VendorExecutionStatus status;
    private final long elapsedMillis;
    private final String detail;

    public VendorExecutionResult(
            VendorExecutionStatus status,
            long elapsedMillis,
            String detail
    ) {
        this.status = Objects.requireNonNull(status, "status");
        if (elapsedMillis < 0) {
            throw new IllegalArgumentException("elapsedMillis must be non-negative");
        }
        this.elapsedMillis = elapsedMillis;
        this.detail = Objects.requireNonNull(detail, "detail");
        if (detail.isEmpty()) {
            throw new IllegalArgumentException("detail must not be empty");
        }
    }

    public VendorExecutionStatus status() { return status; }
    public long elapsedMillis() { return elapsedMillis; }
    public String detail() { return detail; }
}
