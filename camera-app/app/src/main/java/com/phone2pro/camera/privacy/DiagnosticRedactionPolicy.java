package com.phone2pro.camera.privacy;

import java.util.EnumMap;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/** Removes user content and sensitive identifiers before any diagnostic export. */
public final class DiagnosticRedactionPolicy {
    public Optional<RedactedDiagnosticEvent> redact(
            DiagnosticEvent event,
            DiagnosticConsent consent
    ) {
        Objects.requireNonNull(event, "event");
        Objects.requireNonNull(consent, "consent");
        if (consent == DiagnosticConsent.OFF) {
            return Optional.empty();
        }
        EnumMap<DiagnosticField, Object> safe = new EnumMap<>(DiagnosticField.class);
        for (Map.Entry<DiagnosticField, Object> entry : event.fields().entrySet()) {
            DiagnosticField field = entry.getKey();
            if (field.sensitive()) {
                continue;
            }
            if (consent == DiagnosticConsent.REDACTED_EVENTS
                    && field == DiagnosticField.BUILD_FINGERPRINT) {
                continue;
            }
            safe.put(field, entry.getValue());
        }
        return Optional.of(new RedactedDiagnosticEvent(safe));
    }
}
