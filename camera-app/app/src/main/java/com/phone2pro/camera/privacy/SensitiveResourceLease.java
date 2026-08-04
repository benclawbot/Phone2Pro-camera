package com.phone2pro.camera.privacy;

import java.util.Objects;

/**
 * Enforces single-owner release for a sensitive buffer, intermediate, or metadata container.
 */
public final class SensitiveResourceLease implements AutoCloseable {
    private final SensitiveDataKind kind;
    private final Runnable releaser;
    private boolean closed;

    public SensitiveResourceLease(SensitiveDataKind kind, Runnable releaser) {
        this.kind = Objects.requireNonNull(kind, "kind");
        this.releaser = Objects.requireNonNull(releaser, "releaser");
    }

    public synchronized SensitiveDataKind kind() { return kind; }

    public synchronized boolean isClosed() { return closed; }

    public synchronized void requireOpen() {
        if (closed) {
            throw new IllegalStateException("sensitive resource has already been released");
        }
    }

    @Override
    public synchronized void close() {
        if (closed) {
            return;
        }
        closed = true;
        releaser.run();
    }
}
