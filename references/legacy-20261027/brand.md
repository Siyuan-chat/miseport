# MisePort — brand and naming contract

**Decision:** Adopted 2026-10-27 JST, before any public repository, package or domain release.  
**Identity:** `MisePort` (8 Latin letters); Japanese `ミセポート`; lowercase code and URLs `miseport`.  
**Meaning:** Japanese *mise* (店, shop) + *port* (the entry point connecting merchants, developers and agents).  
**Primary English tagline:** **Agent-ready commerce for independent Japanese shops.**  
**Primary Japanese tagline:** **日本の小さなお店を、AIエージェントへ。**

## Naming contract

| Surface | Canonical value | Current status |
| --- | --- | --- |
| Brand | MisePort / ミセポート | Locked |
| GitHub target | `Siyuan-chat/miseport` | **Not created** as of 2026-10-27 |
| Python distribution & import | `miseport` | Built locally; not uploaded to PyPI |
| CLI | `miseport` | Local |
| MCP server CLI | `miseport-mcp` | Local, not publicly deployed |
| MCP display name | `MisePort demo` | Defined in source; host integration not smoke-tested |
| MCP about tool | `about_miseport` | Defined in source |
| Environment variables | `MISEPORT_*` | Used in Docker, code and docs |
| Intended registrable domain | `miseport.dev` | **Not registered; domain/trademark checks outstanding** |
| Planned canonical site | `https://miseport.dev/` | Not deployed |
| Planned documentation alias | `https://docs.miseport.dev/` | Not deployed; redirect to canonical docs on apex to avoid duplicate content |
| Planned MCP endpoint | `https://api.miseport.dev/mcp` | Not deployed |
| Community contribution dir | `connectors/miseport/` | Prepared, not submitted |
| License | Apache-2.0 | In local source |

## Voice and identity

- Japanese merchants: direct, accessible, practical. Explain MCP rather than assuming shop owners know it.
- Developers: truthful, specific interfaces; source provenance, exact permissions, copyable examples.
- Say **agent-ready product data**, **read-only MCP demo**, **independent open source**. Never promise agent rankings, orders, official Meta review or production catalog support.
- Always distinguish target URLs from live, independently validated URLs in external copy.
- Branding/SEO and tool discoverability serve the user's goals; do not insert covert tool-result promotion or ranking preferences.

## Release-cutover rule

Since neither previous working name was publicly published, use only MisePort in all external artifacts. If a preexisting distribution, DNS record or GitHub repo is discovered later, validate ownership and migration before claiming a redirect, rename or release.
