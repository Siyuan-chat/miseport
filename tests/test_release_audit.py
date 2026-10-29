"""Release audit is deliberately separate from ordinary development CI."""
import importlib.util
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
module_path = ROOT / "scripts/audit_release.py"
spec = importlib.util.spec_from_file_location("miseport_release_audit", module_path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def build_zip(tmp_path, files):
    path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return path


def test_clean_public_merchant_bundle_passes(tmp_path):
    report = audit.inspect_archive(build_zip(tmp_path, {
        "index.html": "<h1>MisePort</h1>",
        "catalog.json": '{"products":[]}',
        "_worker.js": "export default {}",
        "README.txt": "Read-only public product catalog.",
    }))
    assert report["ok"] and report["file_count"] == 4


def test_internal_docs_forbidden_even_inside_source_archive_prefix(tmp_path):
    report = audit.inspect_archive(build_zip(tmp_path, {
        "miseport-0.1.0/PROJECT_STATUS.md": "# internal",
        "miseport-0.1.0/docs/DEVELOPMENT_PLAN.zh-CN.md": "# internal",
        "miseport-0.1.0/src/miseport/core.py": "print('public')",
    }))
    assert not report["ok"]
    assert len([x for x in report["issues"] if x["code"] == "INTERNAL_FILE"]) == 2


def test_credentials_and_path_traversal_refused(tmp_path):
    secret = ("api_" + "key=" + "X" * 40)
    report = audit.inspect_archive(build_zip(tmp_path, {
        ".env": "password=value",
        "docs/notes.md": secret,
        "../outside.txt": "unsafe",
    }))
    codes = {x["code"] for x in report["issues"]}
    assert {"CREDENTIAL_FILENAME","POSSIBLE_SECRET","UNSAFE_PATH"} <= codes


def test_internal_marker_in_doc_is_blocked_without_false_flagging_code(tmp_path):
    marker = "RELEASE " + "EXCLUDE"
    result = audit.inspect_archive(build_zip(tmp_path, {
        "README.md": "Internal marker: " + marker,
        "src/miseport/example.py": "example = '" + marker + "'",
    }))
    assert not result["ok"]
    assert any(x["code"] == "INTERNAL_RELEASE_MARKER" and x["path"] == "README.md"
               for x in result["issues"])
    assert not any(x["path"] == "src/miseport/example.py" for x in result["issues"])
