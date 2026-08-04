package com.phone2pro.camera.capture;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.ResolvedCameraEndpoint;
import com.phone2pro.camera.core.RouteMechanism;
import com.phone2pro.camera.imaging.FrameMetadata;
import com.phone2pro.camera.imaging.TimestampDomain;

import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class CaptureSessionRequestEngineTest {
    @Test
    public void cameraXBoundaryRejectsDirectSessionFeatures() {
        expectIllegalArgument(() -> new CaptureSessionPlan(
                1,
                "camerax",
                SessionBinderKind.CAMERAX_PUBLIC,
                OpticalRoute.MAIN,
                endpoint(),
                CaptureProfile.AUTO,
                TimestampDomain.CAMERA_SENSOR,
                Collections.singletonList(StreamSpec.publicOutput(
                        StreamRole.STILL_JPEG,
                        "JPEG",
                        4080,
                        3072,
                        2
                )),
                Collections.singletonList(parameter(
                        "android.control.aeTargetFpsRange",
                        Integer.class,
                        30,
                        RequestParameterScope.SESSION
                )),
                Collections.emptyList(),
                Collections.emptyList()
        ));
    }

    @Test
    public void repeatingAndStillChangesDoNotRecreateSession() {
        CaptureSessionPlan active = directSession(
                3,
                Collections.singletonList(parameter(
                        "android.control.aeMode",
                        Integer.class,
                        1,
                        RequestParameterScope.REPEATING
                )),
                Collections.singletonList(parameter(
                        "android.jpeg.quality",
                        Integer.class,
                        95,
                        RequestParameterScope.STILL
                )),
                Collections.emptyList()
        );
        CaptureSessionPlan requested = directSession(
                4,
                Collections.singletonList(parameter(
                        "android.control.aeMode",
                        Integer.class,
                        2,
                        RequestParameterScope.REPEATING
                )),
                Collections.singletonList(parameter(
                        "android.jpeg.quality",
                        Integer.class,
                        90,
                        RequestParameterScope.STILL
                )),
                Collections.emptyList()
        );

        assertFalse(SessionRecreationDecision.compare(active, requested).recreateRequired());
    }

    @Test
    public void sessionParameterChangeRequiresRecreation() {
        CaptureSessionPlan active = directSession(
                3,
                Collections.emptyList(),
                Collections.emptyList(),
                Collections.singletonList(parameter(
                        "android.control.aeTargetFpsRange",
                        Integer.class,
                        30,
                        RequestParameterScope.SESSION
                ))
        );
        CaptureSessionPlan requested = directSession(
                4,
                Collections.emptyList(),
                Collections.emptyList(),
                Collections.singletonList(parameter(
                        "android.control.aeTargetFpsRange",
                        Integer.class,
                        60,
                        RequestParameterScope.SESSION
                ))
        );

        assertTrue(SessionRecreationDecision.compare(active, requested).recreateRequired());
    }

    @Test
    public void burstPlannerAppliesModifiersInOrder() {
        CaptureSessionPlan session = directSession(
                9,
                Collections.emptyList(),
                Collections.singletonList(parameter(
                        "android.jpeg.quality",
                        Integer.class,
                        95,
                        RequestParameterScope.STILL
                )),
                Collections.emptyList()
        );
        BackendRequestModifier bracket = new BackendRequestModifier() {
            @Override
            public String modifierId() {
                return "exposure-bracket";
            }

            @Override
            public List<RequestParameter<?>> modify(
                    CaptureRequestContext context,
                    List<RequestParameter<?>> currentParameters
            ) {
                List<RequestParameter<?>> modified = new ArrayList<>(currentParameters);
                modified.add(parameter(
                        "android.sensor.exposureTime",
                        Long.class,
                        10_000L + context.sequenceIndex(),
                        RequestParameterScope.STILL
                ));
                return modified;
            }
        };

        StillBurstPlan burst = new CaptureRequestPlanner().planStillBurst(
                session,
                "capture-1",
                3,
                CaptureRequestTemplate.STILL_CAPTURE,
                Collections.singletonList(bracket),
                new CaptureCancellation()
        );

        assertEquals(9, burst.sessionGeneration());
        assertEquals(3, burst.frames().size());
        assertEquals("capture-1:0", burst.frames().get(0).requestId());
        assertEquals(10_002L, burst.frames().get(2).parameters().get(1).value());
    }

    @Test
    public void modifierCannotEmitDuplicateOrVendorKeysOnPublicBinder() {
        CaptureSessionPlan session = directSession(
                1,
                Collections.emptyList(),
                Collections.singletonList(parameter(
                        "android.jpeg.quality",
                        Integer.class,
                        95,
                        RequestParameterScope.STILL
                )),
                Collections.emptyList()
        );
        BackendRequestModifier duplicate = modifierAdding(parameter(
                "android.jpeg.quality",
                Integer.class,
                90,
                RequestParameterScope.STILL
        ));
        expectIllegalArgument(() -> new CaptureRequestPlanner().planStillBurst(
                session,
                "duplicate",
                1,
                CaptureRequestTemplate.STILL_CAPTURE,
                Collections.singletonList(duplicate),
                new CaptureCancellation()
        ));

        BackendRequestModifier vendor = modifierAdding(parameter(
                "com.mediatek.capture.mode",
                Integer.class,
                1,
                RequestParameterScope.STILL
        ));
        expectIllegalArgument(() -> new CaptureRequestPlanner().planStillBurst(
                session,
                "vendor",
                1,
                CaptureRequestTemplate.STILL_CAPTURE,
                Collections.singletonList(vendor),
                new CaptureCancellation()
        ));
    }

    @Test
    public void cancellationStopsBurstBeforeSubmission() {
        CaptureCancellation cancellation = new CaptureCancellation();
        cancellation.cancel();
        try {
            new CaptureRequestPlanner().planStillBurst(
                    directSession(1, Collections.emptyList(), Collections.emptyList(), Collections.emptyList()),
                    "cancelled",
                    2,
                    CaptureRequestTemplate.STILL_CAPTURE,
                    Collections.emptyList(),
                    cancellation
            );
            throw new AssertionError("Expected CaptureCancelledException");
        } catch (CaptureCancellation.CaptureCancelledException expected) {
            assertTrue(cancellation.isCancelled());
        }
    }

    @Test
    public void transientFailuresEscalateAndPermanentFailuresDoNotRetry() {
        SessionRecoveryPolicy policy = new SessionRecoveryPolicy(1, 1, 1, 100);
        CaptureCancellation active = new CaptureCancellation();

        assertEquals(
                SessionRecoveryAction.RETRY_REQUEST,
                policy.decide(TransientFailureCategory.REQUEST_TIMEOUT, 0, true, active).action()
        );
        assertEquals(
                SessionRecoveryAction.RECREATE_SESSION,
                policy.decide(TransientFailureCategory.REQUEST_TIMEOUT, 1, true, active).action()
        );
        assertEquals(
                SessionRecoveryAction.FAIL_PERMANENT,
                policy.decide(TransientFailureCategory.REQUEST_TIMEOUT, 2, true, active).action()
        );
        assertEquals(
                SessionRecoveryAction.REOPEN_CAMERA,
                policy.decide(TransientFailureCategory.CAMERA_DISCONNECTED, 0, true, active).action()
        );
        assertEquals(
                SessionRecoveryAction.FAIL_PERMANENT,
                policy.decide(TransientFailureCategory.PERMISSION_DENIED, 0, true, active).action()
        );

        active.cancel();
        assertEquals(
                SessionRecoveryAction.CANCELLED,
                policy.decide(TransientFailureCategory.CAPTURE_FAILED, 0, true, active).action()
        );
    }

    @Test
    public void timestampsRemainCorrelatedOrFailClosed() {
        FrameMetadata metadata = new FrameMetadata(
                7,
                1_000_000L,
                TimestampDomain.CAMERA_SENSOR,
                10_000L,
                100,
                20_000L,
                0,
                5.56f
        );
        TimestampCorrelator correlator = new TimestampCorrelator(10);
        CorrelatedCaptureFrame correlated = correlator.correlate(
                new ImageTimestamp(
                        "capture-1:0",
                        7,
                        1_000_005L,
                        TimestampDomain.CAMERA_SENSOR
                ),
                metadata
        );
        assertEquals(5, correlated.timestampDeltaNs());
        assertEquals("capture-1:0", correlated.image().requestId());

        expectIllegalArgument(() -> correlator.correlate(
                new ImageTimestamp(
                        "capture-1:0",
                        8,
                        1_000_005L,
                        TimestampDomain.CAMERA_SENSOR
                ),
                metadata
        ));
        expectIllegalArgument(() -> correlator.correlate(
                new ImageTimestamp(
                        "capture-1:0",
                        7,
                        1_000_005L,
                        TimestampDomain.ELAPSED_REALTIME
                ),
                metadata
        ));
        expectIllegalArgument(() -> correlator.correlate(
                new ImageTimestamp(
                        "capture-1:0",
                        7,
                        1_000_100L,
                        TimestampDomain.CAMERA_SENSOR
                ),
                metadata
        ));
    }

    private static CaptureSessionPlan directSession(
            long generation,
            List<RequestParameter<?>> repeating,
            List<RequestParameter<?>> still,
            List<RequestParameter<?>> session
    ) {
        return new CaptureSessionPlan(
                generation,
                "camera2-public",
                SessionBinderKind.CAMERA2_DIRECT,
                OpticalRoute.MAIN,
                endpoint(),
                CaptureProfile.AUTO,
                TimestampDomain.CAMERA_SENSOR,
                Arrays.asList(
                        StreamSpec.publicOutput(StreamRole.PREVIEW, "PRIVATE", 1920, 1080, 3),
                        StreamSpec.publicOutput(StreamRole.STILL_JPEG, "JPEG", 4080, 3072, 2)
                ),
                session,
                repeating,
                still
        );
    }

    private static ResolvedCameraEndpoint endpoint() {
        return new ResolvedCameraEndpoint(
                "0",
                RouteMechanism.PUBLIC_CAMERA,
                "Unit-test public endpoint"
        );
    }

    private static BackendRequestModifier modifierAdding(RequestParameter<?> parameter) {
        return new BackendRequestModifier() {
            @Override
            public String modifierId() {
                return "test-modifier";
            }

            @Override
            public List<RequestParameter<?>> modify(
                    CaptureRequestContext context,
                    List<RequestParameter<?>> currentParameters
            ) {
                List<RequestParameter<?>> modified = new ArrayList<>(currentParameters);
                modified.add(parameter);
                return modified;
            }
        };
    }

    private static <T> RequestParameter<T> parameter(
            String key,
            Class<T> type,
            T value,
            RequestParameterScope scope
    ) {
        return new RequestParameter<>(key, type, value, scope);
    }

    private static void expectIllegalArgument(Runnable work) {
        try {
            work.run();
            throw new AssertionError("Expected IllegalArgumentException");
        } catch (IllegalArgumentException expected) {
            // Expected.
        }
    }
}
