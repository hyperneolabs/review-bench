# review-bench

An open benchmark for AI code-review engines, run on real pull requests from
real repositories — with the corpus, prompts, raw engine outputs, and grading
rubric published alongside the scores, not hidden behind them.

Published by [Hyperneo Labs](https://hyperneolabs.github.io). The product is
closed-source; the evidence is not. You cannot read our engine pipeline, so
every quality claim we make has to be checkable from what lives here.

## Why this exists

The AI code-review market currently runs on dueling benchmarks: in September
2026, three vendors each claimed the #1 F1 spot on the *same* third-party
benchmark run, under different configurations of their products. Public
numbers are abundant; public *methods* are not — corpus construction, prompt
configuration, and grading decisions mostly stay inside each vendor, which
makes the numbers unverifiable and the comparison unrepeatable.

This benchmark publishes the whole chain:

- **Corpus** — which PRs are in the set, how they were selected, and the
  ground truth for every case (upstream repo, PR, and both commit SHAs).
- **Arms** — every engine/model/prompt/configuration combination run, dated.
  Third-party tools, when included, run as installed products with their plan
  tier and settings disclosed.
- **Raw outputs** — the unedited structured report each arm produced for each
  case, plus the telemetry each engine actually reports.
- **Grades** — per-finding grades with the rubric text, grader protocol, and
  the disagreements between graders.

## What is measured

| Question | Metric |
|---|---|
| Does the engine catch the bug? | Catch rate on known-bug cases (a finding that overlaps the later fix **and** describes the defect) |
| Does it invent problems? | False-positive findings per clean control case |
| Are the findings real? | Per-finding grades: real-and-actionable / real-but-trivial / wrong / unanchorable |
| What does it cost? | Cost per case where the engine reports it authoritatively; tokens otherwise — never a derived dollar figure without provenance |
| How fast is it? | Latency P50/P95 per arm |
| Do engines agree? | Cross-engine agreement and disagreement rates per case (which engine catches what) |

See [METHODOLOGY.md](METHODOLOGY.md) for the full protocol, including what
this benchmark deliberately does **not** claim.

## Status: corpus v0.1 frozen; first arms pending

The methodology draft and schemas are published, and corpus v0.1 is frozen
at the tag `corpus/v0.1` with its manifest
([`cases/corpus-v0.1.json`](cases/corpus-v0.1.json)): 17 bug cases + 10
control cases across axios, express, httpx, and serde_json (batch 1) and
chi, grpc-go, cobra, urfave/cli, and testify (batch 2, the Go pass) — real
merged upstream PRs with pinned SHAs, mined under the written sampling rule.
The manifest binds every case file by SHA-256 digest, and CI fails on any
edit to a frozen case — corrections require a new corpus version
([METHODOLOGY.md §2.3](METHODOLOGY.md#23-versioning-and-freezing)). Until a
`results/` entry exists for a corpus version, nothing here ranks anything.
This section will be updated — never quietly deleted — as drops land.

- [x] Methodology v0.1 (draft for public comment)
- [x] Case / run / report schemas
- [x] Corpus v0.1 — frozen 2026-09-25 at `corpus/v0.1` (manifest with
      digests; 17 bug + 10 control cases across axios, express, httpx,
      serde_json, chi, grpc-go, cobra, urfave/cli, testify; nominations for
      a future version welcome)
- [ ] First multi-engine results on corpus v0.1
- [ ] Third-party tool arms

## Repository layout

```
METHODOLOGY.md   benchmark protocol (corpus, arms, grading, disclosures)
schema/          JSON schemas: case manifests, arm run records, report envelopes
cases/           the corpus, one directory per case (v0.1 frozen: sampling rule + manifest + 27 cases)
results/         per-arm outputs and aggregate tables (empty until first drop)
tools/           case validation + corpus build/freeze scripts
CHANGELOG.md     versioned changes to methodology, corpus, and results
```

## Contributing

Case nominations are welcome: a bug case is a merged upstream PR that fixed a
real defect in a permissively licensed repository, with the introducing change
identifiable. Open an issue with the upstream PR link and the suspected
introducing commit. Cases are only admitted through the inclusion criteria in
[METHODOLOGY.md §2](METHODOLOGY.md#2-corpus-construction) — nominated cases
that are excluded get a recorded reason, not a silent close.

## License

The corpus, methodology, schemas, and results in this repository are licensed
[CC BY 4.0](LICENSE). Upstream code redistributed inside cases retains its
original license, recorded per case in `case.json`.
