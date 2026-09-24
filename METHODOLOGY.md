# Benchmark methodology (v0.1, draft)

**Version:** 0.1 — 2026-09-24. This is a draft for public comment; it
describes how cases are built, how arms are run, and how findings are graded.
It will change before the first data drop, and every change is recorded in
[CHANGELOG.md](CHANGELOG.md).

**Goal:** measure what AI code-review engines actually do on real pull
requests — what they catch, what they invent, what they cost, and where they
disagree — in a way a third party could re-run and re-grade from the
published artifacts.

## 1. Principles

1. **Publish the method, not just the score.** Every aggregate in `results/`
   links to the raw per-case outputs it was computed from. An aggregate that
   cannot be recomputed from published raw data does not get published.
2. **Negative results are results.** Engine failures, timeouts, empty
   outputs, and refusals are recorded as first-class outcomes, never dropped
   from the denominator.
3. **Provenance over precision.** A number is published with its provenance
   or not at all. Where an engine does not report cost authoritatively, we
   publish its token counts and say so — we do not publish a derived dollar
   figure dressed up as a measurement.
4. **Point-in-time honesty.** Models and products change. Every arm records
   engine, model, configuration, and run date; results are tagged to the
   corpus version they ran against and are not silently refreshed.
5. **The benchmark does not sell.** Rankings here feed product marketing on
   the landing page, which links back here. If the data and the marketing
   ever disagree, the fix is to the marketing.

## 2. Corpus construction

### 2.1 Bug cases

A bug case is a **real defect that a real project actually fixed**, packaged
as the review task the engine would have seen before the fix landed.

Construction, per case:

1. Start from a merged upstream PR whose diff fixes a defect (satisfies at
   least one of: adds a regression test that fails on the parent commit;
   references a linked bug report; the fix commit message names the defect).
2. Identify the change that introduced or last touched the defective code
   (the *introducing change*). The review target is reconstructed from that
   introducing change: the engine reviews **the diff that contained the
   bug**, at the state the project was in when that diff was proposed.
3. Ground truth is recorded from the fix: the files and line ranges the fix
   touched, and a one-paragraph defect description in the fix's own terms
   (issue text or commit message, quoted with provenance).
4. Everything is pinned by SHA: repository, introducing PR, parent commit,
   fix commit. A case that cannot be reconstructed deterministically from
   public SHAs is excluded.

Inclusion criteria:

- Upstream repository under MIT / Apache-2.0 / BSD / ISC license (so the
  case diffs can be redistributed here with attribution).
- Repository has real maintenance activity (not tutorial/throwaway repos).
- The introducing diff is reviewable in one pass (≤ ~600 changed lines;
  larger diffs excluded — no production reviewer reads those either, and the
  failure would measure truncation, not review quality).
- The defect is in code or behavior, not purely in docs/typos/comments.

Exclusion criteria (recorded per excluded candidate, in the nomination
issue):

- The introducing diff *is* the fix's own revert of a same-day regression
  (trivially discoverable).
- The defect requires unavailable runtime context (hardware, credentials,
  private services) to reason about at all.
- Ground truth is ambiguous — the fix touches many concerns at once and the
  defect cannot be isolated.

### 2.2 Control cases (false-positive pressure)

Catch rate alone rewards engines that flag everything. Each corpus version
therefore also contains **clean controls**: merged PRs from the same
repositories and time window that added features, refactors, or docs without
fixing any defect (verified by the same criteria as §2.1, in reverse — no
regression test, no bug reference, no defect-naming message). The false-
positive metric is graded findings per control case, using the same finding
grades as bug cases.

### 2.3 Versioning and freezing

Corpus versions are frozen at tag (`corpus/v0.1`, …). Bug and control cases
are developed against a written sampling rule before any arm runs on the
final set; the frozen manifest is committed before results are collected.
Corrections after freezing require a new corpus version and a CHANGELOG
entry — cases are never edited under a released tag.

## 3. Arms

An **arm** is one (reviewer, model, configuration, prompt) tuple, recorded
in full:

| Field | Content |
|---|---|
| `arm_id` | Stable identifier used in results |
| `reviewer` | Engine (e.g. `claude`, `codex`, `pi`, `makai`, `deepseek` — self-hosted via our pipeline) or third-party product name |
| `model` | Exact model identifier and provider endpoint, where applicable |
| `prompt_hash` + prompt text | The full prompt is published per corpus version; hash binds runs to it |
| `config` | Every tunable the reviewer exposes that we set (verbosity, diff context, tool access) |
| `run_window` | Start/end dates |

Two arm classes:

