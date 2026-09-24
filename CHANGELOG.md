# Changelog

Methodology, corpus, schemas, and results are versioned together; published
results are never silently rewritten.

## 0.3.0 — 2026-09-24

Corpus batch 2 — the Go-language pass queued by batch 1: 11 bug cases + 5
control cases across go-chi/chi, grpc/grpc-go, spf13/cobra, urfave/cli, and
stretchr/testify (Go). Every case is pinned by full upstream SHAs with ground
truth derived from the later fix; candidate dispositions, including 17
excluded candidates with their excluding criterion (the batch-1 mega-PR
pattern repeats: several strong containerd and urfave/cli candidates trace
to over-limit introducing PRs), are recorded in
[issue #3](https://github.com/hyperneolabs/review-bench/issues/3). The corpus
remains **not yet frozen** — no `corpus/v0.1` tag, no manifest, no results.

- `tools/build_cases_batch2.py`: the batch-2 build script (same blame
  attribution, fix-parent→review-head coordinate mapping, and per-line content
  verification as batch 1; additionally normalizes short pinned SHAs to full,
  and supports an explicit `review_base` for multi-commit landed runs).
- `cases/sampling-v0.1.md`: §2 step 5 amended to name a third landing shape —
  PRs landed as a series of rebased commits contribute the net diff of their
  landed commit run (cobra PR #414 is the batch's instance). Batch-2
  repository list appended to §1.
- `cases/README.md`: batch-1 count corrected (6 bug, not 7 — the repo holds
  11 batch-1 case directories); status updated for batches 1–2.

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
