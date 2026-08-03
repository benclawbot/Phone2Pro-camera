package com.phone2pro.camera.core;

import java.util.Objects;

/** Backend-owned resolution of an optical route to a concrete Camera2 endpoint. */
public final class ResolvedCameraEndpoint {
    private final String cameraId;
    private final RouteMechanism mechanism;
    private final String evidence;

    public ResolvedCameraEndpoint(
            String cameraId,
            RouteMechanism mechanism,
            String evidence
    ) {
        this.cameraId = requireNonBlank(cameraId, "cameraId");
        this.mechanism = Objects.requireNonNull(mechanism, "mechanism");
        if (mechanism == RouteMechanism.UNAVAILABLE) {
            throw new IllegalArgumentException("Resolved endpoint cannot use UNAVAILABLE mechanism");
        }
        this.evidence = requireNonBlank(evidence, "evidence");
    }

    public String cameraId() {
        return cameraId;
    }

    public RouteMechanism mechanism() {
        return mechanism;
    }

    public String evidence() {
        return evidence;
    }

    private static String requireNonBlank(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }
}
