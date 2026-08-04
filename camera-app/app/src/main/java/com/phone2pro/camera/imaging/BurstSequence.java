package com.phone2pro.camera.imaging;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/** Immutable burst and motion timeline with an explicit clock-domain relationship. */
public final class BurstSequence {
    private final List<BurstFrame> frames;
    private final List<MotionSample> motionSamples;
    private final ClockCalibration motionToFrameCalibration;
    private final TimestampDomain frameDomain;

    public BurstSequence(
            List<BurstFrame> frames,
            List<MotionSample> motionSamples,
            ClockCalibration motionToFrameCalibration
    ) {
        Objects.requireNonNull(frames, "frames");
        Objects.requireNonNull(motionSamples, "motionSamples");
        if (frames.isEmpty()) {
            throw new IllegalArgumentException("a burst must contain at least one frame");
        }
        this.frames = Collections.unmodifiableList(new ArrayList<>(frames));
        this.motionSamples = Collections.unmodifiableList(new ArrayList<>(motionSamples));
        this.frameDomain = frames.get(0).metadata().timestampDomain();
        for (BurstFrame frame : frames) {
            if (frame.metadata().timestampDomain() != frameDomain) {
                throw new IllegalArgumentException("all burst frames must use one timestamp domain");
            }
        }

        TimestampDomain motionDomain = motionSamples.isEmpty()
                ? frameDomain
                : motionSamples.get(0).timestampDomain();
        for (MotionSample sample : motionSamples) {
            if (sample.timestampDomain() != motionDomain) {
                throw new IllegalArgumentException("all motion samples must use one timestamp domain");
            }
        }

        if (!motionSamples.isEmpty() && motionDomain != frameDomain) {
            if (motionToFrameCalibration == null
                    || motionToFrameCalibration.sourceDomain() != motionDomain
                    || motionToFrameCalibration.targetDomain() != frameDomain) {
                throw new IllegalArgumentException(
                        "different motion and frame clocks require a matching calibration"
                );
            }
        } else if (motionToFrameCalibration != null
                && (motionToFrameCalibration.sourceDomain() != motionDomain
                || motionToFrameCalibration.targetDomain() != frameDomain)) {
            throw new IllegalArgumentException("calibration domains do not match the burst timeline");
        }
        this.motionToFrameCalibration = motionToFrameCalibration;
    }

    public List<BurstFrame> frames() { return frames; }
    public List<MotionSample> motionSamples() { return motionSamples; }
    public TimestampDomain frameDomain() { return frameDomain; }

    public Optional<ClockCalibration> motionToFrameCalibration() {
        return Optional.ofNullable(motionToFrameCalibration);
    }

    public long motionTimestampInFrameDomain(MotionSample sample) {
        Objects.requireNonNull(sample, "sample");
        if (sample.timestampDomain() == frameDomain) {
            return sample.timestampNs();
        }
        if (motionToFrameCalibration == null
                || sample.timestampDomain() != motionToFrameCalibration.sourceDomain()) {
            throw new IllegalArgumentException("motion sample does not belong to this timeline");
        }
        return motionToFrameCalibration.map(sample.timestampNs());
    }
}
