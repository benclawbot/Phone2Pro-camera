package com.phone2pro.camera.storage;

/** Action selected when replaying the persistent asset journal after startup. */
public enum RecoveryAction {
    KEEP_PUBLISHED,
    PUBLISH_READY_ASSET,
    RESUME_PROCESSING,
    WAIT_FOR_ACTIVE_WRITER,
    DELETE_PENDING_ROW,
    REMOVE_TERMINAL_JOURNAL_RECORD
}
