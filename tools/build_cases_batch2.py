#!/usr/bin/env python3
# Batch-2 corpus build (Go pass): generates cases/ content from pinned upstream
# SHAs. Same rule as batch 1 (cases/sampling-v0.1.md §3) over the batch-2
# candidate set — dispositions in the batch-2 nomination issue (#3). Requires
# local clones of the upstream repositories under $RB_MINE (default /tmp/rb-mine).
"""Build review-bench corpus cases from pinned upstream SHAs.

For each case config:
  - review.diff = git diff <review_base> <review_head>   (the change under review)
  - fix.diff    = git diff <fix_parent> <fix>            (bug cases only)
  - ground truth: pre-image lines of the fix's hunks whose blame at <fix_parent>
    attributes to an introducing commit, mapped back to <review_head> line
    coordinates via git diff -U0 hunk arithmetic, with content verification.
"""
import json, os, re, subprocess, sys

MINE = os.environ.get("RB_MINE", "/tmp/rb-mine")
BENCH = os.environ.get("RB_BENCH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOMINATION = "https://github.com/hyperneolabs/review-bench/issues/3"
CRITERIA = "METHODOLOGY.md v0.1 (2026-09-24)"

BUG = [
  dict(case_id="chi-routeheaders-missing-return", repo_dir="chi", repo="go-chi/chi", license="MIT",
       lang=["Go"], int_pr=503, fix_pr=1045,
       review_head="23b8ec2ca33d",
       fix_sha="05f1ef7bb50b",
       intro_commits=["23b8ec2ca33d"],
       description="HeaderRouter.Handler's empty-routes branch calls next.ServeHTTP(w, r) without returning, so when no header routes are configured the middleware falls through and invokes the handler chain a second time at the end of Handler — the request is served twice.",
       provenance="fix PR #1045 body (commit 05f1ef7): 'next handler to be called twice - once in the empty check and again at the end of the function'",
       bug_report=None),
  dict(case_id="chi-recoverer-negative-index", repo_dir="chi", repo="go-chi/chi", license="MIT",
       lang=["Go"], int_pr=496, fix_pr=633,
       review_head="98de1d836ac7",
       fix_sha="188a1675b707",
       intro_commits=["98de1d836ac7"],
       description="prettyStack.decorateFuncCallLine slices pkg/method with strings.Index results and no -1 guard; a stack line without a '.' separator (Go 1.17+ frames can be bare, e.g. 'panic') makes the code slice with a negative index and panic inside the panic-recovery middleware.",
       provenance="fix PR #633 body (commit 188a167): 'lines of the debug stack aren't guaranteed to contain a period ... don't attempt to slice with a negative index'",
       bug_report=None),
  dict(case_id="grpc-dialcontext-goroutine-leak", repo_dir="grpc-go", repo="grpc/grpc-go", license="Apache-2.0",
       lang=["Go"], int_pr=1112, fix_pr=1424,
       review_head="c5a5dbc5005d",
       fix_sha="4e56696c6c5a",
       intro_commits=["c5a5dbc5005d"],
       description="ClientConn.lbWatcher consumes the balancer's Notify channel but never closes doneChan when that channel closes or the loop breaks; when DialContext times out before the balancer returns addresses or a connection is established, the goroutine waiting on doneChan is never released — a goroutine leak.",
       provenance="fix PR #1424 body (commit 4e56696): 'The loop in ClientConn.lbWatcher breaks and doneChan never gets closed'",
       bug_report=None),
  dict(case_id="grpc-parsetarget-unix-scheme", repo_dir="grpc-go", repo="grpc/grpc-go", license="Apache-2.0",
       lang=["Go"], int_pr=1567, fix_pr=1611,
       review_head="3f10311ccf07",
       fix_sha="0d57c57a68d6",
       intro_commits=["3f10311ccf07"],
       description="parseTarget applies the '/' authority/endpoint split even when the target contains no '://' scheme separator, so a scheme-less target such as 'unix:/path/to/socket' is decomposed into Authority 'unix:' and Endpoint 'path/to/socket', handing the resolver a mangled endpoint instead of the original target.",
       provenance="fix PR #1611 (commit 0d57c57): parseTarget returns the target unsplit when no scheme separator is present",
       bug_report=None),
  dict(case_id="grpc-fromproto-nil-receiver", repo_dir="grpc-go", repo="grpc/grpc-go", license="Apache-2.0",
       lang=["Go"], int_pr=1171, fix_pr=1211,
       review_head="1d27587e10ce",
       fix_sha="84cd50a2f394",
       intro_commits=["1d27587e10ce"],
       description="Status.Code, Status.Message, and Status.Proto dereference the receiver or its inner status without nil checks, so a Status with a nil inner proto — which FromProto(nil) returns — panics in s.s dereference as soon as any accessor is called, as does any accessor on a nil *Status.",
       provenance="fix PR #1211 (commit 84cd50a): nil guards added to all three accessors",
       bug_report=None),
  # PR #414 landed as a run of 7 rebased commits (not a squash or a merge
  # commit), so the review task is the landed run's net diff: review_head is
  # the run tip and review_base is the parent of the run's first commit.
  dict(case_id="cobra-shadowed-persistent-flag-help", repo_dir="cobra", repo="spf13/cobra", license="Apache-2.0",
       lang=["Go"], int_pr=414, fix_pr=1776,
       review_head="f58a8d6bd383c1594da70068e4c236136adc5496",
       review_base="a3cd8ab85aeba3522b9b59242f3b86ddbc67f8bd",
       fix_sha="22b617914c88",
       intro_commits=["6202b5942b8f31501d14d8cb192790d8a10302f4",
                      "3d89ed490897e712ee31d77a26be3db03f656e5d",
                      "37a4355faa3871394f60ee207608f1df565cd37f",
                      "458d79748e944cc033fd025058f824a88cba6a45",
                      "3e61377cd57a0aea7cddd366f77800033d5b5295",
                      "e135867f9649c8be875fa562e54db9c27a045c8e",
                      "f58a8d6bd383c1594da70068e4c236136adc5496"],
       description="Command.LocalFlags' addToLocal check drops a child command's own flag whenever any parent persistent flag shares its name (it tests parentsPflags.Lookup(f.Name) != nil), so a child flag that shadows a parent persistent flag disappears from the child's local-flag help and the parent's flag is shown instead.",
       provenance="fix PR #1776 body (commit 22b6179)",
       bug_report=None),
  dict(case_id="cobra-argsminusfirstx-flag-value", repo_dir="cobra", repo="spf13/cobra", license="Apache-2.0",
       lang=["Go"], int_pr=95, fix_pr=1781,
       review_head="36aee64abe8c",
       fix_sha="6b0bd3076cfa",
       intro_commits=["36aee64abe8c"],
       description="argsMinusFirstX removes the first occurrence of x anywhere in args without flag awareness, so when the subcommand's name appears earlier as a flag's value (e.g. 'mycli --name admin subcmd admin') the flag value is stripped and the remaining argument list is misparsed.",
       provenance="fix PR #1781 (commit 6b0bd30): rewrite skips flag values when locating x",
       bug_report=None),
  dict(case_id="cli-exit-empty-stderr-line", repo_dir="cli", repo="urfave/cli", license="MIT",
       lang=["Go"], int_pr=2237, fix_pr=2310,
       review_head="91ed11d72b02",
       fix_sha="6ce476e539dd",
       intro_commits=["91ed11d72b02"],
       description="HandleExitCoder prints the error to ErrWriter unconditionally before calling OsExiter, so an Exit error with an empty message emits a blank line to stderr.",
       provenance="fix PR #2310 body (commit 6ce476e); fixes issue #2263",
       bug_report="https://github.com/urfave/cli/issues/2263"),
  dict(case_id="testify-isnil-unsafepointer", repo_dir="testify", repo="stretchr/testify", license="MIT",
       lang=["Go"], int_pr=707, fix_pr=1319,
       review_head="1ecda4918e78",
       fix_sha="9acc22213e5f",
       intro_commits=["1ecda4918e78"],
       description="isNil's list of nilable reflect.Kinds omits reflect.UnsafePointer, so a nil unsafe.Pointer value is not classified as nil and Nil/NotNil assertions misjudge it.",
       provenance="fix PR #1319 (commit 9acc222)",
       bug_report=None),
  dict(case_id="testify-unset-iterate-panic", repo_dir="testify", repo="stretchr/testify", license="MIT",
       lang=["Go"], int_pr=982, fix_pr=1250,
       review_head="ba1076d8b3b6",
       fix_sha="2b00d33aec28",
       intro_commits=["ba1076d8b3b6"],
       description="Call.Unset() removes matching entries from Parent.ExpectedCalls with an in-place append while iterating by the original range index; once a removal shifts the slice, a later match reslices past the shortened slice's end and panics.",
       provenance="fix PR #1250 body (commit 2b00d33); fixes issue #1236",
       bug_report="https://github.com/stretchr/testify/issues/1236"),
  dict(case_id="testify-eventually-closed-channel-panic", repo_dir="testify", repo="stretchr/testify", license="MIT",
       lang=["Go"], int_pr=724, fix_pr=808,
       review_head="d84e815d441d",
       fix_sha="f1bd0923b832",
       intro_commits=["d84e815d441d"],
       description="Eventually runs the condition in a goroutine that sends on an unbuffered checkPassed channel and defers close(checkPassed) on return; when the timer expires first, the deferred close races the in-flight goroutine's send, and the send on the closed channel panics in the condition goroutine, crashing the test binary.",
       provenance="fix PR #808 (commit f1bd0923): 'Fix panic for Eventually functions'; fixes issues #805 and #835",
       bug_report="https://github.com/stretchr/testify/issues/805"),
]

CONTROL = [
  dict(case_id="chi-replaceall-refactor", repo_dir="chi", repo="go-chi/chi",
       license="MIT", lang=["Go"], int_pr=1046,
       review_head="142fada", note="refactor: strings.ReplaceAll swap"),
  dict(case_id="grpc-codes-unmarshaljson", repo_dir="grpc-go", repo="grpc/grpc-go",
       license="Apache-2.0", lang=["Go"], int_pr=1720,
       review_head="2941ee12", note="feature: UnmarshalJSON support for codes.Code"),
  dict(case_id="cobra-initdefaultcompletioncmd-public", repo_dir="cobra", repo="spf13/cobra",
       license="Apache-2.0", lang=["Go"], int_pr=1467,
       review_head="8607918", note="feature: make InitDefaultCompletionCmd public"),
  dict(case_id="cli-dynamic-fish-completion", repo_dir="cli", repo="urfave/cli",
       license="MIT", lang=["Go"], int_pr=2270,
       review_head="600026fe69d2", note="feature: dynamic fish completion"),
  dict(case_id="testify-struct-public-compare", repo_dir="testify", repo="stretchr/testify",
       license="MIT", lang=["Go"], int_pr=1309,
       review_head="c5fc9d6b6b21", note="feature: compare public elements of structs"),
]

def git(rd, *args):
    r = subprocess.run(["git", "-C", os.path.join(MINE, rd), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr[:400]}")
    return r.stdout

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*$")

def parse_hunks(diff_text):
    """[(old_start, old_len, new_start, new_len)], len 0 as given."""
    out = []
    for line in diff_text.splitlines():
        m = HUNK.match(line)
        if m:
            o, ol, n, nl = m.groups()
            out.append((int(o), int(ol or "1") if (ol is None or ol == "") else int(ol),
                        int(n), int(nl or "1") if (nl is None or nl == "") else int(nl)))
    return out

def files_in_diff(diff_text):
    files, cur = [], None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
            files.append(cur)
    return files

def blame_lines(rd, rev, path, a, b):
    """{lineno: full_sha} for lines a..b of path at rev, via --porcelain."""
    out = git(rd, "blame", "--porcelain", rev, "-L", f"{a},{b}", "--", path)
    res = {}
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]{40}) (\d+) (\d+)( \d+)?$", line)
        if m:
            res[int(m.group(3))] = (m.group(1), None)
    return res

