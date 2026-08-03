---
name: Camera research task
about: Map or validate one camera capability, interface or boundary
title: "[CAM-XXX] "
labels: ""
assignees: ""
---

## Objective

Describe the single capability, interface, route or boundary this issue must establish.

## Scope

- Included:
- Excluded:

## Questions to answer

- [ ] Which subsystem owns the behaviour?
- [ ] What exact API, key, method, service, symbol or configuration is used?
- [ ] What values, ordering and dependencies are valid?
- [ ] Which process identity, permission, signature or SELinux domain is required?
- [ ] Can the replacement app reproduce it?
- [ ] Where is failure enforced when it cannot?

## Evidence sources

- [ ] Target-device observation
- [ ] Nothing Camera APK/decompiled code
- [ ] Target firmware/framework/native binary
- [ ] Nothing OSS/kernel source
- [ ] AOSP/official Android documentation
- [ ] MediaTek public source
- [ ] Community corroboration
- [ ] Open-source implementation or paper

## Method

Document commands, tools, versions and controlled positive/negative tests.

## Required artifacts

- Raw outputs and hashes
- Build fingerprint and package versions
- Relevant code excerpts or symbol addresses
- Trace/log correlation
- Structured capability-database update

## Acceptance criteria

- [ ] Result is reproducible.
- [ ] Claims use the evidence and confidence model.
- [ ] Negative findings are limited to the exact mechanism tested.
- [ ] Replacement-app consequence is documented.
- [ ] Follow-up unknowns are filed as separate issues.
