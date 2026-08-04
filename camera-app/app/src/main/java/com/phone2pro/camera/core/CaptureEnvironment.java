package com.phone2pro.camera.core;

import java.util.Objects;

/** Immutable scene and resource conditions used to derive a deterministic capture plan. */
public final class CaptureEnvironment {
    public enum Motion {
        LOW,
        MODERATE,
        HIGH
    }

    public enum Light {
        BRIGHT,
        NORMAL,
        LOW
    }

    public enum Thermal {
        NOMINAL,
        WARM,
        HOT,
        CRITICAL
    }

    public enum Memory {
        NORMAL,
        CONSTRAINED,
        CRITICAL
    }

    private final Motion motion;
    private final Light light;
    private final Thermal thermal;
    private final Memory memory;

    public CaptureEnvironment(
            Motion motion,
            Light light,
            Thermal thermal,
            Memory memory
    ) {
        this.motion = Objects.requireNonNull(motion, "motion");
        this.light = Objects.requireNonNull(light, "light");
        this.thermal = Objects.requireNonNull(thermal, "thermal");
        this.memory = Objects.requireNonNull(memory, "memory");
    }

    public static CaptureEnvironment nominal() {
        return new CaptureEnvironment(
                Motion.LOW,
                Light.NORMAL,
                Thermal.NOMINAL,
                Memory.NORMAL
        );
    }

    public Motion motion() {
        return motion;
    }

    public Light light() {
        return light;
    }

    public Thermal thermal() {
        return thermal;
    }

    public Memory memory() {
        return memory;
    }
}
