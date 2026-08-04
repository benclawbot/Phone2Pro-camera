package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Stable identity used by diagnostics and benchmarks for replaceable imaging implementations. */
public final class AlgorithmDescriptor {
    private final String id;
    private final String version;

    public AlgorithmDescriptor(String id, String version) {
        this.id = Objects.requireNonNull(id, "id");
        this.version = Objects.requireNonNull(version, "version");
        if (id.isEmpty() || version.isEmpty()) {
            throw new IllegalArgumentException("algorithm id and version must not be empty");
        }
    }

    public String id() { return id; }
    public String version() { return version; }
}
