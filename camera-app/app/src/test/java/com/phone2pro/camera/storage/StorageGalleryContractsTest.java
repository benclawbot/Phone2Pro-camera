package com.phone2pro.camera.storage;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.OpticalRoute;

import org.junit.Test;

public final class StorageGalleryContractsTest {
    private final AssetLifecyclePolicy lifecycle = new AssetLifecyclePolicy();

    @Test
    public void pendingAssetRemainsHiddenUntilAtomicPublication() {
        CaptureAssetRecord record = reserved(100L);
        assertFalse(record.lifecycle().visibleToOtherApps());
        expectIllegalState(() -> ThumbnailReference.fromPublished(record));
        expectIllegalState(() -> ViewerIntentSpec.forPublished(record));

        record = lifecycle.transition(record, AssetLifecycle.WRITING, false, 110L, null);
        record = lifecycle.transition(record, AssetLifecycle.PROCESSING, true, 120L, null);
        record = lifecycle.transition(record, AssetLifecycle.READY_TO_PUBLISH, true, 130L, null);
        assertFalse(record.lifecycle().visibleToOtherApps());
        record = lifecycle.transition(record, AssetLifecycle.PUBLISHED, true, 140L, null);

        assertTrue(record.lifecycle().visibleToOtherApps());
        ThumbnailReference thumbnail = ThumbnailReference.fromPublished(record);
        ViewerIntentSpec viewer = ViewerIntentSpec.forPublished(record);
        assertEquals(record.contentUri(), thumbnail.contentUri());
        assertTrue(thumbnail.accessibilityLabel().contains("1×"));
        assertEquals(ViewerIntentSpec.ACTION_VIEW, viewer.action());
        assertTrue(viewer.grantReadPermission());
    }

    @Test
    public void incompleteOrFailedAssetCannotBecomeVisible() {
        CaptureAssetRecord reserved = reserved(100L);
        expectIllegalState(() -> lifecycle.transition(
                reserved,
                AssetLifecycle.PUBLISHED,
                false,
                110L,
                null
        ));
        CaptureAssetRecord writing = lifecycle.transition(
                reserved,
                AssetLifecycle.WRITING,
                false,
                110L,
                null
        );
        CaptureAssetRecord failed = lifecycle.transition(
                writing,
                AssetLifecycle.FAILED,
                false,
                120L,
                "Encoder failed"
        );
        assertFalse(failed.lifecycle().visibleToOtherApps());
        assertEquals("Encoder failed", failed.failureReason().get());
        expectIllegalState(() -> lifecycle.transition(
                failed,
                AssetLifecycle.PUBLISHED,
                true,
                130L,
                null
        ));
    }

    @Test
    public void privateMetadataPolicyOmitsSensitiveFields() {
        MetadataPrivacyPolicy privacy = MetadataPrivacyPolicy.privateByDefault();
        MetadataWritePlan plan = MetadataWritePlan.from(privacy);

        assertTrue(plan.included().contains(MetadataField.ORIENTATION));
        assertTrue(plan.included().contains(MetadataField.FOCAL_LENGTH));
        assertTrue(plan.omittedForPrivacy().contains(MetadataField.LOCATION));
        assertTrue(plan.omittedForPrivacy().contains(MetadataField.DEVICE_MAKE_MODEL));
        assertTrue(plan.omittedForPrivacy().contains(MetadataField.DIAGNOSTIC_XMP));
        assertTrue(plan.omittedForPrivacy().contains(MetadataField.PROCESSING_XMP));
    }

    @Test
    public void metadataCanOnlyBeAddedByExplicitOptIn() {
        MetadataWritePlan plan = MetadataWritePlan.from(new MetadataPrivacyPolicy(
                true,
                false,
                false,
                true
        ));

        assertTrue(plan.included().contains(MetadataField.LOCATION));
        assertTrue(plan.included().contains(MetadataField.PROCESSING_XMP));
        assertTrue(plan.omittedForPrivacy().contains(MetadataField.DEVICE_MAKE_MODEL));
        assertTrue(plan.omittedForPrivacy().contains(MetadataField.DIAGNOSTIC_XMP));
    }

    @Test
    public void recoveryPublishesOrResumesOnlyFromDurableBytes() {
        AssetRecoveryPolicy recovery = new AssetRecoveryPolicy(1_000L);
        CaptureAssetRecord ready = lifecycle.transition(
                lifecycle.transition(reserved(100L), AssetLifecycle.WRITING, true, 110L, null),
                AssetLifecycle.READY_TO_PUBLISH,
                true,
                120L,
                null
        );
        assertEquals(
                RecoveryAction.PUBLISH_READY_ASSET,
                recovery.decide(ready, 2_000L).action()
        );

        CaptureAssetRecord processing = lifecycle.transition(
                lifecycle.transition(reserved(100L), AssetLifecycle.WRITING, true, 110L, null),
                AssetLifecycle.PROCESSING,
                true,
                120L,
                null
        );
        assertEquals(
                RecoveryAction.RESUME_PROCESSING,
                recovery.decide(processing, 2_000L).action()
        );
    }

    @Test
    public void recoveryDeletesStaleUnrecoverablePendingRows() {
        AssetRecoveryPolicy recovery = new AssetRecoveryPolicy(1_000L);
        CaptureAssetRecord recentWriting = lifecycle.transition(
                reserved(100L),
                AssetLifecycle.WRITING,
                false,
                900L,
                null
        );
        assertEquals(
                RecoveryAction.WAIT_FOR_ACTIVE_WRITER,
                recovery.decide(recentWriting, 1_000L).action()
        );
        assertEquals(
                RecoveryAction.DELETE_PENDING_ROW,
                recovery.decide(recentWriting, 2_000L).action()
        );
    }

    @Test
    public void mediaStorePlanAlwaysUsesPendingPublication() {
        MediaStoreWritePlan plan = new MediaStoreWritePlan(
                "P2P_20260804_081500.jpg",
                "image/jpeg",
                "Pictures/Phone2Pro",
                90,
                MetadataPrivacyPolicy.privateByDefault()
        );

        assertTrue(plan.reserveAsPending());
        assertTrue(plan.publishByClearingPending());
        assertEquals(90, plan.orientationDegrees());
    }

    private static CaptureAssetRecord reserved(long now) {
        return CaptureAssetRecord.reserved(
                "asset-1",
                "content://media/external/images/media/1",
                "P2P_1.jpg",
                "image/jpeg",
                OpticalRoute.MAIN,
                CaptureProfile.AUTO,
                0,
                now
        );
    }

    private static void expectIllegalState(Runnable work) {
        try {
            work.run();
            throw new AssertionError("Expected IllegalStateException");
        } catch (IllegalStateException expected) {
            // Expected.
        }
    }
}
