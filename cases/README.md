# Cases

Corpus v0.1 is being mined in batches; batches 1–2 (17 bug + 10 control cases)
have landed and the corpus is not yet frozen. Layout per frozen corpus version:

```
cases/
  sampling-v0.1.md        the written sampling rule for v0.1 mining
  corpus-v0.1.json        frozen manifest: every case_id + kind + SHA provenance
                          (committed at freeze time, not yet present)
  <case-id>/
    case.json             conforms to schema/case.schema.json
    review.diff           the diff under review (the introducing change)
    fix.diff              the ground-truth fix (bug cases only)
```

- Bug cases and clean controls live side by side, distinguished by `kind`.
- `review.diff` and `fix.diff` redistribute upstream code from permissively
  licensed repositories; the license is recorded per case in `case.json`.
- A case is never edited after its corpus version is tagged — corrections
  require a new corpus version (see
  [METHODOLOGY.md §2.3](../METHODOLOGY.md#23-versioning-and-freezing)).
- Validate locally: `python3 tools/validate_cases.py` from the repository root.

Case nominations: see [the contributing section](../README.md#contributing).
