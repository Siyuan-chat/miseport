"""Install the freshly built wheel, then verify the installed CLI/MCP suite.

Use in a disposable CI/verification environment: it replaces its MisePort install.
Does not upload or publish anything.
"""
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

root = Path(__file__).resolve().parents[1]
artifact_directory = root / "artifacts"
artifact_directory.mkdir(parents=True, exist_ok=True)
wheels = sorted((root / "dist").glob("miseport-*.whl"))
if len(wheels) != 1:
    raise SystemExit("Expected one wheel; use a clean dist directory")
wheel = wheels[0]
with zipfile.ZipFile(wheel) as archive:
    modules = [name for name in archive.namelist() if name.startswith("miseport/") and name.endswith(".py")]
    if not modules or not all(archive.read(name) == (root / "src" / name).read_bytes() for name in modules):
        raise SystemExit("Wheel source differs from checkout")
sources = list((root / "dist").glob("miseport-*.tar.gz"))
if len(sources) != 1:
    raise SystemExit("Expected one source archive")
with tarfile.open(sources[0]) as archive:
    names = archive.getnames()
    required = ["examples/products.json", "tests/fixtures/demo-store.reference.json",
                "assets/original/miseport-logo.png", "tests/test_legacy.py"]
    if not all(any(name.endswith("/" + suffix) for name in names) for suffix in required):
        raise SystemExit("Source archive is missing required test/data assets")
# Public Python source distribution has a separate clean-content gate.
# GitHub's automatic tag ZIP must additionally pass release_preflight.py
# after the internal working files are removed from the tagged branch.
from audit_release import inspect_archive
release_report = inspect_archive(sources[0])
if not release_report["ok"]:
    first = ", ".join(x["path"] + ":" + x["code"]
                      for x in release_report["issues"][:12])
    raise SystemExit("Source distribution includes excluded files: " + first)
print("Source distribution public-file allowlist passed.")

subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--force-reinstall", str(wheel)], check=True)
subprocess.run([sys.executable, "-c",
    "from pathlib import Path; import miseport; p=Path(miseport.__file__).resolve(); "
    "assert 'site-packages' in p.parts, p; print('Installed wheel:', p)"], check=True)
subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short",
                f"--basetemp={artifact_directory / 'wheel-verification-temp'}", "-p", "no:cacheprovider",
                f"--junitxml={artifact_directory / 'wheel-verification.xml'}"], cwd=root, check=True)
