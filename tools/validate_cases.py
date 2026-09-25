#!/usr/bin/env python3
"""Validate every case in cases/ against schema/case.schema.json.

Checks, per case directory containing a case.json:
  - schema conformance (jsonschema, Draft 2020-12)
  - referenced diff files exist and are non-empty
  - bug cases carry fix.diff; controls carry no fix artifacts at all
  - ground-truth files appear in review.diff (the defect must live in the
    change under review)

Frozen-manifest binding: for every cases/corpus-*.json present, the manifest
is regenerated from the current case tree (tools/freeze_corpus.py) and
byte-compared. Any edit to a frozen case, post-freeze addition to a frozen
version, or hand-edit of the manifest itself fails here — corrections
require a NEW corpus version (METHODOLOGY.md §2.3). Cases declaring an
unfrozen later version (mining in progress) do not fail this check.

Usage: python3 tools/validate_cases.py   (from the repository root)

Requires: jsonschema (pip install jsonschema)
"""
import glob
import json
import os
import re
import sys

try:
    import jsonschema
except ImportError:
    sys.exit("jsonschema is required: pip install jsonschema")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freeze_corpus  # noqa: E402  (same directory; shares the digest recipe)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schema", "case.schema.json")


def check_frozen_manifests():
    """Enforce the freeze: every committed manifest must match the tree."""
    failures = 0
    manifests = sorted(glob.glob(os.path.join(ROOT, "cases", "corpus-*.json")))
    if not manifests:
        print("\nno frozen corpus manifest present (corpus not frozen)")
        return failures
    for mpath in manifests:
        base = os.path.basename(mpath)
        try:
            disk = open(mpath, "rb").read().decode("utf-8")
            meta = json.loads(disk)
            version = meta["corpus_version"]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError,
                KeyError, TypeError) as e:
            print(f"FAIL {base}: unreadable or malformed manifest ({e!r})")
            failures += 1
            continue
        expected = "corpus-%s.json" % version[len("corpus/"):]
        if expected != base:
            print(f"FAIL {base}: declares corpus_version {version!r} "
                  f"(filename should be {expected})")
            failures += 1
            continue
        try:
            regen = freeze_corpus.render_manifest(
                freeze_corpus.build_manifest(version, meta["frozen_at"]))
        except SystemExit as e:  # freeze tool refuses (mixed methods, etc.)
            print(f"FAIL {base}: {e}")
            failures += 1
            continue
        except Exception as e:  # unreadable case data during regeneration
            print(f"FAIL {base}: cannot regenerate from the case tree ({e!r})")
            failures += 1
            continue
        if disk != regen:
            print(f"FAIL {base}: does not match the case tree — a frozen case "
                  "was edited, a case was added to a frozen version, or the "
                  "manifest was hand-modified. Corrections require a NEW "
                  "corpus version (METHODOLOGY.md §2.3)")
            failures += 1
        else:
            counts = meta["case_counts"]
            print(f"ok   {base}: {len(meta['cases'])} cases "
                  f"({counts['bug']} bug, {counts['control']} control) "
                  f"match the tree")
    return failures


def main():
    schema = json.load(open(SCHEMA))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    cases_dir = os.path.join(ROOT, "cases")
    case_dirs = sorted(
        d for d in os.listdir(cases_dir)
        if os.path.isdir(os.path.join(cases_dir, d))
    )
    if not case_dirs:
        sys.exit("no case directories found under cases/")

    failures = 0
    kinds = {}
    for d in case_dirs:
        cpath = os.path.join(cases_dir, d, "case.json")
        if not os.path.exists(cpath):
            print(f"FAIL {d}: no case.json")
            failures += 1
            continue
        case = json.load(open(cpath))
        errs = sorted(validator.iter_errors(case), key=str)
        if errs:
            for e in errs:
                print(f"FAIL {d}: schema: {'/'.join(str(p) for p in e.absolute_path)}: {e.message}")
            failures += 1
            continue

        problems = []
        if case["case_id"] != d:
            problems.append(f"directory name {d!r} != case_id {case['case_id']!r}")
        if not re.fullmatch(r"corpus/v\d+\.\d+", case["corpus_version"]):
            problems.append(f"corpus_version {case['corpus_version']!r} is not of "
                            "the form corpus/vX.Y")
        review_diff = os.path.join(cases_dir, d, case["files"]["review_diff"])
        if not os.path.isfile(review_diff) or os.path.getsize(review_diff) == 0:
            problems.append("review.diff missing or empty")
        review_text = open(review_diff, encoding="utf-8", errors="replace").read() \
            if os.path.isfile(review_diff) else ""
        chg = sum(1 for l in review_text.splitlines()
                  if (l.startswith("+") or l.startswith("-"))
                  and not l.startswith(("+++", "---")))
        if chg > 600:
            problems.append(f"review.diff has {chg} changed lines (over the ~600 reviewable limit)")

        if case["kind"] == "bug":
            fix_path = os.path.join(cases_dir, d, case["files"]["fix_diff"])
            if not os.path.isfile(fix_path) or os.path.getsize(fix_path) == 0:
                problems.append("fix.diff missing or empty")
            for gt in case["defect"]["ground_truth"]:
                if not re.search(r"^diff --git a/{0} b/{0}$".format(re.escape(gt["file"])),
                                 review_text, re.M):
                    problems.append(f"ground-truth file {gt['file']} not in review.diff")
                if gt["line_end"] < gt["line_start"]:
                    problems.append(f"ground-truth range {gt['file']}:{gt['line_start']}-{gt['line_end']} inverted")
        else:
            if "fix_diff" in case["files"] or "fix_pr" in case["source"] or "fix_sha" in case["source"]:
                problems.append("control case carries fix artifacts (fix_diff/fix_pr/fix_sha)")
            if "defect" in case:
                problems.append("control case carries a defect block")
            if os.path.exists(os.path.join(cases_dir, d, "fix.diff")):
                problems.append("control case ships a fix.diff file")
        if problems:
            for p in problems:
                print(f"FAIL {d}: {p}")
            failures += 1
        else:
            kinds[case["kind"]] = kinds.get(case["kind"], 0) + 1
            print(f"ok   {d} ({case['kind']}, {chg} chg lines)")

    failures += check_frozen_manifests()
    if failures:
        sys.exit(f"\n{failures} case(s) failed validation")
    print(f"\nall {sum(kinds.values())} cases valid: "
          + ", ".join(f"{v} {k}" for k, v in sorted(kinds.items())))


if __name__ == "__main__":
    main()
