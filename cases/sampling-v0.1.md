# Sampling rule for corpus v0.1

**Applies to:** all corpus/v0.1 case mining (batches 1 onward until the corpus
is frozen at tag `corpus/v0.1`). Judged against [METHODOLOGY.md
v0.1 (2026-09-24)](../METHODOLOGY.md). Per-batch candidate dispositions,
including every exclusion and its criterion, are recorded in the batch's
nomination issue (batch 1: [issue #1](https://github.com/hyperneolabs/review-bench/issues/1),
batch 2: [issue #3](https://github.com/hyperneolabs/review-bench/issues/3)).

This file is the written rule the methodology's §2.3 requires before any arm
runs: how candidates were searched, how the introducing change is identified,
and how ground truth is anchored. It changes only with a CHANGELOG entry.

## 1. Repository selection

Candidate repositories were chosen to satisfy the §2.1 inclusion criteria up
front:

- License MIT / Apache-2.0 / BSD-2-Clause / BSD-3-Clause / ISC (checked via the
  GitHub API license field, recorded per case in `case.json`).
- Real maintenance activity at mining time (pushes within ~6 months), not
  tutorial or throwaway repos.
- Pull-request-based history (the schema pins an `introducing_pr`; repositories
  whose relevant history is direct-push commits cannot yield reconstructible
  cases and are dropped — recorded per repository when this happens).

Batch 1 mined: `axios/axios`, `expressjs/express`, `encode/httpx`,
`serde-rs/json`, plus `gin-gonic/gin`, `redis/go-redis`, `psf/requests`,
`pallets/flask` (the last four yielded only excluded candidates — see the
nomination issue; Go is unrepresented in batch 1 and queued for batch 2).

Batch 2 (the Go pass) mined: `go-chi/chi`, `grpc/grpc-go`, `spf13/cobra`,
`urfave/cli`, `stretchr/testify`, plus `containerd/containerd` (yielded only
excluded candidates — every criteria-passing recent fix traced to an
over-limit introducing PR; see the batch-2 nomination issue
[#3](https://github.com/hyperneolabs/review-bench/issues/3)).

## 2. Bug-case search procedure

1. Enumerate merged commits whose subject matches fix-flavored patterns
   (`fix`, `Fix`, `fix(...)`) in each repository.
2. Keep a fix only if it satisfies at least one §2.1 criterion: adds a
   regression test; references a linked bug report; or the commit message
   itself names the defect.
3. Read the fix diff; the defect lines are the fix's pre-image hunks in
   non-test source files.
4. Identify the introducing change: `git blame` (with move detection `-C -C`
   where the region was relocated) of the fix's pre-image lines at the fix's
   parent, walking to the change that introduced the defective lines. The
   introducing commit must belong to a merged pull request (checked via the
   commits→pulls API). If the defect lines' origin is split across multiple
   changes such that no single introducing diff contains the defect, the
   candidate is excluded as *introducing-change ambiguous*.
5. The introducing pull request's net diff (first-parent range for
   merge-commit PRs, the squash commit for squash merges, and the net diff of
   the landed commit run for PRs landed as a series of rebased commits) is
   the review task. Its changed-line count must be ≤ ~600; the count used is
   +/- lines in the whole PR diff, not just source files.

## 3. Ground-truth anchoring

Ground truth is derived mechanically from the fix, then mapped into the
reviewed revision's coordinates:

1. Take the fix's `-U0` hunks in non-test source files. Pure insertions (no
   pre-image lines) anchor on the line the fix inserted after.
2. Blame those pre-image lines at the fix's parent; keep only lines attributed
   to commits belonging to the introducing pull request.
3. Map each kept line from fix-parent coordinates to review-head coordinates
   by `git diff -U0 <review_head> <fix_parent>` hunk arithmetic (kept lines are
   by construction unchanged between the two). Content equality between the
   two revisions is verified per line; a mismatch aborts the case.
4. Contiguous review-head lines collapse into ranges — the `ground_truth`
   array in `case.json`. Grading's ±3-line location window (§5.1) is applied
   at grading time, not baked into these ranges. Anchor lines can be blank or
   comment lines (a pure insertion anchors on the line it follows); the
   description half of the match rule, not the location half, is what
   discriminates real catches there.

The build is scripted (blame + mapping + content verification); the script
output for batch 1 is archived with the batch's nomination issue. A published
re-derivation tool ships with the first results drop.

## 4. Control-case selection

Controls are merged pull requests from the same repositories mined for that
batch's bug cases, dated within the span those bug cases cover (±3 months),
that added a feature, refactor, or documentation without fixing any
defect. Verified
clean by all of: no regression test for a defect; no bug-report reference; no
defect-naming commit message. The verification basis is recorded per control
in the nomination issue. Controls carry no `defect` block and no `fix.diff`.

## 5. Batch discipline

- One batch = one nomination issue recording every candidate (included and
  excluded, with criterion) — no silent drops.
- Cases land under `cases/<case-id>/` with `case.json`, `review.diff`, and
  (bug cases) `fix.diff`; `tools/validate_cases.py` must pass.
- Freezing: when mining for v0.1 closes, the manifest `corpus-v0.1.json` is
committed and the `corpus/v0.1` tag is cut. Only then do arms run; corrections
after the tag require a new corpus version (§2.3).
