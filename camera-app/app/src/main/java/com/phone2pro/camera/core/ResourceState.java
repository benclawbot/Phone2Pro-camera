package com.phone2pro.camera.core;

import java.util.Objects;

/** Immutable thermal, battery and memory state used to derive an effective budget. */
public final class ResourceState {
    private final CaptureEnvironment.Thermal thermal;
    private final BatteryState battery;
    private final long availableMemoryBytes;

    public ResourceState(
            CaptureEnvironment.Thermal thermal,
            BatteryState battery,
            long availableMemoryBytes
    ) {
        this.thermal = Objects.requireNonNull(thermal, "thermal");
        this.battery = Objects.requireNonNull(battery, "battery");
        if (availableMemoryBytes < 0) {
            throw new IllegalArgumentException("availableMemoryBytes must be non-negative");
        }
        this.availableMemoryBytes = availableMemoryBytes;
    }

    public CaptureEnvironment.Thermal thermal() { return thermal; }
    public BatteryState battery() { return battery; }
    public long availableMemoryBytes() { return availableMemoryBytes; }
}
