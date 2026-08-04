package com.phone2pro.camera.imaging;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumSet;

public final class ImageRenderingPipelineTest {
    @Test
    public void linearAndNonlinearEncodingsAreExplicit() {
        ImageEncoding linear = ImageEncoding.linearSrgb16();
        ImageEncoding display = ImageEncoding.srgb8();

        assertTrue(linear.colorSpace().isLinear());
        assertTrue(linear.isLinearHighPrecision());
        assertFalse(display.colorSpace().isLinear());
        assertEquals(8, display.bitDepth());

        expectIllegalArgument(() -> new ImageEncoding(
                ColorSpace.LINEAR_SRGB,
                TransferFunction.SRGB,
                16,
                false
        ));
        expectIllegalArgument(() -> new ImageEncoding(
                ColorSpace.SRGB,
                TransferFunction.LINEAR,
                8,
                false
        ));
    }

    @Test
    public void naturalJpegPlanHasCanonicalOrderAndTransitions() {
        RenderPipelinePlan plan = RenderPipelinePlan.naturalJpeg();

        assertEquals(RenderStage.INPUT_NORMALIZATION, plan.first().stage());
        assertEquals(RenderStage.ENCODING, plan.last().stage());
        assertEquals(ImageEncoding.srgb8(), plan.last().outputEncoding());
        assertTrue(plan.includes(RenderStage.ROBUST_MERGE));
        assertTrue(plan.includes(RenderStage.SUPER_RESOLUTION));

        int previousOrder = -1;
        RenderStageSpec previous = null;
        for (RenderStageSpec stage : plan.stages()) {
            assertTrue(stage.stage().order() > previousOrder);
            assertTrue(stage.preservesAllMetadata());
            if (previous != null) {
                assertEquals(previous.outputEncoding(), stage.inputEncoding());
            }
            previousOrder = stage.stage().order();
            previous = stage;
        }
    }

    @Test
    public void unsafeStageOrderAndPrecisionAreRejected() {
        ImageEncoding linear = ImageEncoding.linearSrgb16();
        ImageEncoding display = ImageEncoding.srgb8();

        expectIllegalArgument(() -> new RenderStageSpec(
                RenderStage.ROBUST_MERGE,
                display,
                display,
                true
        ));
        expectIllegalArgument(() -> new RenderPipelinePlan(Arrays.asList(
                new RenderStageSpec(RenderStage.TONE_MAPPING, linear, display, true),
                new RenderStageSpec(RenderStage.COLOR_TRANSFORM, display, display, true),
                new RenderStageSpec(RenderStage.ENCODING, display, display, true)
        )));
        expectIllegalArgument(() -> new RenderPipelinePlan(Arrays.asList(
                new RenderStageSpec(RenderStage.ROBUST_MERGE, linear, linear, true),
                new RenderStageSpec(RenderStage.ENCODING, linear, linear, true)
        )));
    }

    @Test
    public void metadataIsImmutableAndPropagatedByContract() {
        RenderMetadata empty = RenderMetadata.empty();
        RenderMetadata metadata = empty
                .with(RenderMetadata.REFERENCE_FRAME_ID, "frame-3")
                .with(RenderMetadata.SOURCE_FRAME_COUNT, 8)
                .with(RenderMetadata.LENS_ROUTE_ID, "main");

        assertFalse(empty.contains(RenderMetadata.REFERENCE_FRAME_ID));
        assertEquals("frame-3", metadata.get(RenderMetadata.REFERENCE_FRAME_ID).get());
        assertEquals(Integer.valueOf(8), metadata.get(RenderMetadata.SOURCE_FRAME_COUNT).get());
        assertEquals("main", metadata.snapshotByName().get("lensRouteId"));
        expectIllegalArgument(() -> new RenderStageSpec(
                RenderStage.DENOISE,
                ImageEncoding.linearSrgb16(),
                ImageEncoding.linearSrgb16(),
                false
        ));
    }

    @Test
    public void conservativeFallbackSacrificesDetailBeforeNaturalness() {
        ConservativeFallbackPolicy policy = new ConservativeFallbackPolicy();
        ArtifactReport severeGhosting = new ArtifactReport(
                RenderStage.ROBUST_MERGE,
                Collections.singletonList(new ArtifactFinding(
                        ArtifactType.GHOSTING,
                        0.9,
                        ConfidenceMask.filled(1, 1, 1.0f),
                        "moving subject duplicated"
                ))
        );
        assertTrue(policy.decide(severeGhosting).usesReferenceOnly());

        ArtifactReport detailArtifacts = new ArtifactReport(
                RenderStage.SHARPENING,
                Arrays.asList(
                        new ArtifactFinding(
                                ArtifactType.SYNTHETIC_TEXTURE,
                                0.5,
                                null,
                                "invented high-frequency texture"
                        ),
                        new ArtifactFinding(
                                ArtifactType.RINGING,
                                0.4,
                                null,
                                "edge overshoot"
                        )
                )
        );
        FallbackDecision decision = policy.decide(detailArtifacts);
        assertTrue(decision.actions().contains(FallbackAction.DISABLE_SUPER_RESOLUTION));
        assertTrue(decision.actions().contains(FallbackAction.DISABLE_SHARPENING));
        assertFalse(decision.usesReferenceOnly());
    }

    @Test
    public void jpegEncodingAndQualityPolicyAreExplicit() {
        RenderingQualityPolicy quality = RenderingQualityPolicy.naturalStill();
        assertEquals(
                EnumSet.allOf(RenderingQualityGoal.class),
                quality.goals()
        );
        assertTrue(quality.accepts(ArtifactReport.clean(RenderStage.TONE_MAPPING)));
        assertFalse(quality.accepts(new ArtifactReport(
                RenderStage.TONE_MAPPING,
                Collections.singletonList(new ArtifactFinding(
                        ArtifactType.HIGHLIGHT_CLIPPING,
                        0.5,
                        null,
                        "clipped highlight region"
                ))
        )));

        JpegEncodingOptions options = new JpegEncodingOptions(
                96,
                ColorSpace.SRGB,
                false,
                false
        );
        assertEquals(96, options.quality());
        assertFalse(options.includeLocation());
        expectIllegalArgument(() -> new JpegEncodingOptions(
                96,
                ColorSpace.LINEAR_SRGB,
                false,
                false
        ));

        byte[] source = {1, 2, 3};
        EncodedImage image = new EncodedImage(
                "image/jpeg",
                source,
                RenderMetadata.empty()
        );
        source[0] = 9;
        assertEquals(1, image.copyBytes()[0]);
    }

    @Test
    public void renderImageRequiresBufferAndEncodingBitDepthAgreement() {
        RenderImage image = new RenderImage(
                new TestFrameBuffer(16),
                ImageEncoding.linearSrgb16(),
                RenderMetadata.empty()
        );
        assertEquals(16, image.encoding().bitDepth());
        expectIllegalArgument(() -> new RenderImage(
                new TestFrameBuffer(16),
                ImageEncoding.srgb8(),
                RenderMetadata.empty()
        ));
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
        private final int bitDepth;
        private final ByteBuffer data = ByteBuffer.allocate(16).asReadOnlyBuffer();

        TestFrameBuffer(int bitDepth) {
            this.bitDepth = bitDepth;
        }

        @Override public int width() { return 2; }
        @Override public int height() { return 2; }
        @Override public int bitDepth() { return bitDepth; }
        @Override public Format format() { return Format.LINEAR_RGB; }
        @Override public long sizeBytes() { return data.capacity(); }
        @Override public ByteBuffer readOnlyData() { return data.asReadOnlyBuffer(); }
        @Override public void close() { }
    }
}
