package com.phone2pro.camera.storage;

import java.util.List;
import java.util.Optional;

/** Persistent journal required for recovery after app or process termination. */
public interface AssetJournal {
    void put(CaptureAssetRecord record);

    Optional<CaptureAssetRecord> find(String assetId);

    List<CaptureAssetRecord> all();

    void remove(String assetId);
}
