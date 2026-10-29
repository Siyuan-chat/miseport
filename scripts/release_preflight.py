"""Pre-tag check for tracked files that would leak into GitHub's auto source ZIP.

Run before creating a public tag: python scripts/release_preflight.py
This is intentionally NOT part of ordinary branch CI: internal notes remain
tracked in the development branch until explicit pre-release cleanup.
"""
from pathlib import Path
import json
import subprocess

from audit_release import INTERNAL_FILES, INTERNAL_PREFIXES


OLD_ASSETS = {
    "assets/brand-v01-review.png",
    "assets/geometry-v01.json",
    "assets/social-cover.png",
    "assets/favicon.ico",
    "assets/favicon.png",
    "assets/favicon.svg",
    "assets/logo-light.svg",
    "assets/logo-dark.svg",
    "assets/logo-light.png",
    "assets/logo-dark.png",
    "assets/logo-light-small.png",
    "assets/logo-dark-small.png",
}
OLD_PREFIXES = ("references/",)


def release_blockers(tracked: list[str]) -> list[str]:
    return sorted(name for name in tracked
                  if name in INTERNAL_FILES or name in OLD_ASSETS
                  or any(name.startswith(prefix) for prefix in
                         (*INTERNAL_PREFIXES, *OLD_PREFIXES)))


def main():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    paths = [s.decode("utf-8") for s in result.stdout.split(b"\x00") if s]
    blockers = release_blockers(paths)
    report = {
        "status": "blocked" if blockers else "ready_to_review",
        "tracked_files": len(paths),
        "internal_or_superseded_files": blockers,
        "note": ("A release tag's automatic source archives include ALL tracked files. "
                 "Already public Git history cannot be erased by a new commit."),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if blockers:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
