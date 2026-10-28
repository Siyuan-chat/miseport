"""Regenerate inspectable schemas from the validated models."""
from pathlib import Path
import json
from miseport.core import Product
from miseport.legacy import CanonicalDocument, LegacyDocument

root = Path(__file__).resolve().parents[1]
for filename, model in [("product.schema.json", Product),
                        ("catalog-envelope.schema.json", CanonicalDocument),
                        ("legacy-catalog.schema.json", LegacyDocument)]:
    (root / "examples" / filename).write_text(
        json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Generated product, canonical envelope and legacy catalog schemas.")
