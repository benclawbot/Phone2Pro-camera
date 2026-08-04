package com.phone2pro.camera.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.phone2pro.camera.backend.PublicMainBackend;

import org.junit.Test;

import java.util.EnumMap;

public final class CameraBackendContractTest {
    @Test
    public void everyBackendExposesBuildAwareRuntimeContract() {
        RouteBackend backend = new PublicMainBackend();
        CameraBackendContract contract = backend.contract();

        assertEquals(PublicMainBackend.BACKEND_ID, contract.backendId());
        assertTrue(contract.buildAware());
        assertTrue(contract.runtimeCapabilityDiscovery());
        assertTrue(contract.errorCategories().contains(BackendErrorCategory.PERMISSION));
        assertTrue(contract.errorCategories().contains(BackendErrorCategory.THERMAL));
        assertTrue(contract.metadataFields().contains(BackendMetadataField.SENSOR_TIMESTAMP));
        assertTrue(contract.metadataFields().contains(BackendMetadataField.ACTIVE_ROUTE));
    }

    @Test
    public void standardLifecycleAllowsRecoveryButRejectsInvalidJump() {
        BackendLifecycleContract lifecycle = BackendLifecycleContract.standard();
        assertTrue(lifecycle.allows(
                BackendLifecycleState.IDLE,
                BackendLifecycleState.DISCOVERING
        ));
        assertTrue(lifecycle.allows(
                BackendLifecycleState.STREAMING,
                BackendLifecycleState.CAPTURING
        ));
        assertTrue(lifecycle.allows(
                BackendLifecycleState.ERROR,
                BackendLifecycleState.RECOVERING
        ));
        assertFalse(lifecycle.allows(
                BackendLifecycleState.IDLE,
                BackendLifecycleState.CAPTURING
        ));
        assertFalse(lifecycle.allows(
                BackendLifecycleState.CLOSED,
                BackendLifecycleState.STREAMING
        ));
    }

    @Test
    public void errorStateRequiresNormalizedErrorCategory() {
        BackendStatusSnapshot error = new BackendStatusSnapshot(
                "public-main-camera2",
                BackendLifecycleState.ERROR,
                BackendErrorCategory.DISCONNECTED,
                "Camera disconnected during capture.",
                100L
        );
        assertEquals(BackendErrorCategory.DISCONNECTED, error.errorCategory().get());

        expectIllegalArgument(() -> new BackendStatusSnapshot(
                "public-main-camera2",
                BackendLifecycleState.ERROR,
                null,
                "missing category",
                100L
        ));
        expectIllegalArgument(() -> new BackendStatusSnapshot(
                "public-main-camera2",
                BackendLifecycleState.READY,
                BackendErrorCategory.INTERNAL,
                "unexpected category",
                100L
        ));
    }

    @Test
    public void normalizedMetadataIsImmutableAndTyped() {
        EnumMap<BackendMetadataField, Object> source = new EnumMap<>(BackendMetadataField.class);
        source.put(BackendMetadataField.FRAME_NUMBER, 7L);
        source.put(BackendMetadataField.SENSOR_TIMESTAMP, 12345L);
        source.put(BackendMetadataField.FOCAL_LENGTH, 5.56f);
        source.put(BackendMetadataField.ACTIVE_ROUTE, OpticalRoute.MAIN.id());
        NormalizedBackendMetadata metadata = new NormalizedBackendMetadata(
                "public-main-camera2",
                source
        );
        source.put(BackendMetadataField.FRAME_NUMBER, 9L);

        assertEquals(Long.valueOf(7L), metadata.get(
                BackendMetadataField.FRAME_NUMBER,
                Long.class
        ).get());
        assertEquals(Float.valueOf(5.56f), metadata.get(
                BackendMetadataField.FOCAL_LENGTH,
                Float.class
        ).get());
        try {
            metadata.get(BackendMetadataField.FOCAL_LENGTH, Long.class);
            throw new AssertionError("Expected typed metadata failure");
        } catch (IllegalStateException expected) {
            // Expected.
        }
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
