import {mkdir, readFile, writeFile, copyFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const out = path.join(here, 'public');
const origin = process.env.MISEPORT_PUBLIC_ORIGIN || 'https://miseport.pages.dev';
if (new URL(origin).protocol !== 'https:' || new URL(origin).origin !== origin) throw new Error('Expected exact HTTPS public origin');
await mkdir(path.join(out, 'assets/original'), {recursive: true});
await mkdir(path.join(out, 'docs'), {recursive: true});
await copyFile(path.join(root, 'assets/original/miseport-logo.png'), path.join(out, 'assets/original/miseport-logo.png'));
let html = await readFile(path.join(root, 'site/index.html'), 'utf8');
const css = /<style>([\s\S]*?)<\/style>/.exec(html)?.[1];
const script = /<script>([\s\S]*?)<\/script>/.exec(html)?.[1];
if (!css || !script) throw new Error('Site source layout changed');
html = html.replace(/<style>[\s\S]*?<\/style>/, '<link rel="stylesheet" href="/styles.css">');
html = html.replace(/<script>[\s\S]*?<\/script>/, '<script src="/site.js" defer></script><script src="/demo.js" defer></script>');
html = html.replaceAll('../assets/', '/assets/');
html = html.replaceAll('href="../README.ja.md"', 'href="/docs/?lang=ja" data-doc-link');
html = html.replaceAll('href="../docs/DEPLOYMENT.md"', 'href="/docs/#deployment"');
html = html.replaceAll('href="../docs/SCENARIOS.ja.md"', 'href="/docs/#testing"');
for (const [before, after] of [
  ['ローカルstdio MCPカタログの試作。', '出典付き商品カタログの読み取り専用デモ。'],
  ['ローカルで試す →', '接続方法を見る →'], ['Try it locally →', 'Connection guide →'],
  ['開発中の試作 · Python 3.10+ · stdio MCP', '架空データ専用 · 読み取り専用 · MCP / REST'],
  ['Prototype in development · Python 3.10+ · stdio MCP', 'Synthetic demo · Read-only · MCP / REST'],
  ['Local catalog prototype', 'Read-only catalog demo'],
  ['CATALOG / coffee-001', 'CATALOG / tea-001'], ['ドリップコーヒー', '京都産ほうじ茶 ギフト'],
  ['Drip coffee', 'Kyoto hojicha gift'], ['¥1,200', '¥1,850'],
  ['現在はローカルstdioのみ。決済・注文・取り置きは行いません。在庫や価格は取得済みデータであり、購入前には販売元で確認が必要です。', '公開デモは架空の商品情報だけを返します。決済・注文・取り置きは行いません。価格や在庫は記録時点の情報です。'],
  ['Local stdio only. No payments, orders, or reservations. Catalog prices and stock are snapshots; confirm current details with the seller before buying.', 'The public demo returns fictional catalog data only. No payments, orders, or reservations. Prices and stock are dated snapshots.'],
  ['Muse参加資格、正式リポジトリ、公開ドメインは未確認です。11月10日は作業目標で、審査や公開の完了を保証するものではありません。このページは未公開の草稿です。', 'ソースはGitHubで公開しています。独自ドメインは未取得で、Cloudflareの標準URLを利用しています。Museとの実接続は検証中で、掲載承認や推薦を保証しません。'],
  ['Muse eligibility, the final repository, and the production domain are unverified. November 10 is a planning target, not a promise of approval or launch. This page is an unpublished draft.', 'Source is public on GitHub. No custom domain has been purchased; this uses a Cloudflare URL. Muse integration is under test, with no listing approval or recommendations claimed.']
]) html = html.replaceAll(before, after);
const demo = `<section class="section" id="demo"><div class="eyebrow">SYNTHETIC DATA ONLY</div><h2 data-ja="架空カタログを検索する" data-en="Search the fictional catalog">架空カタログを検索する</h2><p data-ja="実在のお店ではありません。在庫・送料・価格は古い記録で、購入できません。" data-en="This is not a real shop. Stock, shipping, and prices are dated records; purchases are unavailable.">実在のお店ではありません。在庫・送料・価格は古い記録で、購入できません。</p><form id="demo-form"><label for="query">商品検索 / Product search</label><div class="search-row"><input id="query" name="query" value="ほうじ茶" maxlength="500"><button type="submit" class="cta">検索 / Search</button></div></form><p id="demo-status" aria-live="polite"></p><div id="demo-results" class="cards"></div><p class="small">MCP: <a href="/docs/#mcp">${origin}/mcp</a> · <a href="/openapi.json">OpenAPI</a> · <a href="https://github.com/Siyuan-chat/miseport">GitHub</a></p></section>`;
html = html.replace('</main>', demo + '</main>');
html = html.replace('</head>', `<link rel="canonical" href="${origin}/"><meta property="og:title" content="MisePort — Agent-ready commerce"><meta property="og:image" content="${origin}/assets/original/miseport-logo.png"></head>`);
html = html.replace('</footer>', '<span><a href="/privacy.html">Privacy</a> · <a href="/terms.html">Demo terms</a></span></footer>');
let activeScript = script.replace("document.querySelectorAll('a[href=\"../README.ja.md\"],a[href=\"../README.md\"]')", "document.querySelectorAll('[data-doc-link]')");
activeScript = activeScript.replace("'../README.ja.md':'../README.md'", "'/docs/?lang=ja':'/docs/?lang=en'");
const extraCss = '\n.search-row{display:flex;gap:12px;align-items:center}.search-row input{min-width:0;flex:1;font:inherit;padding:12px;border:1px solid var(--line);border-radius:8px}.search-row .cta{margin:0;border:0}.card dl{font-size:14px}.card dt{font-weight:700}.card dd{margin:0 0 10px;overflow-wrap:anywhere}.doc{max-width:840px;margin:50px auto;padding:0 24px}.doc code{overflow-wrap:anywhere}.doc pre{overflow:auto}.doc h2{margin-top:40px}@media(max-width:500px){.search-row{align-items:stretch;flex-direction:column}}';
await writeFile(path.join(out, 'index.html'), html);
await writeFile(path.join(out, 'styles.css'), css + extraCss);
await writeFile(path.join(out, 'site.js'), activeScript);
await copyFile(path.join(here, 'demo-ui.js'), path.join(out, 'demo.js'));
const frame = (title, body, route) => `<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title} — MisePort</title><link rel="canonical" href="${origin}${route}"><link rel="stylesheet" href="/styles.css"></head><body><main class="doc"><a href="/">← MisePort</a><h1>${title}</h1>${body}<p><a href="/privacy.html">Privacy</a> · <a href="/terms.html">Demo terms</a> · <a href="https://github.com/Siyuan-chat/miseport">Source</a></p></main></body></html>`;
await writeFile(path.join(out, 'docs/index.html'), frame('接続ガイド / Connection guide', `<p>読み取り専用・架空データ専用 / Read-only synthetic data only.</p><h2 id="mcp">MCP</h2><pre>${origin}/mcp</pre><p>Stateless Streamable HTTP, JSON responses, protocol 2025-11-25. No credential is required for this public fictional demo. Send Accept: application/json, text/event-stream and Content-Type: application/json. This is not a production or personal-data endpoint.</p><pre>{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"your-client","version":"1"}}}</pre><p>Tools: about_miseport, search_products, get_product, check_inventory, get_quote, audit_catalog, export_product_jsonld.</p><h2>REST / OpenAPI</h2><p><a href="/openapi.json">OpenAPI document</a> · <a href="/api/products?query=%E3%81%BB%E3%81%86%E3%81%98%E8%8C%B6">Sample search</a> · <a href="/api/quote/tea-001?quantity=2">Sample nonbinding quote</a></p><p>Use these GET APIs if a custom-connector host asks for API information. Do not infer that every MCP-capable host accepts this endpoint automatically.</p><h2 id="testing">Muse integration status</h2><p>接続検証中です。Muse実呼び出しの成功や公開ディレクトリ承認はまだ主張しません。Integration testing is in progress; no successful Muse call or official listing is claimed. <a href="https://www.meta.com/help/superintelligence/1687253048996149/">Official custom connector guide</a>.</p><p>Keep is_demo, source_url, evidence_url and updated_at visible. Unknown shipping/tax/stock must remain unknown. A quote never creates a reservation or payment. The tea-001 example is fictional, recorded 2026-10-27.</p><h2 id="deployment">Runtime limits</h2><p>Exact Host/Origin rules; 64 KiB MCP body cap; bounded request reads; per-isolate/IP throttling. No outbound product fetch, account or data write. Global rate guarantees, OAuth and tenant isolation are not implemented for this public sample. Cloudflare free quotas may stop availability. No private merchant data should be submitted.</p>`, '/docs/'));
await writeFile(path.join(out, 'privacy.html'), frame('Privacy / データの扱い', `<p>This demo serves a fixed fictional product catalog. It has no account, payment, customer records, analytics tag or application database. The application does not persist search text or tool-call bodies. Temporary in-memory IP counters enforce request limits and expire; this is not a promise about Cloudflare network logs.</p><p>Cloudflare provides hosting and may process request metadata under its own <a href="https://www.cloudflare.com/privacypolicy/">privacy policy</a>. If connected to Muse or another host, that host also processes your requests under its terms. Use sample product queries only, without personal information, credentials or real customer data.</p><p>このデモに秘密情報や個人情報を送信しないでください。公開の架空商品を確認するためのサービスです。</p><p>Project questions: <a href="https://github.com/Siyuan-chat/miseport/issues">GitHub issues</a>; do not include secrets or personal data in public reports. Last updated 2026-10-29.</p>`, '/privacy.html'));
await writeFile(path.join(out, 'terms.html'), frame('Demo terms / デモの制約', `<p>MisePort is independent open-source software. This public endpoint contains fictional, dated samples; it does not represent real merchants or offer goods for sale. No order, checkout, payment, stock reservation or live quote is provided. Sources using example.org are synthetic references.</p><p>Do not rely on these amounts for purchases, submit private data, or attempt to access unrelated infrastructure. Availability is limited by hosting quotas. Source is licensed under Apache-2.0; no affiliation, Muse approval, traffic or recommendation is claimed.</p><p>架空データの検証用です。実在商品の購入、在庫確認、最終決済金額の確認には使えません。</p>`, '/terms.html'));
await writeFile(path.join(out, 'robots.txt'), `User-agent: *\nAllow: /\nSitemap: ${origin}/sitemap.xml\n`);
await writeFile(path.join(out, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${['/','/docs/','/privacy.html','/terms.html'].map(route=>`<url><loc>${origin}${route}</loc></url>`).join('')}</urlset>`);
await writeFile(path.join(out, '_headers'), '/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Content-Security-Policy: default-src \'self\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; connect-src \'self\'; frame-ancestors \'none\'; base-uri \'self\'; object-src \'none\'\n');
console.log('Built bilingual site, original logo, demo search, connection guide, privacy and demo terms.');
