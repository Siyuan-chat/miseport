"""Package the built static site plus Advanced Mode Worker, without credentials."""
from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parents[1]
public = root / "cloudflare/public"
output = root / "artifacts/cloudflare-pages"
output.mkdir(parents=True, exist_ok=True)
required = ("index.html", "_worker.js", "docs/index.html", "privacy.html", "terms.html",
            "assets/original/miseport-logo.png")
if not all((public / name).is_file() for name in required):
    raise SystemExit("Build the Pages deployment before packaging")
entries = []
with zipfile.ZipFile(output / "miseport-pages.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(public.rglob("*")):
        if not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(public.resolve()):
            raise ValueError("Unsafe deployment path")
        relative = path.relative_to(public).as_posix()
        if path.name.startswith(".env") or path.suffix in {".pem", ".key"}:
            raise ValueError("Credential-like filename in deployment")
        data = path.read_bytes()
        archive.writestr(relative, data)
        entries.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
(output / "manifest.json").write_text(json.dumps({"origin": "https://miseport.pages.dev",
    "provider": "Cloudflare Pages Advanced Mode", "data": "synthetic-only", "files": entries}, indent=2), encoding="utf-8")
print(f"Cloudflare upload ZIP: {len(entries)} files; static assets + read-only Worker.")
