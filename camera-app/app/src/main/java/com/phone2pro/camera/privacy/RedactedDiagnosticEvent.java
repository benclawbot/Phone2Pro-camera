package com.phone2pro.camera.privacy;

import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;
import java.util.Objects;

/** Diagnostic payload after consent and redaction, safe for local export. */
public final class RedactedDiagnosticEvent {
    private final Map<DiagnosticField, Object> fields;

    RedactedDiagnosticEvent(Map<DiagnosticField, Object> fields) {
        Objects.requireNonNull(fields, "fields");
        this.fields = Collections.unmodifiableMap(new EnumMap<>(fields));
        for (DiagnosticField field : fields.keySet()) {
            if (field.sensitive()) {
                throw new IllegalArgumentException("redacted event contains sensitive field " + field);
            }
        }
    }

    public Map<DiagnosticField, Object> fields() { return fields; }
}
