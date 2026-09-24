# Changelog

Methodology, corpus, schemas, and results are versioned together; published
results are never silently rewritten.

## 0.2.0 — 2026-09-24

First corpus data: batch 1 of corpus v0.1 mining — 6 bug cases + 5 control
cases across axios/axios, expressjs/express, encode/httpx, and serde-rs/json
(JavaScript, TypeScript, Python, Rust). Every case is pinned by full upstream
SHAs with ground truth derived from the later fix; candidate dispositions,
including 12 excluded candidates with their excluding criterion, are recorded
in [issue #1](https://github.com/hyperneolabs/review-bench/issues/1). The
corpus is **not yet frozen** — no `corpus/v0.1` tag, no manifest, no results;
mining continues (Go-language pass queued).

- `cases/sampling-v0.1.md`: the written sampling rule (repository selection,
  bug-case search, introducing-change identification, mechanical ground-truth
  anchoring, control selection) required by methodology §2.3 before any arm
  runs.
- `tools/validate_cases.py`: per-case schema validation plus structural checks
  (diff presence, reviewable-size limit, ground-truth files present in the
  review diff, controls carrying no fix artifacts).
- `tools/build_cases_batch1.py`: the batch-1 build script (blame attribution,
  fix-parent→review-head coordinate mapping, per-line content verification).
- CI: `.github/workflows/cases.yml` runs the validator on every push and PR.
- `schema/case.schema.json`: `fix_pr`/`fix_sha` (in `source`) and `fix_diff`
  (in `files`) are now required only for `kind: bug` — control cases have no
  fix by construction. Amended before the first data drop; no published case
  predates the change.

## 0.1.0 — 2026-09-24

Initial skeleton, published for public comment. No data yet.

- `METHODOLOGY.md` v0.1 draft: corpus construction (bug cases from merged
  upstream fixes + clean controls), arm definition and disclosure, match
  rule, finding grades, blinded two-grader protocol, telemetry-provenance
  rules, and the explicit non-claims (no aggregation/consensus arm until the
  product posts genuinely aggregated verdicts; no training-data hygiene
  claim).
- Schemas v0.1: `case.schema.json`, `run.schema.json`,
  `finding-envelope.schema.json`.
- Repository layout (`cases/`, `results/`) and license (CC BY 4.0).
