package com.phone2pro.camera.imaging;

import java.util.Objects;
import java.util.function.LongSupplier;

/** Minimal benchmark wrapper shared by scoring, selection and alignment implementations. */
public final class AlgorithmBenchmark {
    private AlgorithmBenchmark() {
    }

    public static Result measure(
            AlgorithmDescriptor descriptor,
            int workUnits,
            Runnable work
    ) {
        return measure(descriptor, workUnits, work, System::nanoTime);
    }

    static Result measure(
            AlgorithmDescriptor descriptor,
            int workUnits,
            Runnable work,
            LongSupplier nanoClock
    ) {
        Objects.requireNonNull(descriptor, "descriptor");
        Objects.requireNonNull(work, "work");
        Objects.requireNonNull(nanoClock, "nanoClock");
        if (workUnits <= 0) {
            throw new IllegalArgumentException("workUnits must be positive");
        }
        long start = nanoClock.getAsLong();
        work.run();
        long end = nanoClock.getAsLong();
        if (end < start) {
            throw new IllegalStateException("benchmark clock moved backwards");
        }
        return new Result(descriptor, workUnits, end - start);
    }

    public static final class Result {
        private final AlgorithmDescriptor descriptor;
        private final int workUnits;
        private final long durationNs;

        Result(AlgorithmDescriptor descriptor, int workUnits, long durationNs) {
            this.descriptor = descriptor;
            this.workUnits = workUnits;
            this.durationNs = durationNs;
        }

        public AlgorithmDescriptor descriptor() { return descriptor; }
        public int workUnits() { return workUnits; }
        public long durationNs() { return durationNs; }
        public double nanosecondsPerWorkUnit() { return durationNs / (double) workUnits; }
    }
}
