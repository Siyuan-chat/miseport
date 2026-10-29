"""Validate screenshots produced by the actual MisePort Tk window.

Only synthetic merchant data may be used for the visual smoke test.
The check is not an accessibility audit or Windows end-user acceptance.
"""
from hashlib import sha256
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Install Pillow in visual-test environment.")


FILES = ("01-shops-and-products.png",
         "02-product-review.png",
         "03-publish-steps.png")


def main():
    directory = Path(sys.argv[1])
    hashes = []
    for name in FILES:
        path = directory / name
        if not path.is_file():
            raise SystemExit(f"Missing screenshot: {name}")
        with Image.open(path) as image:
            if (image.format != "PNG" or image.width < 880 or image.height < 580
                    or image.mode not in ("RGB", "RGBA")):
                raise SystemExit(f"Invalid GUI screenshot: {name}")
            small = image.resize((100, 70)).convert("RGB")
            variety = small.getcolors(maxcolors=7000)
            if variety is None or len(variety) < 12:
                raise SystemExit(f"Blank/flat GUI screenshot: {name}")
        hashes.append(sha256(path.read_bytes()).hexdigest())
        print(f"{name} verified. Screenshot SHA-256 {hashes[-1][:12]}")
    if hashes[1] == hashes[2]:
        raise SystemExit("The scrollable review page did not change between captures.")
    note = (directory / "README.txt").read_text(encoding="utf-8")
    if not all(k in note for k in ("synthetic", "No actual merchant", "No actual merchant, PAT")):
        raise SystemExit("Synthetic source disclosure missing from visual artifact.")
    print("Actual Tk visual smoke test passed (synthetic data only).")


if __name__ == "__main__":
    main()
