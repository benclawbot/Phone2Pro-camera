# Typed vendor-tag database

This directory documents the generated MediaTek and Nothing camera metadata database stored at `data/vendor-tags/database.v1.json`.

The database is generated from committed evidence by `tools/build-vendor-tag-database.py` and validated by `tools/validate-vendor-tag-database.py`.

## Evidence rules

Every record must preserve the distinction between verified observations, partial verification, hypotheses and unknowns. Unknown value layouts or semantics must remain explicit and must not be promoted into production probe values.

## Regeneration

```bash
python3 tools/build-vendor-tag-database.py
python3 tools/validate-vendor-tag-database.py
```

The validator checks schema integrity, unique key identity, direction and type fields, camera/build scope, evidence links, confidence classification and explicit handling of unknown structures.
