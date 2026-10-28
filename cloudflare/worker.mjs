import data from './generated-catalog.mjs';
import {createCatalog} from './catalog.mjs';
import {handleMcp, invokeTool, about, json} from './mcp.mjs';

const csv = value => (value || '').split(',').map(v => v.trim()).filter(Boolean);
const numeric = new Set(['min_price_jpy', 'max_price_jpy', 'limit', 'offset', 'quantity']);
const boolean = new Set(['in_stock_only', 'gift_wrapping']);
function parameters(url, allowed) {
  const args = {};
  for (const [name, value] of url.searchParams) {
    if (!allowed.includes(name) || Object.hasOwn(args, name)) throw new Error(`unknown or repeated query parameter: ${name}`);
    if (numeric.has(name)) {
      if (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value))) throw new Error(`${name} must be an integer`);
      args[name] = Number(value);
    } else if (boolean.has(name)) {
      if (!['true', 'false'].includes(value)) throw new Error(`${name} must be true or false`);
      args[name] = value === 'true';
    } else args[name] = value;
  }
  return args;
}
function openapi(url, catalogData) {
  const parameters = name => {
    const schema = catalogData.tools.find(t => t.name === name)?.inputSchema;
    return Object.entries(schema?.properties || {}).filter(([k]) => k !== 'sku').map(([name, schema]) => ({name, in: 'query', required: false, schema}));
  };
  const sku = {name: 'sku', in: 'path', required: true, schema: {type: 'string'}};
  const get = (summary, params = []) => ({get: {summary, parameters: params, responses: {'200': {description: 'Dated synthetic catalog result'}, '400': {description: 'Invalid arguments'}, '404': {description: 'Unknown SKU'}}}});
  return {openapi: '3.1.0', info: {title: 'MisePort read-only synthetic demo', version: catalogData.version,
    description: 'Public demo snapshots only; no OAuth, orders, checkout, live stock or private merchant data.'}, servers: [{url: url.origin}], paths: {
      '/about': get('Scope and limitations'), '/healthz': get('Readiness'),
      '/api/products': get('Search products with AND filters', parameters('search_products')),
      '/api/products/{sku}': get('Product with provenance', [sku]),
      '/api/inventory/{sku}': get('Dated inventory, never live', [sku]),
      '/api/quote/{sku}': get('Nonbinding amount, never a checkout', [sku, ...parameters('get_quote')]),
      '/api/products/{sku}/jsonld': get('Snapshot Product JSON-LD', [sku]), '/api/audit': get('Missing data audit') }};
}
export function createWorker({catalogData = data, clock = Date.now, rateLimit = 120} = {}) {
  const catalog = createCatalog(catalogData), clients = new Map();
  function rate(request) {
    const now = clock(), key = request.headers.get('cf-connecting-ip') || 'unidentified';
    for (const [k, state] of clients) if (now - state.start >= 60000) clients.delete(k);
    let state = clients.get(key);
    if (!state) {
      // Bound memory and fail closed under key churn rather than evict active limits.
      if (clients.size >= 1024) return false;
      state = {start: now, count: 0}; clients.set(key, state);
    }
    state.count++;
    return state.count <= rateLimit;
  }
  return {async fetch(request, env = {}) {
    const url = new URL(request.url), hosts = csv(env.MISEPORT_ALLOWED_HOSTS).map(h => h.toLowerCase());
    if (!hosts.length || hosts.some(h => /[\/*\s,@]/.test(h))) return json({error: 'exact MISEPORT_ALLOWED_HOSTS configuration required'}, 503);
    if (!hosts.includes(url.host.toLowerCase()) || request.headers.has('host') && request.headers.get('host').toLowerCase() !== url.host.toLowerCase()) return json({error: 'invalid Host'}, 421);
    const origin = request.headers.get('origin');
    if (origin && origin !== url.origin && !csv(env.MISEPORT_ALLOWED_ORIGINS).includes(origin)) return json({error: 'invalid Origin'}, 403);
    const dynamic = url.pathname === '/mcp' || url.pathname === '/about' || url.pathname === '/healthz' || url.pathname === '/openapi.json' || url.pathname.startsWith('/api/');
    if (!dynamic) return env.ASSETS ? env.ASSETS.fetch(request) : json({error: 'static assets not bound'}, 404);
    let response;
    if (!rate(request)) response = json({error: 'per-isolate rate limit reached'}, 429, {'retry-after': '60'});
    else if (request.method === 'OPTIONS') response = new Response(null, {status: 204, headers: {'access-control-allow-methods': 'GET, POST, OPTIONS', 'access-control-allow-headers': 'Content-Type, MCP-Protocol-Version', 'access-control-max-age': '600'}});
    else if (url.pathname === '/mcp') response = await handleMcp(request, catalog, catalogData);
    else if (request.method !== 'GET') response = json({error: 'read-only REST uses GET'}, 405, {allow: 'GET'});
    else {
      try {
        let value;
        if (url.pathname === '/healthz') { parameters(url, []); value = {ready: true, demo: true, version: catalogData.version, product_count: catalog.products.length}; }
        else if (url.pathname === '/about') { parameters(url, []); value = about(catalog, catalogData.version); }
        else if (url.pathname === '/openapi.json') { parameters(url, []); value = openapi(url, catalogData); }
        else if (url.pathname === '/api/products') {
          const args = parameters(url, ['query', 'category', 'min_price_jpy', 'max_price_jpy', 'in_stock_only', 'limit', 'offset', 'gift_wrapping', 'origin_prefecture']);
          value = invokeTool('search_products', args, catalog, catalogData);
        } else if (url.pathname === '/api/audit') { parameters(url, []); value = catalog.audit(); }
        else {
          const match = /^\/api\/(products|inventory|quote)\/([^/]+)(\/jsonld)?$/.exec(url.pathname);
          if (!match || match[3] && match[1] !== 'products') return json({error: 'not found'}, 404);
          const sku = decodeURIComponent(match[2]);
          const args = parameters(url, match[1] === 'quote' ? ['quantity'] : []); args.sku = sku;
          const tool = match[3] ? 'export_product_jsonld' : {products: 'get_product', inventory: 'check_inventory', quote: 'get_quote'}[match[1]];
          value = invokeTool(tool, args, catalog, catalogData);
        }
        response = json(value, value.found === false ? 404 : 200);
      } catch (error) { response = json({error: error.message}, 400); }
    }
    if (origin) {
      const headers = new Headers(response.headers); headers.set('access-control-allow-origin', origin); headers.set('vary', 'Origin');
      response = new Response(response.body, {status: response.status, headers});
    }
    return response;
  }};
}
export default createWorker();
