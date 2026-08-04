package com.phone2pro.camera.core;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Objects;
import java.util.Set;

/** Lifecycle, error and metadata contract shared by all camera backends. */
public final class CameraBackendContract {
    private final String backendId;
    private final BackendLifecycleContract lifecycle;
    private final Set<BackendErrorCategory> errorCategories;
    private final Set<BackendMetadataField> metadataFields;
    private final boolean buildAware;
    private final boolean runtimeCapabilityDiscovery;

    public CameraBackendContract(
            String backendId,
            BackendLifecycleContract lifecycle,
            Set<BackendErrorCategory> errorCategories,
            Set<BackendMetadataField> metadataFields,
            boolean buildAware,
            boolean runtimeCapabilityDiscovery
    ) {
        this.backendId = Objects.requireNonNull(backendId, "backendId");
        if (backendId.isEmpty()) {
            throw new IllegalArgumentException("backendId must not be empty");
        }
        this.lifecycle = Objects.requireNonNull(lifecycle, "lifecycle");
        if (errorCategories == null || errorCategories.isEmpty()) {
            throw new IllegalArgumentException("backend must expose error categories");
        }
        if (metadataFields == null || metadataFields.isEmpty()) {
            throw new IllegalArgumentException("backend must expose normalized metadata fields");
        }
        this.errorCategories = Collections.unmodifiableSet(EnumSet.copyOf(errorCategories));
        this.metadataFields = Collections.unmodifiableSet(EnumSet.copyOf(metadataFields));
        this.buildAware = buildAware;
        this.runtimeCapabilityDiscovery = runtimeCapabilityDiscovery;
    }

    public static CameraBackendContract standard(String backendId) {
        return new CameraBackendContract(
                backendId,
                BackendLifecycleContract.standard(),
                EnumSet.allOf(BackendErrorCategory.class),
                EnumSet.of(
                        BackendMetadataField.FRAME_NUMBER,
                        BackendMetadataField.SENSOR_TIMESTAMP,
                        BackendMetadataField.EXPOSURE_TIME,
                        BackendMetadataField.SENSITIVITY_ISO,
                        BackendMetadataField.FRAME_DURATION,
                        BackendMetadataField.FOCUS_DISTANCE,
                        BackendMetadataField.FOCAL_LENGTH,
                        BackendMetadataField.APERTURE,
                        BackendMetadataField.WHITE_BALANCE,
                        BackendMetadataField.CROP_REGION,
                        BackendMetadataField.ACTIVE_ROUTE,
                        BackendMetadataField.ORIENTATION,
                        BackendMetadataField.ERROR_CATEGORY
                ),
                true,
                true
        );
    }

    public String backendId() { return backendId; }
    public BackendLifecycleContract lifecycle() { return lifecycle; }
    public Set<BackendErrorCategory> errorCategories() { return errorCategories; }
    public Set<BackendMetadataField> metadataFields() { return metadataFields; }
    public boolean buildAware() { return buildAware; }
    public boolean runtimeCapabilityDiscovery() { return runtimeCapabilityDiscovery; }
}
