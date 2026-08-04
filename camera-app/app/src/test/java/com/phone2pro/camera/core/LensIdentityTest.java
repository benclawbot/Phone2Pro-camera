package com.phone2pro.camera.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.OptionalDouble;

public final class LensIdentityTest {
    private static final double EPSILON = 0.0001;

    @Test
    public void staticRoutesExposeVerifiedGeometryAndUnknownAperture() {
        assertRoute(
                OpticalRoute.ULTRAWIDE,
                1.64f,
                15,
                15.0 / 1.64
        );
        assertRoute(
                OpticalRoute.MAIN,
                5.56f,
                24,
                24.0 / 5.56
        );
        assertRoute(
                OpticalRoute.TELEPHOTO,
                7.10f,
                50,
                50.0 / 7.10
        );
    }

    @Test
    public void fullyVerifiedIdentityRequiresVerifiedAperture() {
        LensIdentity identity = new LensIdentity(
                5.56f,
                24,
                OptionalDouble.of(1.8),
                EvidenceConfidence.VERIFIED,
                EvidenceConfidence.VERIFIED,
                "Controlled target measurement"
        );

        assertEquals(EvidenceConfidence.VERIFIED, identity.confidence());
        assertTrue(identity.aperture().isPresent());
        assertEquals(1.8, identity.aperture().getAsDouble(), EPSILON);
    }

    @Test(expected = IllegalArgumentException.class)
    public void missingApertureCannotClaimVerifiedConfidence() {
        new LensIdentity(
                5.56f,
                24,
                OptionalDouble.empty(),
                EvidenceConfidence.VERIFIED,
                EvidenceConfidence.VERIFIED,
                "Invalid evidence claim"
        );
    }

    @Test(expected = IllegalArgumentException.class)
    public void routeDimensionsMustBePositive() {
        new OpticalRoute(
                "invalid",
                "Invalid",
                LensIdentity.withUnknownAperture(
                        5.56f,
                        24,
                        EvidenceConfidence.UNKNOWN,
                        "Synthetic test"
                ),
                0,
                3072
        );
    }

    private static void assertRoute(
            OpticalRoute route,
            float physicalFocalLengthMm,
            int equivalentFocalLengthMm,
            double cropFactor
    ) {
        LensIdentity identity = route.lensIdentity();
        assertEquals(physicalFocalLengthMm, identity.physicalFocalLengthMm(), 0.001f);
        assertEquals(equivalentFocalLengthMm, identity.equivalentFocalLengthMm());
        assertEquals(cropFactor, identity.cropFactor(), EPSILON);
        assertEquals(EvidenceConfidence.VERIFIED, identity.geometryConfidence());
        assertEquals(EvidenceConfidence.UNKNOWN, identity.apertureConfidence());
        assertEquals(EvidenceConfidence.PARTIALLY_VERIFIED, identity.confidence());
        assertFalse(identity.aperture().isPresent());
        assertTrue(identity.evidence().contains("Exact aperture value is not yet recorded"));
    }
}
