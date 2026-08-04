package com.phone2pro.camera.capture;

import java.util.concurrent.atomic.AtomicBoolean;

/** Thread-safe cancellation signal checked before request submission and between burst frames. */
public final class CaptureCancellation {
    private final AtomicBoolean cancelled = new AtomicBoolean();

    public boolean cancel() {
        return cancelled.compareAndSet(false, true);
    }

    public boolean isCancelled() {
        return cancelled.get();
    }

    public void throwIfCancelled() {
        if (isCancelled()) {
            throw new CaptureCancelledException();
        }
    }

    public static final class CaptureCancelledException extends RuntimeException {
        public CaptureCancelledException() {
            super("Capture request was cancelled.");
        }
    }
}
