# Cases

Empty until the first corpus drop. Layout per frozen corpus version:

```
cases/
  corpus-v0.1.json        frozen manifest: every case_id + kind + SHA provenance
  <case-id>/
    case.json             conforms to schema/case.schema.json
    review.diff           the diff under review (the introducing change)
    fix.diff              the ground-truth fix (bug cases)
```

- Bug cases and clean controls live side by side, distinguished by `kind`.
- `review.diff` and `fix.diff` redistribute upstream code from permissively
  licensed repositories; the license is recorded per case in `case.json`.
- A case is never edited after its corpus version is tagged — corrections
  require a new corpus version (see
  [METHODOLOGY.md §2.3](../METHODOLOGY.md#23-versioning-and-freezing)).

Case nominations: see [the contributing section](../README.md#contributing).
