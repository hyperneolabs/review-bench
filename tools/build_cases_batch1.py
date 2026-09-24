#!/usr/bin/env python3
# Batch-1 corpus build: generates cases/ content from pinned upstream SHAs.
# See cases/sampling-v0.1.md §3 for the rule this implements. Requires local
# clones of the upstream repositories under $RB_MINE (default /tmp/rb-mine).
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
NOMINATION = "https://github.com/hyperneolabs/review-bench/issues/1"
CRITERIA = "METHODOLOGY.md v0.1 (2026-09-24)"

BUG = [
  dict(case_id="axios-socket-listener-request-leak", repo_dir="axios", repo="axios/axios", license="MIT",
       lang=["JavaScript"], int_pr=10788, fix_pr=11091,
       review_head="4709a48fa2717ba97f43f5432d48ca4e26c2d326",
       fix_sha="e8147e6ae25a74793e48b4e00e2f98bc303f5b29",
       intro_commits=["4709a48fa2717ba97f43f5432d48ca4e26c2d326"],
       description="The http adapter installs a once-per-socket 'error' listener whose closure retains the request context that was installing it; on pooled keep-alive sockets that get reassigned, the retained context leaks (memory leak).",
       provenance="fix PR #11091 title and summary (commit e8147e6)", bug_report=None),
  dict(case_id="axios-nullish-interceptor-handlers", repo_dir="axios", repo="axios/axios", license="MIT",
       lang=["JavaScript"], int_pr=11087, fix_pr=11118,
       review_head="712e02373f1c5ac72fdf5da16f04838338ba817e",
       fix_sha="2d2a21af8a433089474a2149781799c93acbcf3c",
       intro_commits=["712e02373f1c5ac72fdf5da16f04838338ba817e"],
       description="syncHandlerEntries() reads handlers.length before checking that handlers exists, so a falsy/ejected-to-nullish handlers value crashes interceptor synchronization.",
       provenance="fix PR #11118 body (commit 2d2a21a); fixes issue #11114",
       bug_report="https://github.com/axios/axios/issues/11114"),
  dict(case_id="axios-nonstring-error-stack", repo_dir="axios", repo="axios/axios", license="MIT",
       lang=["JavaScript"], int_pr=10660, fix_pr=11109,
       review_head="363185461b90b1b78845dc8a99a1f103d9b122a1",
       fix_sha="a75bf44647e5132e39b778730394b0a2b983265c",
       intro_commits=["363185461b90b1b78845dc8a99a1f103d9b122a1"],
       description="The stack-decoration block in Axios.prototype.request's catch handler guards dummy.stack only for truthiness; a non-string stack (e.g. from a patched global Error captureStackTrace) crashes the decoration with a type error.",
       provenance="fix PR #11109 body (commit a75bf44); fixes issue #11108",
       bug_report="https://github.com/axios/axios/issues/11108"),
  dict(case_id="axios-noproxy-wildcard-entry", repo_dir="axios", repo="axios/axios", license="MIT",
       lang=["JavaScript"], int_pr=10661, fix_pr=11053,
       review_head="fb3befb6daac6cad26b2e54094d0f2d9e47f24df",
       fix_sha="ff60b43277c32a5b2f7589c917db16d8e043c0d4",
       intro_commits=["fb3befb6daac6cad26b2e54094d0f2d9e47f24df"],
       description="NO_PROXY wildcard handling treats '*' as a bypass-all only when the entire variable is exactly '*'; a '*' entry inside a comma- or space-separated list is not honored.",
       provenance="fix PR #11053 summary (commit ff60b43)", bug_report=None),
  dict(case_id="json-be-skip-to-escape", repo_dir="json", repo="serde-rs/json", license="Apache-2.0",
       lang=["Rust"], int_pr=1161, fix_pr=1173,
       review_head="859ead8e6d60f4eaed97f7ac2b18f879bec5afe5",
       fix_sha="8b314a77bf57ad8d6089536fea1b3c3b303cba92",
       intro_commits=None,  # filled below: all commits of PR #1161
       description="The SWAR control-character scan in SliceRead::skip_to_escape loads chunks with from_ne_bytes and computes the first matching byte offset with an endianness-conditional leading/trailing_zeros branch, yielding the wrong byte offset on big-endian architectures.",
       provenance="fix PR #1173 (merge 8b314a7, commit 8eba786 'Fix skip_to_escape on BE architectures')",
       bug_report=None),
  # httpx verify=False/cert= case EXCLUDED after review: at the introducing
  # revision (PR #3394) create_ssl_context takes no cert parameter (that PR
  # removes it); the defect only became live when #3419 re-added cert and the
  # load_cert_chain tail. Split-origin defect -> sampling rule section 2.4.
  dict(case_id="express-etag-transfer-encoding", repo_dir="express", repo="expressjs/express", license="MIT",
       lang=["JavaScript"], int_pr=4893, fix_pr=7459,
       review_head="18e5985b8a9d5e8423db0a9121f22bdaecd5b120",
       fix_sha="9a34acf03cb818ff3f8bc40e44176e277a25cbb9",
       intro_commits=["18e5985b8a9d5e8423db0a9121f22bdaecd5b120"],
       description="Gating the whole length-computation block on !Transfer-Encoding also skips the ETag generation path, so res.send with a pre-set Transfer-Encoding header loses its automatic ETag.",
       provenance="fix PR #7459 body (commit 9a34acf0), which names introducing commit 18e5985b",
       bug_report=None),
]

CONTROL = [
  dict(case_id="express-conditional-revalidation-query", repo_dir="express", repo="expressjs/express",
       license="MIT", lang=["JavaScript"], int_pr=7366,
       review_head="ae6dd376", note="feature: conditional revalidation for QUERY requests"),
  dict(case_id="axios-httpstatus-rfc9110-aliases", repo_dir="axios", repo="axios/axios",
       license="MIT", lang=["JavaScript"], int_pr=11082,
       review_head="39955a6", note="feature: RFC 9110 aliases for 413/422 status codes"),
  dict(case_id="axios-typed-params-property", repo_dir="axios", repo="axios/axios",
       license="MIT", lang=["TypeScript"], int_pr=11081,
       review_head="3077e62", note="feature: typed Params property"),
  dict(case_id="json-hashmap-128bit-keys", repo_dir="json", repo="serde-rs/json",
       license="Apache-2.0", lang=["Rust"], int_pr=1188,
       review_head="599228d", note="feature: 128-bit HashMap key serialization"),
  dict(case_id="httpx-python313-support", repo_dir="httpx", repo="encode/httpx",
       license="BSD-3-Clause", lang=["Python"], int_pr=3460,
       review_head="c7c13f1", note="feature: Python 3.13 support (CI matrix + classifier)"),
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
    # fill introducing-commit set for the serde merge-PR case
    for c in BUG:
        if c["intro_commits"] is None:
            revs = git(c["repo_dir"], "log", "--format=%H",
                       f'{c["review_head"]}^1..{c["review_head"]}^2').split()
            c["intro_commits"] = revs
            print(f'{c["case_id"]}: {len(revs)} introducing commits in PR')

    report = {}
    for c in BUG + CONTROL:
        rd, cid = c["repo_dir"], c["case_id"]
        head = c["review_head"]
        head = git(rd, "rev-parse", head).strip() if len(head) < 40 else head
        base = git(rd, "rev-parse", head + "^").strip()
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
    json.dump(report, open(os.path.join(MINE, "build-report.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
