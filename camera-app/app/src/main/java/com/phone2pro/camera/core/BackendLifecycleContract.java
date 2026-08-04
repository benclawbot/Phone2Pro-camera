package com.phone2pro.camera.core;

import java.util.Collections;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

/** Shared lifecycle transition contract for every concrete camera backend. */
public final class BackendLifecycleContract {
    private final Map<BackendLifecycleState, Set<BackendLifecycleState>> transitions;

    public BackendLifecycleContract(
            Map<BackendLifecycleState, Set<BackendLifecycleState>> transitions
    ) {
        if (transitions == null) {
            throw new NullPointerException("transitions");
        }
        EnumMap<BackendLifecycleState, Set<BackendLifecycleState>> copy =
                new EnumMap<>(BackendLifecycleState.class);
        for (BackendLifecycleState state : BackendLifecycleState.values()) {
            Set<BackendLifecycleState> next = transitions.get(state);
            if (next == null) {
                throw new IllegalArgumentException("missing transitions for " + state);
            }
            EnumSet<BackendLifecycleState> set = next.isEmpty()
                    ? EnumSet.noneOf(BackendLifecycleState.class)
                    : EnumSet.copyOf(next);
            copy.put(state, Collections.unmodifiableSet(set));
        }
        this.transitions = Collections.unmodifiableMap(copy);
    }

    public static BackendLifecycleContract standard() {
        EnumMap<BackendLifecycleState, Set<BackendLifecycleState>> map =
                new EnumMap<>(BackendLifecycleState.class);
        map.put(BackendLifecycleState.IDLE, EnumSet.of(
                BackendLifecycleState.DISCOVERING,
                BackendLifecycleState.CLOSED
        ));
        map.put(BackendLifecycleState.DISCOVERING, EnumSet.of(
                BackendLifecycleState.READY,
                BackendLifecycleState.ERROR,
                BackendLifecycleState.CLOSING
        ));
        map.put(BackendLifecycleState.READY, EnumSet.of(
                BackendLifecycleState.OPENING,
                BackendLifecycleState.CLOSING,
                BackendLifecycleState.ERROR
        ));
        map.put(BackendLifecycleState.OPENING, EnumSet.of(
                BackendLifecycleState.OPEN,
                BackendLifecycleState.ERROR,
                BackendLifecycleState.RECOVERING
        ));
        map.put(BackendLifecycleState.OPEN, EnumSet.of(
                BackendLifecycleState.CONFIGURING,
                BackendLifecycleState.CLOSING,
                BackendLifecycleState.ERROR
        ));
        map.put(BackendLifecycleState.CONFIGURING, EnumSet.of(
                BackendLifecycleState.STREAMING,
                BackendLifecycleState.ERROR,
                BackendLifecycleState.RECOVERING
        ));
        map.put(BackendLifecycleState.STREAMING, EnumSet.of(
                BackendLifecycleState.CAPTURING,
                BackendLifecycleState.CONFIGURING,
                BackendLifecycleState.CLOSING,
                BackendLifecycleState.ERROR,
                BackendLifecycleState.RECOVERING
        ));
        map.put(BackendLifecycleState.CAPTURING, EnumSet.of(
                BackendLifecycleState.STREAMING,
                BackendLifecycleState.ERROR,
                BackendLifecycleState.RECOVERING
        ));
        map.put(BackendLifecycleState.RECOVERING, EnumSet.of(
                BackendLifecycleState.READY,
                BackendLifecycleState.OPENING,
                BackendLifecycleState.CLOSING,
                BackendLifecycleState.ERROR
        ));
        map.put(BackendLifecycleState.CLOSING, EnumSet.of(
                BackendLifecycleState.CLOSED,
                BackendLifecycleState.ERROR
        ));
        map.put(BackendLifecycleState.CLOSED, EnumSet.of(
                BackendLifecycleState.DISCOVERING
        ));
        map.put(BackendLifecycleState.ERROR, EnumSet.of(
                BackendLifecycleState.RECOVERING,
                BackendLifecycleState.CLOSING,
                BackendLifecycleState.CLOSED
        ));
        return new BackendLifecycleContract(map);
    }

    public boolean allows(BackendLifecycleState from, BackendLifecycleState to) {
        if (from == null || to == null) {
            throw new NullPointerException("lifecycle state");
        }
        return transitions.get(from).contains(to);
    }

    public Set<BackendLifecycleState> allowedNext(BackendLifecycleState from) {
        if (from == null) {
            throw new NullPointerException("from");
        }
        return transitions.get(from);
    }
}
