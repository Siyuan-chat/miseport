"""DEVELOPMENT-ONLY GitHub upload helper; NOT a public merchant release packager.

See docs/RELEASE_PUBLICATION_POLICY.ja.md and Issue #10: this currently
includes internal docs and archives, and must not generate 11/10 release assets.

Create a reviewable source-only upload ZIP with explicit allowlists.

Original historical binary packages, environments, Git internals, credentials,
local logs and caches are excluded. This script never connects to GitHub.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import zipfile

root = Path(__file__).resolve().parents[1]
output = root / "artifacts/github-ready"
output.mkdir(parents=True, exist_ok=True)
top = {"pyproject.toml", "MANIFEST.in", "Dockerfile", "Dockerfile.http", ".dockerignore", ".gitignore", ".env.example",
       "README.md", "README.ja.md", "LICENSE", "SECURITY.md", "PROJECT_STATUS.md", "CHANGELOG.md", "CONTRIBUTING.md"}
folders = {"src", "tests", "examples", "docs", "site", "assets", "scripts", ".github", "references", "cloudflare"}
excluded = {"__pycache__", ".pytest_cache", ".git", ".venv", "artifacts", "build", "dist", "node_modules", ".wrangler", "public", "bundle"}
paths = []
candidates = [root / name for name in top if (root / name).is_file()]
for name in sorted(folders):
    folder = root / name
    if not folder.is_dir():
        continue
    for directory, subdirectories, filenames in os.walk(folder, followlinks=False):
        subdirectories[:] = [name for name in subdirectories
                             if name not in excluded and not name.endswith(".egg-info")]
        candidates.extend(Path(directory) / filename for filename in filenames)
for path in sorted(candidates):
    relative = path.relative_to(root)
    if any(part in excluded or part.endswith(".egg-info") for part in relative.parts):
        continue
    if not path.is_file() or not (relative.as_posix() in top or relative.parts[0] in folders):
        continue
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise SystemExit(f"Refuse symlink/outside-root upload path: {relative}")
    if relative.parts[0] == "references" and path.suffix.lower() in {".zip", ".whl"}:
        continue
    if path.suffix.lower() in {".pyc", ".pyo"}:
        continue
    if ((path.name.startswith(".env") and path.name != ".env.example")
            or path.suffix.lower() in {".pem", ".key", ".pfx"}
            or path.name.lower() in {"credentials.json", "id_rsa", "id_ed25519"}):
        raise SystemExit(f"Forbidden upload filename: {relative}")
    data = path.read_bytes()
    if re.search(rb"gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----", data):
        raise SystemExit(f"Possible credential in upload file: {relative}")
    paths.append((path, relative.as_posix(), data))
with zipfile.ZipFile(output / "MisePort-current-GitHub-ready.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path, name, data in paths:
        archive.writestr("miseport/" + name, data)
manifest = {"scope": "local source-only upload candidate; not published",
            "files": [{"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                      for _, name, data in paths]}
(output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"GitHub upload candidate: {len(paths)} files; ZIP and manifest in {output}")
