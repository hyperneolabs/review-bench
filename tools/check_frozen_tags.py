#!/usr/bin/env python3
"""Tag-anchored freeze check: compare the current tree against every frozen
corpus tag.

tools/validate_cases.py only proves the committed manifest matches the tree
as it stands — deleting the manifest, or regenerating it over edited cases,
would both pass it. The tag is the actual freeze (METHODOLOGY.md §2.3), so
this check compares the current tree against the manifest recorded AT each
`corpus/vX.Y` tag:

  - the tag's manifest must still exist in the tree (no silent un-freeze);
  - the frozen version's case set is unchanged (no removals, no additions);
  - every per-file SHA-256 digest matches (no edits to frozen cases, no
    files added to or removed from a frozen case);
  - the sampling rule of record is byte-identical to the tagged copy.

CI runs this on every push and PR (actions/checkout with fetch-depth: 0 so
tags are present). Outside a git checkout it exits 0 with a note — the
filesystem-only validate_cases.py remains the local quick check.

Usage: python3 tools/check_frozen_tags.py   (from the repository root)

Requires: git, standard library.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freeze_corpus  # noqa: E402  (same directory; shares digest logic)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    return r.returncode, r.stdout


def main():
    code, _ = git("rev-parse", "--is-inside-work-tree")
    if code != 0:
        print("not a git checkout — tag-anchored freeze check skipped "
              "(run tools/validate_cases.py for the filesystem check)")
        return 0
    code, out = git("tag", "--list", "corpus/v*")
    tags = [t for t in out.decode().split() if t]
    if not tags:
        print("no corpus tags present (nothing frozen yet)")
        return 0

    # Current-tree entries per declared corpus version, via the freeze tool
    # so the digest recipe cannot drift between tools.
    head_entries = {}
    cases_dir = os.path.join(ROOT, "cases")
    for d in sorted(os.listdir(cases_dir)):
        if not os.path.isdir(os.path.join(cases_dir, d)):
            continue
        try:
            declared, entry = freeze_corpus.collect_case(d)
        except SystemExit as e:
            print(f"FAIL case directory {d!r}: {e}")
            return 1
        except Exception as e:
            print(f"FAIL case directory {d!r}: unreadable ({e!r})")
            return 1
        head_entries.setdefault(declared, {})[d] = entry

    failures = 0
    for tag in tags:
        ver = tag[len("corpus/"):]
        mpath = f"cases/corpus-{ver}.json"
        version = f"corpus/{ver}"
        code, out = git("show", f"{tag}:{mpath}")
        if code != 0:
            print(f"FAIL {tag}: no manifest at {mpath} in the tag itself")
            failures += 1
            continue
        try:
            tagged = json.loads(out)
        except json.JSONDecodeError as e:
            print(f"FAIL {tag}: manifest at the tag is malformed ({e})")
            failures += 1
            continue

        tag_failures = 0
        if not os.path.isfile(os.path.join(ROOT, mpath)):
            print(f"FAIL {tag}: manifest {mpath} removed from the current tree — "
                  "a frozen version cannot be un-frozen; corrections require a "
                  "NEW corpus version (METHODOLOGY.md §2.3)")
            tag_failures += 1

        tagged_ids = {e["case_id"]: e for e in tagged["cases"]}
        head = head_entries.get(version, {})
        for cid, te in sorted(tagged_ids.items()):
            he = head.get(cid)
            if he is None:
                print(f"FAIL {tag}: case {cid} (frozen in the tag) is gone "
                      "from the current tree")
                tag_failures += 1
                continue
            if he["kind"] != te["kind"]:
                print(f"FAIL {tag}: case {cid} kind {te['kind']} -> {he['kind']}")
                tag_failures += 1
            for f, digest in sorted(te["files"].items()):
                if he["files"].get(f) != digest:
                    print(f"FAIL {tag}: cases/{cid}/{f} differs from the "
                          "tagged manifest")
                    tag_failures += 1
            for f in sorted(he["files"]):
                if f not in te["files"]:
                    print(f"FAIL {tag}: cases/{cid}/{f} added to a frozen case")
                    tag_failures += 1
        for cid in sorted(head):
            if cid not in tagged_ids:
                print(f"FAIL {tag}: case {cid} declares {version} but is not "
                      "in the tagged manifest — a frozen version cannot grow")
                tag_failures += 1

        rule = tagged.get("sampling_rule")
        if rule:
            hpath = os.path.join(ROOT, rule)
            hd = freeze_corpus.sha256_file(hpath) if os.path.isfile(hpath) else None
            td = tagged.get("sampling_sha256")
            if td is None:  # manifest predates the field: compare to the tag's copy
                code, tout = git("show", f"{tag}:{rule}")
                td = hashlib.sha256(tout).hexdigest() if code == 0 else None
            if hd != td:
                print(f"FAIL {tag}: sampling rule {rule} differs from the tagged copy")
                tag_failures += 1

        if not tag_failures:
            print(f"ok   {tag}: {len(tagged['cases'])} cases + sampling rule "
                  "match the tagged manifest")
        failures += tag_failures

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
