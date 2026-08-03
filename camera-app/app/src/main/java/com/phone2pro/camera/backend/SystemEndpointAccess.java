package com.phone2pro.camera.backend;

import com.phone2pro.camera.core.DeviceCapabilitySnapshot;

/** Authorization probe for CameraService endpoints hidden from ordinary applications. */
public interface SystemEndpointAccess {
    boolean canOpen(String cameraId, DeviceCapabilitySnapshot capabilities);

    String evidence();
}
