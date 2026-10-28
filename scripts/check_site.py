"""Static document checks only; does not claim browser/layout verification."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Check(HTMLParser):
    pairs = 0
    links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "data-ja" in values or "data-en" in values:
            assert values.get("data-ja") and values.get("data-en"), "incomplete translation"
            self.pairs += 1
        for key in ("href", "src"):
            if key in values:
                target = values[key]
                if target.startswith("#"):
                    continue
                assert ":" not in target, f"unexpected external resource: {target}"
                assert (ROOT / "site" / target).is_file(), f"missing local target: {target}"
                self.links.append(target)


text = (ROOT / "site/index.html").read_text(encoding="utf-8")
assert "\ufffd" not in text
check = Check()
check.feed(text)
assert check.pairs >= 20
assert '<html lang="ja">' in text and 'id="language"' in text
assert '@media(max-width:760px)' in text
print(f"Static site: {check.pairs} translation pairs, {len(check.links)} local links/assets valid.")
