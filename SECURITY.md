# Security boundaries

This prototype is a read-only local stdio MCP server. It has no listener, authentication service, remote URL importer, payment, checkout or order tool. Only the catalog selected at startup is exposed to the connected client. The server does not visit product URLs or execute descriptions.

Use a dedicated process and only catalogs you are authorized to share with that client. Exclude secrets, personal information and private merchant notes. Data returned by tools is untrusted content, not agent instructions. MCP instructions and annotations communicate this boundary; they do not guarantee that a downstream language model will follow it. The 20 Japanese scenarios include client-level checks which are still pending.

Local JSON/CSV input is bounded to 10 MiB and 10000 products; JSON nesting errors become catalog errors. Catalog validation happens before serving and failed imports preserve the previous output. This is not a sandbox against a malicious operating-system account, hostile local filesystem, or compromised client/dependency. No tenant isolation or network service security is claimed.

Before public hosting, implement and review the transport, authorization, tenant isolation, request bounds, rate limits, observability, retention and incident procedures described in `docs/DEPLOYMENT.md`. Keep dependencies patched and rerun the protocol tests after upgrades. No third-party security audit or vulnerability scan has been completed. A public vulnerability-reporting contact must be chosen before release; do not publish secrets in public issue trackers.
