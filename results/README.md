# Results

Empty until the first data drop — until an entry exists here for a corpus
version, this benchmark ranks nothing.

Layout per drop:

```
results/
  corpus-v0.1/
    prompts/              full prompt text per arm, hashed
    arms.json             the arm registry for this drop (reviewer/model/config)
    runs/<arm-id>/<case-id>.json   conforms to schema/run.schema.json
    aggregates.json       mechanically computed from runs/ (published script)
    telemetry.md          per-arm telemetry disclosure (what each engine reports)
```

Rules (see [METHODOLOGY.md](../METHODOLOGY.md)):

- Every aggregate is recomputable from the published `runs/` records by the
  published script; `aggregates.json` is never hand-edited.
- Failures, timeouts, and refusals stay in the data — an engine's bad day is
  a result.
- Cost columns exist only for arms whose `telemetry.cost_usd.provenance` is
  `authoritative` (or explicitly labeled `modeled`).
- Corrections are new tagged versions with a CHANGELOG entry, never in-place
  rewrites.
