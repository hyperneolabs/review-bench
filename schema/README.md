# Schemas

JSON Schema (draft 2020-12) for the three record types the benchmark
publishes:

| Schema | Describes |
|---|---|
| [`case.schema.json`](case.schema.json) | A benchmark case: provenance pinned by SHA, ground truth for bug cases, absent for controls |
| [`run.schema.json`](run.schema.json) | One arm reviewing one case: configuration, raw-output reference, telemetry with provenance, per-finding grades |
| [`finding-envelope.schema.json`](finding-envelope.schema.json) | The structured report contract self-hosted engine arms return (the production envelope) |

Everything under `cases/` and `results/` validates against these schemas;
CI (added with the first data drop) enforces it. Schema changes bump
`schema_version` and get a [CHANGELOG](../CHANGELOG.md) entry — records
already published under an older schema version are not rewritten.

In `run.schema.json`, note two fields that exist to keep the benchmark
honest rather than to describe the data nicely:

- `telemetry.cost_usd.provenance` — `authoritative` (reported by the
  engine/provider) or `modeled` (computed from a published pricing table).
  Absent means the engine reports no cost dimension at all.
- `arm.config` / `arm.plan_tier` — full disclosure of what was run,
  including the commercial plan for third-party product arms.