- **Self-hosted engine arms** run through the same harness code path used in
  production review: repository checkout at the parent commit, the diff under
  review, repository context, and the structured output contract defined in
  [`schema/finding-envelope.schema.json`](schema/finding-envelope.schema.json).
  The prompt and configuration for each arm are published in full with the
  results.
- **Third-party product arms** (when included) run as the installed product,
  on a throwaway organization with a fresh install, on the same frozen
  corpus. Plan tier, configuration UI state, and version are disclosed.
  Third-party arms are identified by their product name and are their
  vendor's behavior on that date — nothing more.

Retries: an arm run that fails for infrastructure reasons (harness crash,
network) is re-run and the failure is recorded; an engine's own refusal,
timeout, or error output is a **result**, not an infrastructure failure, and
is graded as a miss with the outcome recorded.

## 4. Task shape

The engine receives the review task a production reviewer would receive: the
PR diff under review, the repository at the parent state for context, and
the instruction set (published per arm). It returns findings anchored to
files and lines. Anchors that do not exist in the reviewed revision are
recorded as `unanchorable` — a distinct grade, because a finding a reviewer
cannot act on is not a finding.

## 5. Grading

### 5.1 Match rule (bug cases)

A finding **catches** the bug when both hold:

1. **Location:** its anchor (file, line ±3 lines of hunk context) intersects
   the ground-truth lines the later fix touched; and
2. **Description:** it describes the defect class the fix addressed — not
   merely a generic complaint about the touched lines.

Findings satisfying (1) but not (2) are counted separately as
`location-hit/description-miss`. This separation is deliberate: an engine
that flags every changed line "consider error handling" hits every location
and catches nothing.

### 5.2 Finding grades

Every published finding (on bug and control cases alike) receives exactly
one grade:

| Grade | Definition |
|---|---|
| `real-actionable` | Describes a real defect or clear policy violation in the reviewed change, as claimed |
| `real-trivial` | True but inconsequential (style, harmless redundancy) |
| `wrong` | The claimed defect or behavior is not real |
| `unanchorable` | The cited file/line does not exist in the reviewed revision |

### 5.3 Grader protocol

- Graders work from the rubric text above, with the case's ground truth and
  the finding — **blind to the arm** that produced it (arm identity is
  stripped from grading input and restored only for aggregation).
- Every case is graded by two independent graders; disagreements are
  adjudicated by a third, and all three judgments are retained in the
  published grade records.
- Aggregates are computed mechanically from published per-finding grades by
  the script in `results/tools/` (published with the first drop).

### 5.4 Aggregates

Per arm and per corpus version: catch rate, findings per case, location-hit
rate, false-positive findings per control case, grade mix, latency P50/P95,
tokens per case (where reported), cost per case (only where authoritative —
see §6), and outcome mix on failures/timeouts/refusals. Cross-engine tables
add per-case agreement/disagreement (which arms caught which bugs).

## 6. Cost and telemetry provenance

Engines differ in what they actually report, and this benchmark refuses to
paper over it. The per-arm telemetry disclosure, published with results:

| Engine class | Reports |
|---|---|
| `claude` | Authoritative cost per run, token counts |
| `codex` | Token totals (no authoritative cost; cached-input split not reported) |
| `makai`, `deepseek` | Token totals only |
| `pi` | No usage dimensions reported at time of writing |
| Third-party products | Whatever their UI/API exposes, screenshotted or exported with the date |

Consequences, applied strictly: cost-per-case columns exist only for arms
with authoritative cost; token-count comparisons are labeled as such; "no
usage reported" is recorded as exactly that, never as zero. If we ever
publish a modeled cost for a token-only arm, it is labeled *modeled* with
the pricing table and date used.

## 7. What this benchmark does not claim

1. **No aggregation/consensus arm.** Hyperneo's production posted review is
   currently a single-engine verdict with other engines recorded as
   telemetry; cross-engine aggregation is not a shipped stage. No
   "consensus" or "hyperneo ensemble" arm will appear in results until the
   product genuinely posts aggregated verdicts, at which point the
   methodology version is bumped and the aggregation rule is published in
   full.
2. **No training-data hygiene claim.** These are public repositories; any
   model may have trained on them, before or after the fix. Corpus dates
   are recorded so the reader can reason about it; we cannot certify
   contamination-freedom and will not pretend to.
3. **No vendor endorsement.** Third-party arms are measurements of a
   product on a date under a disclosed configuration. Vendors were not
   consulted and did not approve anything here.
4. **No single-number verdict.** We publish the table, not a trophy. An
   engine "wins" nothing here; it catches some classes and misses others,
   and the per-case data shows which.

## 8. Corrections

Errors in published data are fixed by new tagged versions with a CHANGELOG
entry describing what changed and why. Published results are never silently
rewritten. Suspected errors should be filed as issues; every issue gets a
recorded disposition.
