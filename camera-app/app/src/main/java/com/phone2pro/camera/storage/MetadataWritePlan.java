package com.phone2pro.camera.storage;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Set;

/** Exact metadata allowlist generated before final asset publication. */
public final class MetadataWritePlan {
    private final Set<MetadataField> included;
    private final Set<MetadataField> omittedForPrivacy;

    private MetadataWritePlan(
            Set<MetadataField> included,
            Set<MetadataField> omittedForPrivacy
    ) {
        this.included = Collections.unmodifiableSet(EnumSet.copyOf(included));
        this.omittedForPrivacy = Collections.unmodifiableSet(EnumSet.copyOf(omittedForPrivacy));
    }

    public static MetadataWritePlan from(MetadataPrivacyPolicy policy) {
        EnumSet<MetadataField> included = EnumSet.of(
                MetadataField.ORIENTATION,
                MetadataField.CAPTURE_TIMESTAMP,
                MetadataField.EXPOSURE_TIME,
                MetadataField.SENSITIVITY_ISO,
                MetadataField.FOCAL_LENGTH,
                MetadataField.LENS_ROUTE,
                MetadataField.CAPTURE_PROFILE,
                MetadataField.SOFTWARE
        );
        EnumSet<MetadataField> omitted = EnumSet.noneOf(MetadataField.class);
        includeOrOmit(policy.includeLocation(), MetadataField.LOCATION, included, omitted);
        includeOrOmit(
                policy.includeDeviceIdentity(),
                MetadataField.DEVICE_MAKE_MODEL,
                included,
                omitted
        );
        includeOrOmit(
                policy.includeDiagnosticMetadata(),
                MetadataField.DIAGNOSTIC_XMP,
                included,
                omitted
        );
        includeOrOmit(
                policy.includeProcessingXmp(),
                MetadataField.PROCESSING_XMP,
                included,
                omitted
        );
        return new MetadataWritePlan(included, omitted);
    }

    public Set<MetadataField> included() { return included; }
    public Set<MetadataField> omittedForPrivacy() { return omittedForPrivacy; }

    private static void includeOrOmit(
            boolean enabled,
            MetadataField field,
            EnumSet<MetadataField> included,
            EnumSet<MetadataField> omitted
    ) {
        if (enabled) {
            included.add(field);
        } else {
            omitted.add(field);
        }
    }
}
