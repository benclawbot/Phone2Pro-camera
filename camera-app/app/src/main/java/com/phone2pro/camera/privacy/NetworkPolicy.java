package com.phone2pro.camera.privacy;

/** Network contract for every production processing stage. */
public enum NetworkPolicy {
    DENIED;

    public boolean permitsNetwork() {
        return false;
    }
}
