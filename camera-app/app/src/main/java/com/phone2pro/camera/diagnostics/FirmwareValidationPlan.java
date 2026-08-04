package com.phone2pro.camera.diagnostics;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Set;

/** Immutable diagnostic module plan for a named firmware build. */
public final class FirmwareValidationPlan {
    private final String buildFingerprint;
    private final Set<FirmwareValidationModule> modules;
    private final boolean explicitRiskConsent;

    public FirmwareValidationPlan(
            String buildFingerprint,
            Set<FirmwareValidationModule> modules,
            boolean explicitRiskConsent
    ) {
        if (buildFingerprint == null || buildFingerprint.isEmpty()) {
            throw new IllegalArgumentException("buildFingerprint must not be empty");
        }
        if (modules == null || modules.isEmpty()) {
            throw new IllegalArgumentException("validation plan must contain modules");
        }
        EnumSet<FirmwareValidationModule> copy = EnumSet.copyOf(modules);
        if (!explicitRiskConsent) {
            for (FirmwareValidationModule module : copy) {
                if (!module.safeByDefault()) {
                    throw new IllegalArgumentException(
                            module + " requires explicit risk consent and a guarded protocol"
                    );
                }
            }
        }
        this.buildFingerprint = buildFingerprint;
        this.modules = Collections.unmodifiableSet(copy);
        this.explicitRiskConsent = explicitRiskConsent;
    }

    public static FirmwareValidationPlan safeBaseline(String buildFingerprint) {
        EnumSet<FirmwareValidationModule> modules = EnumSet.noneOf(
                FirmwareValidationModule.class
        );
        for (FirmwareValidationModule module : FirmwareValidationModule.values()) {
            if (module.safeByDefault()) {
                modules.add(module);
            }
        }
        return new FirmwareValidationPlan(buildFingerprint, modules, false);
    }

    public String buildFingerprint() { return buildFingerprint; }
    public Set<FirmwareValidationModule> modules() { return modules; }
    public boolean explicitRiskConsent() { return explicitRiskConsent; }
}
