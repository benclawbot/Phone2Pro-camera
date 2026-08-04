package com.phone2pro.camera.vendor;

import java.util.List;

/**
 * Android/vendor-specific bridge. Portable camera logic depends only on this interface and plans.
 */
public interface VendorSettingsApplier {
    VendorExecutionResult applySessionSettings(
            List<VendorSetting<?>> settings,
            long timeoutMillis
    );

    VendorExecutionResult applyPerFrameSettings(
            List<VendorSetting<?>> settings,
            long timeoutMillis
    );
}
