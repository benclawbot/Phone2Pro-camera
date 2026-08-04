package com.phone2pro.camera.privacy;

import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;
import java.util.Objects;

/** Structured diagnostic event before consent and redaction are applied. */
public final class DiagnosticEvent {
    private final Map<DiagnosticField, Object> fields;

    public DiagnosticEvent(Map<DiagnosticField, Object> fields) {
        Objects.requireNonNull(fields, "fields");
        EnumMap<DiagnosticField, Object> copy = new EnumMap<>(DiagnosticField.class);
        for (Map.Entry<DiagnosticField, Object> entry : fields.entrySet()) {
            copy.put(
                    Objects.requireNonNull(entry.getKey(), "diagnostic field"),
                    Objects.requireNonNull(entry.getValue(), "diagnostic value")
            );
        }
        if (!copy.containsKey(DiagnosticField.EVENT_TYPE)
                || !copy.containsKey(DiagnosticField.TIMESTAMP)) {
            throw new IllegalArgumentException("diagnostic event requires type and timestamp");
        }
        this.fields = Collections.unmodifiableMap(copy);
    }

    public Map<DiagnosticField, Object> fields() { return fields; }
}
