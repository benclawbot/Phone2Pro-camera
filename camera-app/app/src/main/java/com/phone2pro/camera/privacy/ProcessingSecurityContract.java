package com.phone2pro.camera.privacy;

import java.util.Objects;

/** Security declaration required from every production processing stage. */
public final class ProcessingSecurityContract {
    private final String stageId;
    private final NetworkPolicy networkPolicy;
    private final boolean acceptsUserContent;
    private final boolean writesTemporaryFiles;

    public ProcessingSecurityContract(
            String stageId,
            NetworkPolicy networkPolicy,
            boolean acceptsUserContent,
            boolean writesTemporaryFiles
    ) {
        this.stageId = Objects.requireNonNull(stageId, "stageId");
        this.networkPolicy = Objects.requireNonNull(networkPolicy, "networkPolicy");
        if (stageId.isEmpty()) {
            throw new IllegalArgumentException("stageId must not be empty");
        }
        if (networkPolicy.permitsNetwork()) {
            throw new IllegalArgumentException("production processing stages may not use network access");
        }
        this.acceptsUserContent = acceptsUserContent;
        this.writesTemporaryFiles = writesTemporaryFiles;
    }

    public String stageId() { return stageId; }
    public NetworkPolicy networkPolicy() { return networkPolicy; }
    public boolean acceptsUserContent() { return acceptsUserContent; }
    public boolean writesTemporaryFiles() { return writesTemporaryFiles; }
}
