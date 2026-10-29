"""Audit source/wheel/merchant ZIP contents before a public release.

Run explicitly against each artifact. Does not delete Git history or publish.
Current main-branch sdist is expected to fail until internal files are removed.
"""
import argparse
import json
from pathlib import PurePosixPath, Path
import re
import tarfile
import zipfile


INTERNAL_PREFIXES = (
    "references/legacy-20261027/",
    "docs/evidence/",
)
INTERNAL_FILES = {
    "PROJECT_STATUS.md",
    "docs/DEVELOPMENT_PLAN.zh-CN.md",
    "docs/DEVELOPMENT_PLAN.ja.md",
    "docs/RELEASE_2026-11-10.ja.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/RELEASE_PUBLICATION_POLICY.ja.md",
    "docs/merchant/PILOT_2026-11-10.ja.md",
    "docs/merchant/VIDEO_DEMO_PLAN.ja.md",
    "docs/GITHUB_TESTING.md",
    "docs/VALIDATION.md",
    "docs/LEGACY_BASELINE.md",
    "docs/DEPLOYMENT.md",
    "docs/SEO_GEO.md",
    "docs/BRAND_VECTOR.md",
    "references/README.md",
}
SENSITIVE = re.compile(
    rb"gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|"
    rb"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----|"
    rb"(?i:access[_-]?token|client[_-]?secret|api[_-]?key)\s*[:=]\s*[^\s]{16,}"
)
DANGEROUS_FILE = re.compile(r"(?:^|/)(?:\.env(?!\.example$)|id_rsa|id_ed25519|credentials\.json)(?:$|/)|\.(?:pem|pfx|key)$")


def _normal_path(value: str) -> str:
    if "\\" in value or value.startswith("/") or ".." in PurePosixPath(value).parts:
        raise ValueError("unsafe archive path")
    segments = PurePosixPath(value).parts
    if len(segments) > 1 and (segments[0].startswith("miseport-") or segments[0] == "miseport"):
        return "/".join(segments[1:])
    return value


def inspect_archive(path: str | Path) -> dict:
    """Return only file names and issue codes, never secret content."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            entries = [(info.filename, archive.read(info.filename))
                       for info in archive.infolist() if not info.is_dir()]
    elif tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            entries = [(info.name, archive.extractfile(info).read())
                       for info in archive.getmembers() if info.isfile()]
    else:
        raise ValueError("supported archive types: ZIP / tar.gz")
    issues = []
    seen = set()
    for full, data in entries:
        try:
            name = _normal_path(full)
        except ValueError:
            issues.append({"path": full, "code": "UNSAFE_PATH"})
            continue
        if name in seen:
            issues.append({"path": name, "code": "DUPLICATE_PATH"})
        seen.add(name)
        if name in INTERNAL_FILES or any(name.startswith(p) for p in INTERNAL_PREFIXES):
            issues.append({"path": name, "code": "INTERNAL_FILE"})
        if DANGEROUS_FILE.search(name):
            issues.append({"path": name, "code": "CREDENTIAL_FILENAME"})
        if SENSITIVE.search(data):
            issues.append({"path": name, "code": "POSSIBLE_SECRET"})
        if b"INTERNAL WORKING DOCUMENT" in data or b"RELEASE EXCLUDE" in data:
            issues.append({"path": name, "code": "INTERNAL_RELEASE_MARKER"})
    return {"archive": path.name, "file_count": len(entries),
            "ok": not issues, "issues": issues}


def main():
    parser = argparse.ArgumentParser(description="Audit public release archive contents")
    parser.add_argument("archives", nargs="+", help="Actual release ZIP/sdist/wheel files")
    args = parser.parse_args()
    reports = [inspect_archive(path) for path in args.archives]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    if not all(r["ok"] for r in reports):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
