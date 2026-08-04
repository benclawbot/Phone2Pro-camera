package com.phone2pro.camera.privacy;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.EnumMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

public final class PrivacySecurityContractsTest {
    @Test
    public void everySensitiveKindHasAnExplicitLifetime() {
        DataHandlingPolicy policy = DataHandlingPolicy.privateByDefault();
        assertEquals(SensitiveDataKind.values().length, policy.rules().size());
        assertEquals(
                RetentionRule.LifetimeBoundary.FRAME_CONSUMED,
                policy.rule(SensitiveDataKind.PREVIEW_FRAME).boundary()
        );
        assertEquals(
                RetentionRule.LifetimeBoundary.PROCESSING_COMPLETED,
                policy.rule(SensitiveDataKind.PROCESSING_INTERMEDIATE).boundary()
        );
        assertEquals(
                RetentionRule.LifetimeBoundary.NEVER_COLLECT,
                policy.rule(SensitiveDataKind.LOCATION).boundary()
        );
        assertTrue(policy.rule(SensitiveDataKind.FINAL_IMAGE).persistentStorageAllowed());
        assertFalse(policy.rule(SensitiveDataKind.CAPTURE_FRAME).persistentStorageAllowed());
    }

    @Test
    public void diagnosticsAreOffByDefaultAndSensitiveFieldsNeverExport() {
        EnumMap<DiagnosticField, Object> fields = new EnumMap<>(DiagnosticField.class);
        fields.put(DiagnosticField.EVENT_TYPE, "capture_error");
        fields.put(DiagnosticField.TIMESTAMP, 123L);
        fields.put(DiagnosticField.BUILD_FINGERPRINT, "build");
        fields.put(DiagnosticField.BACKEND_ID, "public-main-camera2");
        fields.put(DiagnosticField.IMAGE_BYTES, new byte[]{1, 2});
        fields.put(DiagnosticField.CONTENT_URI, "content://private/1");
        fields.put(DiagnosticField.LOCATION, "47.0,8.0");
        fields.put(DiagnosticField.CAMERA_METADATA_VALUE, "secret-value");
        DiagnosticEvent event = new DiagnosticEvent(fields);
        DiagnosticRedactionPolicy redaction = new DiagnosticRedactionPolicy();

        assertFalse(redaction.redact(event, DiagnosticConsent.OFF).isPresent());
        Map<DiagnosticField, Object> eventsOnly = redaction
                .redact(event, DiagnosticConsent.REDACTED_EVENTS)
                .get()
                .fields();
        assertFalse(eventsOnly.containsKey(DiagnosticField.BUILD_FINGERPRINT));
        assertFalse(eventsOnly.containsKey(DiagnosticField.IMAGE_BYTES));
        assertFalse(eventsOnly.containsKey(DiagnosticField.CONTENT_URI));
        assertFalse(eventsOnly.containsKey(DiagnosticField.LOCATION));

        Map<DiagnosticField, Object> metadata = redaction
                .redact(event, DiagnosticConsent.REDACTED_METADATA)
                .get()
                .fields();
        assertEquals("build", metadata.get(DiagnosticField.BUILD_FINGERPRINT));
        for (DiagnosticField field : metadata.keySet()) {
            assertFalse(field.sensitive());
        }
    }

    @Test
    public void sensitiveResourceIsReleasedExactlyOnce() {
        AtomicInteger releases = new AtomicInteger();
        SensitiveResourceLease lease = new SensitiveResourceLease(
                SensitiveDataKind.CAPTURE_FRAME,
                releases::incrementAndGet
        );
        lease.requireOpen();
        lease.close();
        lease.close();
        assertTrue(lease.isClosed());
        assertEquals(1, releases.get());
        try {
            lease.requireOpen();
            throw new AssertionError("Expected closed lease failure");
        } catch (IllegalStateException expected) {
            // Expected.
        }
    }

    @Test
    public void productionProcessingContractAlwaysDeniesNetwork() {
        ProcessingSecurityContract contract = new ProcessingSecurityContract(
                "alignment",
                NetworkPolicy.DENIED,
                true,
                false
        );
        assertFalse(contract.networkPolicy().permitsNetwork());
        assertTrue(contract.acceptsUserContent());
        assertFalse(contract.writesTemporaryFiles());
    }

    @Test
    public void neverCollectedDataCannotBeStoredOrExported() {
        try {
            new RetentionRule(
                    SensitiveDataKind.LOCATION,
                    RetentionRule.LifetimeBoundary.NEVER_COLLECT,
                    true,
                    false,
                    "invalid"
            );
            throw new AssertionError("Expected invalid retention rule");
        } catch (IllegalArgumentException expected) {
            // Expected.
        }
    }
}
