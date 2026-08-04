package com.phone2pro.camera.imaging;

/** Clock domains that may appear in capture and motion metadata. */
public enum TimestampDomain {
    /** Camera sensor timestamps, normally represented by SENSOR_TIMESTAMP. */
    CAMERA_SENSOR,
    /** Android elapsed realtime / monotonic time including deep sleep. */
    ELAPSED_REALTIME,
    /** Android uptime / monotonic time excluding deep sleep. */
    UPTIME,
    /** Unix wall-clock time. Never align frames directly in this domain. */
    WALL_CLOCK,
    /** The producer did not establish the source clock. */
    UNKNOWN
}
