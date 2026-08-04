package com.phone2pro.camera.vendor;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Immutable, scope-separated vendor settings for one verified feature. */
public final class VendorConfiguration {
    private final List<VendorSetting<?>> sessionSettings;
    private final List<VendorSetting<?>> perFrameSettings;

    public VendorConfiguration(
            List<VendorSetting<?>> sessionSettings,
            List<VendorSetting<?>> perFrameSettings
    ) {
        this.sessionSettings = immutableWithScope(
                sessionSettings,
                VendorSettingScope.SESSION,
                "sessionSettings"
        );
        this.perFrameSettings = immutableWithScope(
                perFrameSettings,
                VendorSettingScope.PER_FRAME,
                "perFrameSettings"
        );
        if (this.sessionSettings.isEmpty() && this.perFrameSettings.isEmpty()) {
            throw new IllegalArgumentException("vendor configuration must contain a setting");
        }
    }

    public List<VendorSetting<?>> sessionSettings() { return sessionSettings; }
    public List<VendorSetting<?>> perFrameSettings() { return perFrameSettings; }

    public List<VendorSetting<?>> settingsFor(VendorSettingScope scope) {
        Objects.requireNonNull(scope, "scope");
        return scope == VendorSettingScope.SESSION ? sessionSettings : perFrameSettings;
    }

    private static List<VendorSetting<?>> immutableWithScope(
            List<VendorSetting<?>> source,
            VendorSettingScope requiredScope,
            String name
    ) {
        Objects.requireNonNull(source, name);
        List<VendorSetting<?>> copy = new ArrayList<>(source.size());
        for (VendorSetting<?> setting : source) {
            Objects.requireNonNull(setting, name + " entry");
            if (setting.scope() != requiredScope) {
                throw new IllegalArgumentException(
                        setting.keyName() + " belongs to " + setting.scope()
                                + " but was supplied as " + requiredScope
                );
            }
            copy.add(setting);
        }
        return Collections.unmodifiableList(copy);
    }
}
