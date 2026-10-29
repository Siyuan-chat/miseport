# Contributing to MisePort

Thank you for your interest. MisePort is an Apache-2.0 licensed, merchant-owned, read-only product catalog and MCP/REST interoperability project for Japanese online shops.

## Development and tests

\`\`\`sh
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
python scripts/verify_distribution.py
\`\`\`

Please keep Python and Cloudflare contracts consistent; use synthetic fixtures in \`tests/fixtures/\`. Do not commit API credentials, orders, customer records, unapproved seller images, or private business information.

## Pull requests and issue quality

Describe what changed, the source/version of any official EC platform API or CSV format, and exact tests run. Keep a clear separation between proposed features, mock-tested Alpha code, Windows UI acceptance, and actually authorized merchant usage. New connectors must be read-only by default, handle missing data honestly and preserve source URLs and timestamps. Avoid adding model/API costs as requirements.

Review the [public product status](docs/STATUS.md), [test guide](docs/TESTING.md), [platform compatibility](docs/PLATFORM_COMPATIBILITY.ja.md), and [roadmap](docs/ROADMAP.md). For security concerns see [SECURITY.md](SECURITY.md).

All public releases and community submissions must be evidence-based and authorized. A working MCP tool does not imply its discovery or endorsement by Meta Muse.
