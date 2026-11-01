"""Fail a release candidate if Markdown links point to deleted local files.

External links are deliberately not validated here; only tracked Git files.
"""
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

LINK = re.compile(r"\]\(([^)]+)\)")


def _tracked(root):
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                       check=True, capture_output=True)
    return {x.decode("utf-8") for x in r.stdout.split(b"\x00") if x}


def broken_links(root):
    root = Path(root)
    tracked = _tracked(root)
    missing = []
    for path in sorted(p for p in tracked if p.lower().endswith(".md")):
        file = root / path
        if not file.is_file():
            continue
        content = file.read_text(encoding="utf-8")
        for link in LINK.findall(content):
            uri = link.strip().split()[0].strip("<>")
            if uri.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            local = unquote(uri.split("#", 1)[0].split("?", 1)[0])
            if not local:
                continue
            target = (file.parent / local).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                missing.append((path, local, "unsafe relative path"))
                continue
            if not target.is_file() and not target.is_dir():
                missing.append((path, local, "not found"))
    return missing


def main():
    root = Path(__file__).resolve().parents[1]
    missing = broken_links(root)
    for path, link, reason in missing:
        print(f"{path}: {link} — {reason}")
    print("Local Markdown link check:", "FAIL" if missing else "PASS",
          "(" + str(len(missing)) + " issue(s))")
    if missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
