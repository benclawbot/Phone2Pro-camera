package com.phone2pro.camera.diagnostics;

import java.util.Objects;

/** Redacted error shown to users and stored in diagnostic reports. */
public final class UserFacingError {
    private final UserErrorCategory category;
    private final String message;
    private final boolean retryable;

    public UserFacingError(
            UserErrorCategory category,
            String message,
            boolean retryable
    ) {
        this.category = Objects.requireNonNull(category, "category");
        this.message = Objects.requireNonNull(message, "message");
        if (message.isEmpty()) {
            throw new IllegalArgumentException("message must not be empty");
        }
        this.retryable = retryable;
    }

    public UserErrorCategory category() { return category; }
    public String message() { return message; }
    public boolean retryable() { return retryable; }
}
