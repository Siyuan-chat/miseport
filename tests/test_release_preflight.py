"""The GitHub tag source archive has a different surface than sdist/wheel."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = spec_from_file_location(name, ROOT / path)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tag_preflight_blocks_development_docs_and_retired_assets(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    module = load_module("miseport_release_preflight", "scripts/release_preflight.py")
    dirty = [
        "README.md",
        "PROJECT_STATUS.md",
        "docs/DEVELOPMENT_PLAN.zh-CN.md",
        "references/legacy-20261027/roadmap.reference.md",
        "assets/logo-light.svg",
        "src/miseport/core.py",
    ]
    assert module.release_blockers(dirty) == [
        "PROJECT_STATUS.md",
        "assets/logo-light.svg",
        "docs/DEVELOPMENT_PLAN.zh-CN.md",
        "references/legacy-20261027/roadmap.reference.md",
    ]
    assert module.release_blockers([
        "README.md", "LICENSE", "src/miseport/core.py", "tests/test_base_urls.py",
    ]) == []
