package com.phone2pro.camera.imaging;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;

import com.phone2pro.camera.core.EvidenceConfidence;

import org.junit.Test;

import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.LongSupplier;

public final class BurstAlignmentContractsTest {
    @Test
    public void differentClockDomainsRequireCalibration() {
        BurstFrame frame = frame("frame-1", 10_000L, TimestampDomain.CAMERA_SENSOR);
        MotionSample gyro = new MotionSample(
                MotionSample.Source.GYROSCOPE_RAD_PER_SECOND,
                5_000L,
                TimestampDomain.ELAPSED_REALTIME,
                0.1,
                0.2,
                0.3
        );

        expectIllegalArgument(() -> new BurstSequence(
                Collections.singletonList(frame),
                Collections.singletonList(gyro),
                null
        ));
    }

    @Test
    public void calibratedMotionMapsIntoFrameClock() {
        BurstFrame frame = frame("frame-1", 10_500L, TimestampDomain.CAMERA_SENSOR);
        MotionSample gyro = new MotionSample(
                MotionSample.Source.GYROSCOPE_RAD_PER_SECOND,
                5_250L,
                TimestampDomain.ELAPSED_REALTIME,
                0.1,
                0.2,
                0.3
        );
        ClockCalibration calibration = new ClockCalibration(
                TimestampDomain.ELAPSED_REALTIME,
                TimestampDomain.CAMERA_SENSOR,
                5_000L,
                10_000L,
                2.0,
                100L,
                EvidenceConfidence.PARTIALLY_VERIFIED,
                "paired monotonic samples"
        );

        BurstSequence sequence = new BurstSequence(
                Collections.singletonList(frame),
                Collections.singletonList(gyro),
                calibration
        );

        assertEquals(10_500L, sequence.motionTimestampInFrameDomain(gyro));
        assertEquals(100L, sequence.motionToFrameCalibration().get().uncertaintyNs());
    }

    @Test
    public void localMotionAndConfidenceMasksRemainAccessible() {
        ConfidenceMask confidence = new ConfidenceMask(
                2,
                2,
                new float[]{1.0f, 0.8f, 0.4f, 0.0f}
        );
        MotionField field = new MotionField(
                2,
                2,
                new float[]{0.0f, 1.0f, 2.0f, 3.0f},
                new float[]{0.0f, -1.0f, -2.0f, -3.0f},
                confidence
        );
        AlignmentResult result = new AlignmentResult(
                "reference",
                "candidate",
                4,
                new double[]{1, 0, 0, 0, 1, 0, 0, 0, 1},
                field,
                confidence,
                ConfidenceMask.filled(2, 2, 1.0f),
                0.25
        );

        assertEquals(2.0f, result.localMotion().deltaXAt(0, 1), 0.0f);
        assertEquals(-2.0f, result.localMotion().deltaYAt(0, 1), 0.0f);
        assertEquals(0.4f, result.alignmentConfidence().valueAt(0, 1), 0.0f);
        assertEquals(1.0f, result.validityMask().valueAt(1, 1), 0.0f);
    }

