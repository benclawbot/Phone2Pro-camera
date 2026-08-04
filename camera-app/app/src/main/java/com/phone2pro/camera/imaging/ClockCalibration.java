package com.phone2pro.camera.imaging;

import com.phone2pro.camera.core.EvidenceConfidence;

import java.util.Objects;

/**
 * Affine mapping between two timestamp domains with an explicit uncertainty bound.
 *
 * <p>The mapping is:</p>
 * <pre>
 * target = targetAnchor + (source - sourceAnchor) * scale
 * </pre>
 */
public final class ClockCalibration {
    private final TimestampDomain sourceDomain;
    private final TimestampDomain targetDomain;
    private final long sourceAnchorNs;
    private final long targetAnchorNs;
    private final double scale;
    private final long uncertaintyNs;
    private final EvidenceConfidence confidence;
    private final String evidence;

    public ClockCalibration(
            TimestampDomain sourceDomain,
            TimestampDomain targetDomain,
            long sourceAnchorNs,
            long targetAnchorNs,
            double scale,
            long uncertaintyNs,
            EvidenceConfidence confidence,
            String evidence
    ) {
        this.sourceDomain = requireKnown(sourceDomain, "sourceDomain");
        this.targetDomain = requireKnown(targetDomain, "targetDomain");
        if (!(scale > 0.0) || !Double.isFinite(scale)) {
            throw new IllegalArgumentException("scale must be finite and positive");
        }
        if (uncertaintyNs < 0) {
            throw new IllegalArgumentException("uncertaintyNs must be non-negative");
        }
        this.sourceAnchorNs = sourceAnchorNs;
        this.targetAnchorNs = targetAnchorNs;
        this.scale = scale;
        this.uncertaintyNs = uncertaintyNs;
        this.confidence = Objects.requireNonNull(confidence, "confidence");
        this.evidence = Objects.requireNonNull(evidence, "evidence");
    }

    public long map(long sourceTimestampNs) {
        double mapped = targetAnchorNs
                + (sourceTimestampNs - (double) sourceAnchorNs) * scale;
        if (!Double.isFinite(mapped) || mapped > Long.MAX_VALUE || mapped < Long.MIN_VALUE) {
            throw new ArithmeticException("mapped timestamp is outside long range");
        }
        return Math.round(mapped);
    }

    public TimestampDomain sourceDomain() {
        return sourceDomain;
    }

    public TimestampDomain targetDomain() {
        return targetDomain;
    }

    public long sourceAnchorNs() {
        return sourceAnchorNs;
    }

    public long targetAnchorNs() {
        return targetAnchorNs;
    }

    public double scale() {
        return scale;
    }

    public long uncertaintyNs() {
        return uncertaintyNs;
    }

    public EvidenceConfidence confidence() {
        return confidence;
    }

    public String evidence() {
        return evidence;
    }

    private static TimestampDomain requireKnown(TimestampDomain domain, String name) {
        Objects.requireNonNull(domain, name);
        if (domain == TimestampDomain.UNKNOWN) {
            throw new IllegalArgumentException(name + " must be established before calibration");
        }
        return domain;
    }
}
