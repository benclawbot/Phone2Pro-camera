package com.phone2pro.camera.capture;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/** Immutable ordered still-burst plan bound to one session generation. */
public final class StillBurstPlan {
    private final String captureId;
    private final long sessionGeneration;
    private final List<CaptureFrameRequest> frames;

    public StillBurstPlan(
            String captureId,
            long sessionGeneration,
            List<CaptureFrameRequest> frames
    ) {
        this.captureId = requireText(captureId, "captureId");
        if (sessionGeneration < 0) {
            throw new IllegalArgumentException("sessionGeneration must be non-negative");
        }
        Objects.requireNonNull(frames, "frames");
        if (frames.isEmpty()) {
            throw new IllegalArgumentException("frames must not be empty");
        }
        if (frames.size() > 64) {
            throw new IllegalArgumentException("burst must not exceed 64 frames");
        }
        List<CaptureFrameRequest> copy = new ArrayList<>(frames.size());
        Set<String> requestIds = new HashSet<>();
        for (int index = 0; index < frames.size(); index++) {
            CaptureFrameRequest frame = Objects.requireNonNull(frames.get(index), "frame");
            if (frame.sequenceIndex() != index) {
                throw new IllegalArgumentException("frame sequence must be contiguous and ordered");
            }
            if (!requestIds.add(frame.requestId())) {
                throw new IllegalArgumentException("request IDs must be unique within a burst");
            }
            copy.add(frame);
        }
        this.sessionGeneration = sessionGeneration;
        this.frames = Collections.unmodifiableList(copy);
    }

    public String captureId() { return captureId; }
    public long sessionGeneration() { return sessionGeneration; }
    public List<CaptureFrameRequest> frames() { return frames; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }
}