    @Test
    public void scoringSelectionAndAlignmentAreReplaceable() {
        BurstFrame first = frame("first", 1_000L, TimestampDomain.CAMERA_SENSOR);
        BurstFrame second = frame("second", 2_000L, TimestampDomain.CAMERA_SENSOR);
        BurstSequence sequence = new BurstSequence(
                Arrays.asList(first, second),
                Collections.emptyList(),
                null
        );

        FrameScorer scorer = new FrameScorer() {
            private final AlgorithmDescriptor descriptor = new AlgorithmDescriptor("fake-score", "1");

            @Override
            public AlgorithmDescriptor descriptor() { return descriptor; }

            @Override
            public FrameScore score(BurstFrame frame, BurstSequence ignored) {
                double value = "second".equals(frame.id()) ? 0.9 : 0.5;
                return new FrameScore(value, value, value, value, value, value, "test");
            }
        };
        Map<String, FrameScore> scores = new LinkedHashMap<>();
        for (BurstFrame frame : sequence.frames()) {
            scores.put(frame.id(), scorer.score(frame, sequence));
        }

        ReferenceSelector selector = new ReferenceSelector() {
            private final AlgorithmDescriptor descriptor = new AlgorithmDescriptor("fake-select", "1");

            @Override
            public AlgorithmDescriptor descriptor() { return descriptor; }

            @Override
            public BurstFrame select(BurstSequence input, Map<String, FrameScore> inputScores) {
                return input.frames().stream()
                        .max((left, right) -> Double.compare(
                                inputScores.get(left.id()).total(),
                                inputScores.get(right.id()).total()
                        ))
                        .orElseThrow(AssertionError::new);
            }
        };
        BurstFrame reference = selector.select(sequence, scores);
        assertSame(second, reference);

        FrameAligner aligner = new FrameAligner() {
            private final AlgorithmDescriptor descriptor = new AlgorithmDescriptor("fake-align", "1");

            @Override
            public AlgorithmDescriptor descriptor() { return descriptor; }

            @Override
            public AlignmentResult align(
                    BurstFrame selected,
                    BurstFrame candidate,
                    BurstSequence ignored,
                    AlignmentRequest request
            ) {
                ConfidenceMask mask = ConfidenceMask.filled(1, 1, 1.0f);
                MotionField field = new MotionField(
                        1,
                        1,
                        new float[]{0.0f},
                        new float[]{0.0f},
                        mask
                );
                return new AlignmentResult(
                        selected.id(),
                        candidate.id(),
                        request.pyramidLevels(),
                        new double[]{1, 0, 0, 0, 1, 0, 0, 0, 1},
                        field,
                        mask,
                        mask,
                        0.0
                );
            }
        };
        AlignmentResult alignment = aligner.align(
                reference,
                first,
                sequence,
                new AlignmentRequest(3, 32.0f, true, 0.5f)
        );
        assertEquals("second", alignment.referenceFrameId());
        assertEquals(3, alignment.pyramidLevelsUsed());
    }

    @Test
    public void benchmarkUsesStableAlgorithmIdentity() {
        AtomicInteger work = new AtomicInteger();
        long[] times = {100L, 250L};
        AtomicInteger clockIndex = new AtomicInteger();
        LongSupplier clock = () -> times[clockIndex.getAndIncrement()];
        AlgorithmDescriptor descriptor = new AlgorithmDescriptor("fake-align", "2");

        AlgorithmBenchmark.Result result = AlgorithmBenchmark.measure(
                descriptor,
                3,
                work::incrementAndGet,
                clock
        );

        assertEquals(1, work.get());
        assertSame(descriptor, result.descriptor());
        assertEquals(150L, result.durationNs());
        assertEquals(50.0, result.nanosecondsPerWorkUnit(), 0.0);
    }

    private static BurstFrame frame(String id, long timestamp, TimestampDomain domain) {
        return new BurstFrame(
                id,
                new TestFrameBuffer(),
                new FrameMetadata(
                        1L,
                        timestamp,
                        domain,
                        1_000_000L,
                        100,
                        33_333_333L,
                        1_000_000L,
                        5.56f
                )
        );
    }

    private static void expectIllegalArgument(Runnable work) {
        try {
            work.run();
            throw new AssertionError("Expected IllegalArgumentException");
        } catch (IllegalArgumentException expected) {
            // Expected.
        }
    }

    private static final class TestFrameBuffer implements FrameBuffer {
        private final ByteBuffer data = ByteBuffer.allocate(16).asReadOnlyBuffer();

        @Override public int width() { return 2; }
        @Override public int height() { return 2; }
        @Override public int bitDepth() { return 16; }
        @Override public Format format() { return Format.LINEAR_RGB; }
        @Override public long sizeBytes() { return data.capacity(); }
        @Override public ByteBuffer readOnlyData() { return data.asReadOnlyBuffer(); }
        @Override public void close() { }
    }
}