def show_lines(rd, rev, path):
    content = git(rd, "show", f"{rev}:{path}")
    return content.splitlines()

def main():
    # blame reports full 40-hex SHAs; normalize any short intro refs to full
    for c in BUG:
        c["intro_commits"] = [git(c["repo_dir"], "rev-parse", s).strip()
                              if len(s) < 40 else s for s in c["intro_commits"]]

    report = {}
    for c in BUG + CONTROL:
        rd, cid = c["repo_dir"], c["case_id"]
        head = c["review_head"]
        head = git(rd, "rev-parse", head).strip() if len(head) < 40 else head
        # default review base is the introducer's parent; multi-commit landed
        # runs (rebase landings) pin the run's first commit's parent instead
        base_ref = c["review_base"] if "review_base" in c else head + "^"
        base = git(rd, "rev-parse", base_ref).strip()
        outdir = os.path.join(BENCH, "cases", cid)
        os.makedirs(outdir, exist_ok=True)

        review_diff = git(rd, "diff", base, head)
        open(os.path.join(outdir, "review.diff"), "w").write(review_diff)
        chg = sum(1 for l in review_diff.splitlines()
                  if (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---")))
        case = {
            "schema_version": "0.1", "case_id": cid,
            "kind": "bug" if c in BUG else "control",
            "corpus_version": "corpus/v0.1",
            "source": {"repo": c["repo"], "license": c["license"], "introducing_pr": c["int_pr"],
                        "review_base_sha": base, "review_head_sha": head},
            "language": c["lang"],
            "files": {"review_diff": "review.diff"},
            "selection": {"nominated_in": NOMINATION, "included_at": "2026-09-24",
                           "criteria_version": CRITERIA},
        }
        if c in BUG:
            fix = c["fix_sha"]
            fix = git(rd, "rev-parse", fix).strip() if len(fix) < 40 else fix
            fixp = git(rd, "rev-parse", fix + "^").strip()
            fix_diff = git(rd, "diff", fixp, fix)
            open(os.path.join(outdir, "fix.diff"), "w").write(fix_diff)
            case["source"]["fix_pr"] = c["fix_pr"]
            case["source"]["fix_sha"] = fix
            case["files"]["fix_diff"] = "fix.diff"

            gt, problems = [], []
            def is_test_path(p):
                p = p.lower()
                return (p.startswith(("tests/", "test/")) or "/tests/" in p or "/test/" in p
                        or p.endswith(("_test.go", ".test.js", ".test.ts", "_test.py", "_test.rs",
                                      ".browser.test.js", "test.rs", "test.py")))
            for path in files_in_diff(fix_diff):
                if is_test_path(path):
                    continue
                file_diff = git(rd, "diff", "-U0", fixp, fix, "--", path)
                hunks = parse_hunks(file_diff)
                # pre-image ranges of changed hunks; pure insertions (ol == 0)
                # anchor on the line the fix inserted after (old_start)
                pre_ranges = [(o, o + ol - 1) for (o, ol, n, nl) in hunks if ol > 0] + \
                             [(o, o) for (o, ol, n, nl) in hunks if ol == 0 and o >= 1]
                if not pre_ranges:
                    continue
                lo = min(a for a, b in pre_ranges); hi = max(b for a, b in pre_ranges)
                bl = blame_lines(rd, fixp, path, lo, hi)
                intro = set(c["intro_commits"])
                defect = {ln for ln in range(lo, hi + 1)
                          if any(a <= ln <= b for a, b in pre_ranges)
                          and ln in bl and bl[ln][0] in intro}
                if not defect:
                    continue
                # map fixp -> head coordinates
                drift = parse_hunks(git(rd, "diff", "-U0", head, fixp, "--", path))
                head_lines = show_lines(rd, head, path)
                fixp_lines = show_lines(rd, fixp, path)
                mapped = []
                for ln in sorted(defect):
                    rh = None
                    for (o, ol, n, nl) in drift:
                        if n <= ln <= n + nl - 1:
                            rh = "CHANGED"; break
                    else:
                        off = sum((nl - ol) for (o, ol, n, nl) in drift if n + nl - 1 < ln)
                        rh = ln - off
                    if rh == "CHANGED":
                        problems.append(f"{path}:{ln} fell inside a drift hunk")
                        continue
                    if rh < 1 or rh > len(head_lines) or fixp_lines[ln - 1] != head_lines[rh - 1]:
                        problems.append(f"{path}:{ln}->{rh} content mismatch")
                        continue
                    mapped.append((ln, rh))
                # contiguous runs, tracked in both coordinate systems
                pairs, cur = [], []
                for fp, rh in mapped:
                    if cur and rh == cur[-1][1] + 1:
                        cur.append((fp, rh))
                    else:
                        if cur:
                            pairs.append(cur)
                        cur = [(fp, rh)]
                if cur:
                    pairs.append(cur)
                for run in pairs:
                    rh_a, rh_b = run[0][1], run[-1][1]
                    fp_a, fp_b = run[0][0], run[-1][0]
                    gt.append({"file": path, "line_start": rh_a, "line_end": rh_b,
                               "note": f"fix hunk attributed to the introducing change (fix-parent lines {fp_a}-{fp_b}, review-head lines {rh_a}-{rh_b})"})
            if not gt:
                raise RuntimeError(f"{cid}: no ground truth extracted; problems={problems}")
            case["defect"] = {"description": c["description"], "provenance": c["provenance"],
                               "ground_truth": gt}
            report[cid] = dict(changed_lines=chg, gt=gt, problems=problems)
        else:
            report[cid] = dict(changed_lines=chg, control=True)

        json.dump(case, open(os.path.join(outdir, "case.json"), "w"), indent=2)
        open(os.path.join(outdir, "case.json"), "a").write("\n")
        print(f"{cid}: review.diff {chg} chg lines"
              + (f", {len(gt)} gt ranges, problems={problems}" if c in BUG else " (control)"))
    json.dump(report, open(os.path.join(MINE, "build-report-batch2.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
