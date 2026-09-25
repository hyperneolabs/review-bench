#!/usr/bin/env python3
"""Freeze a corpus version: generate the frozen manifest from cases/.

The manifest (cases/corpus-<version>.json) is the freeze artifact required
by METHODOLOGY.md §2.3, committed before any results are collected: every
case_id, kind, and upstream SHA provenance, plus content digests binding the
manifest to the exact bytes of every case file — so an edit to a frozen case
is detectable. tools/validate_cases.py enforces the binding in CI by
regenerating the manifest and byte-comparing (see check_frozen_manifests).

Deterministic: cases sorted by id, files sorted by name, fixed JSON layout.
Re-running against an unchanged tree (with the same --date) reproduces a
byte-identical manifest.

Usage (from the repository root):
  python tools/freeze_corpus.py corpus/v0.1              # write the manifest
  python tools/freeze_corpus.py corpus/v0.1 --check      # verify tree matches

An existing manifest is never silently regenerated — --force is required and
only meaningful before the version is tagged; once `corpus/vX.Y` exists, CI
(tools/check_frozen_tags.py) compares the tree against the tagged manifest,
so regenerating over edited cases fails validation anyway.

Requires: standard library only.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES_DIR = os.path.join(ROOT, "cases")

# Order of keys in rendered case entries and the manifest (readability only;
# Python dicts preserve insertion order and the rendering is canonical).
CASE_KEYS = ["case_id", "kind", "repo", "license", "introducing_pr",
             "review_base_sha", "review_head_sha", "fix_pr", "fix_sha",
             "files", "case_digest"]

DIGEST_RECIPE = (
    "per file: sha256 of the file bytes; per case: sha256 of the UTF-8 "
    "concatenation of '<file-sha256>  <relative-path>' lines over every "
    "regular file in the case directory, recursively including "
    "subdirectories (symlinks are rejected), paths in POSIX form relative "
    "to the case directory, entries sorted bytewise by path (C-locale "
    "codepoint order), each line followed by one newline"
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def case_files(case_dir):
    """Every regular file under a case directory, as sorted relative paths.

    Symlinks (to files or directories) are rejected: a digest that silently
    follows or skips them would not bind the bytes a third party sees.
    """
    rels = []
    for root, dirs, names in os.walk(case_dir):
        for n in dirs:
            if os.path.islink(os.path.join(root, n)):
                sys.exit(f"symlinked directory in case {os.path.basename(case_dir)!r}: "
                         f"{os.path.join(root, n)} — case directories must contain only real files")
        for n in names:
            if os.path.islink(os.path.join(root, n)):
                sys.exit(f"symlinked file in case {os.path.basename(case_dir)!r}: "
                         f"{os.path.join(root, n)} — case directories must contain only real files")
            rels.append(os.path.relpath(os.path.join(root, n), case_dir))
    return sorted(rels, key=lambda p: p.replace(os.sep, "/"))


def digest_case(case_dir):
    """(per-file sha256 map, case digest) per DIGEST_RECIPE."""
    files = {}
    lines = []
    for rel in case_files(case_dir):
        digest = sha256_file(os.path.join(case_dir, rel))
        files[rel.replace(os.sep, "/")] = digest
        lines.append(f"{digest}  {rel.replace(os.sep, '/')}\n")
    return files, hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def collect_case(case_id):
    """(declared corpus_version, manifest entry) for one case directory."""
    case_dir = os.path.join(CASES_DIR, case_id)
    case = json.load(open(os.path.join(case_dir, "case.json"), encoding="utf-8"))
    src, sel = case["source"], case.get("selection", {})
    if not sel.get("criteria_version"):
        sys.exit(f"cannot freeze: case {case_id} lacks selection.criteria_version")
    entry = {k: case[k] for k in ("case_id", "kind")}
    for k in ("repo", "license", "introducing_pr",
              "review_base_sha", "review_head_sha", "fix_pr", "fix_sha"):
        if k in src:
            entry[k] = src[k]
    entry["files"], entry["case_digest"] = digest_case(case_dir)
    entry["criteria_version"] = sel["criteria_version"]
    return case["corpus_version"], entry


def build_manifest(version, frozen_at):
    if not re.fullmatch(r"corpus/v\d+\.\d+", version):
        sys.exit(f"version must look like 'corpus/v0.1', got {version!r}")
    ver = version[len("corpus/"):]
    sampling = os.path.join(CASES_DIR, f"sampling-{ver}.md")
    if not os.path.isfile(sampling):
        sys.exit(f"no sampling rule at cases/sampling-{ver}.md "
                 "(methodology §2.3 requires one before freezing)")

    entries, skipped = [], {}
    for d in sorted(os.listdir(CASES_DIR)):
        if not os.path.isdir(os.path.join(CASES_DIR, d)):
            continue
        declared, entry = collect_case(d)
        if declared == version:
            entries.append(entry)
        else:
            skipped[declared] = skipped.get(declared, 0) + 1
    if not entries:
        sys.exit(f"no case directories under cases/ declare corpus_version {version}")
    if skipped:
        # Not an error: other versions may be mid-mining alongside a frozen
        # one. Printed so a mistyped corpus_version is visible at freeze time.
        print(f"note: {sum(skipped.values())} case(s) declare other corpus "
              "version(s) and are not part of this manifest: "
              + ", ".join(f"{v} x{n}" for v, n in sorted(skipped.items())))

    criteria = {e.pop("criteria_version") for e in entries}
    if len(criteria) > 1:
        sys.exit("cases were admitted under differing methodology versions: "
                 + "; ".join(sorted(criteria)))

    return {
        "schema_version": "0.1",
        "corpus_version": version,
        "frozen_at": frozen_at,
        "sampling_rule": f"cases/sampling-{ver}.md",
        "sampling_sha256": sha256_file(sampling),
        "methodology_version": criteria.pop(),
        "case_counts": {
            "bug": sum(1 for e in entries if e["kind"] == "bug"),
            "control": sum(1 for e in entries if e["kind"] == "control"),
        },
        "digest_recipe": DIGEST_RECIPE,
        "cases": [{k: e[k] for k in CASE_KEYS if k in e} for e in entries],
    }


def render_manifest(manifest):
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version", help="corpus version to freeze, e.g. corpus/v0.1")
    ap.add_argument("--date", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
                    help="freeze date (YYYY-MM-DD, UTC); defaults to today")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed manifest matches the tree instead of writing")
    ap.add_argument("--force", action="store_true",
                    help="allow overwriting an existing manifest (only meaningful "
                         "before the version is tagged; CI compares against the tag)")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        sys.exit(f"--date must be YYYY-MM-DD, got {args.date!r}")
    if not args.version.startswith("corpus/"):
        sys.exit(f"version must look like 'corpus/v0.1', got {args.version!r}")

    path = os.path.join(CASES_DIR, "corpus-%s.json" % args.version[len("corpus/"):])
    if args.check:
        disk = open(path, "rb").read().decode("utf-8")
        meta = json.loads(disk)
        if meta["corpus_version"] != args.version:
            sys.exit(f"{os.path.basename(path)} declares corpus_version "
                     f"{meta['corpus_version']!r} — filename and content disagree")
        regen = render_manifest(build_manifest(meta["corpus_version"], meta["frozen_at"]))
        if disk != regen:
            sys.exit(f"{os.path.basename(path)} does not match the case tree — "
                     "a frozen case was edited or the manifest was hand-modified. "
                     "Corrections require a NEW corpus version (METHODOLOGY.md §2.3).")
        print(f"ok   {os.path.basename(path)}: "
              f"{len(meta['cases'])} cases match the tree")
        return

    if os.path.exists(path) and not args.force:
        sys.exit(f"{os.path.relpath(path, ROOT)} already exists — a frozen "
                 "manifest is not regenerated over the cases it froze; "
                 "corrections require a NEW corpus version (METHODOLOGY.md §2.3). "
                 "Pass --force only if this version has not been tagged yet.")
    manifest = build_manifest(args.version, args.date)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(render_manifest(manifest))
    counts = manifest["case_counts"]
    print(f"wrote {os.path.relpath(path, ROOT)}: {len(manifest['cases'])} cases "
          f"({counts['bug']} bug, {counts['control']} control), frozen {args.date}")


if __name__ == "__main__":
    main()
