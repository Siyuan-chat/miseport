import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import data from './generated-catalog.mjs';
import {createCatalog, normalize} from './catalog.mjs';
import {createWorker} from './worker.mjs';
import {validate, PROTOCOL_VERSION} from './mcp.mjs';

const env = {MISEPORT_ALLOWED_HOSTS: 'demo.example'};
const init = {jsonrpc: '2.0', id: 1, method: 'initialize', params: {protocolVersion: PROTOCOL_VERSION, capabilities: {}, clientInfo: {name: 'local-test', version: '1'}}};
function request(path = '/mcp', body = init, headers = {}, method = 'POST') {
  return new Request(`https://demo.example${path}`, {method,
    headers: {'content-type': 'application/json', accept: 'application/json, text/event-stream', ...headers},
    ...(method === 'GET' || method === 'HEAD' ? {} : {body: typeof body === 'string' ? body : JSON.stringify(body)})});
}
const tool = (name, args = {}) => ({jsonrpc: '2.0', id: 2, method: 'tools/call', params: {name, arguments: args}});
const catalog = createCatalog(data);

test('Python-generated contract cases match all six catalog operations', async () => {
  const {cases} = JSON.parse(await readFile(new URL('./contract-cases.json', import.meta.url), 'utf8'));
  assert.ok(cases.length > 0);
  const covered = new Set();
  for (const item of cases) {
    assert.ok(['search', 'detail', 'inventory', 'quote', 'audit', 'jsonld'].includes(item.method));
    assert.deepEqual(catalog[item.method](...item.args), item.expected, `${item.method}(${JSON.stringify(item.args)})`);
    covered.add(item.method);
  }
  assert.equal(covered.size, 6);
});

test('public adapter refuses empty, mixed and non-demo metadata catalogs', () => {
  assert.throws(() => createCatalog({...data, products: []}));
  assert.throws(() => createCatalog({...data, products: [{...data.products[0], is_demo: false}]}));
  assert.throws(() => createCatalog({...data, metadata: {demo_only: false}}));
  assert.throws(() => createCatalog({...data, products: [data.products[0], data.products[0]]}));
});

test('all fields/timestamps survive and callers cannot mutate the catalog', () => {
  const p = data.products[0], response = catalog.detail(p.sku);
  assert.deepEqual(response.product, p);
  response.product.name = 'mutated';
  assert.equal(catalog.detail(p.sku).product.name, p.name);
  assert.ok(p.updated_at.endsWith('+09:00'));
  const utc = createCatalog({...data, products: [{...p, updated_at: '2026-10-27T00:00:00Z', snapshot_at: '2026-10-27T00:00:00Z'}]});
  assert.equal(utc.detail(p.sku).product.updated_at, '2026-10-27T00:00:00Z');
  assert.equal(utc.inventory(p.sku).updated_at, '2026-10-27T00:00:00+00:00');
});

test('casefold and Japanese normalization; strict quantities and unknown totals', () => {
  assert.equal(normalize('ＳＴＲＡẞＥ ｺｰﾋｰ'), normalize('strasse こーひー'));
  for (const quantity of [0, 1001, true, 1.5, '2', null]) assert.throws(() => catalog.quote(data.products[0].sku, quantity));
  assert.equal(catalog.quote(data.products[0].sku, 1000).quantity, 1000);
  const unknown = data.products.find(p => p.shipping_jpy === null);
  assert.ok(unknown); assert.equal(catalog.quote(unknown.sku).total_jpy, null);
  assert.equal(catalog.quote(unknown.sku).complete_total, false);
});

test('schema validator rejects unknown properties and wrong scalar types', () => {
  const schema = {type: 'object', properties: {flag: {type: 'boolean'}, amount: {type: 'integer', minimum: 1, maximum: 3}, mode: {enum: ['a', 'b']}}, required: ['flag']};
  for (const value of [{}, {flag: 'false'}, {flag: false, extra: 2}, {flag: true, amount: true}, {flag: true, amount: 4}, {flag: true, mode: 'c'}]) assert.throws(() => validate(schema, value));
  validate(schema, {flag: false, amount: 1, mode: 'a'});
});

test('initialize negotiates target version with older clients without creating a session', async () => {
  const worker = createWorker();
  for (const version of [PROTOCOL_VERSION, '2024-11-05', '2099-01-01']) {
    const message = structuredClone(init); message.params.protocolVersion = version;
    const response = await worker.fetch(request('/mcp', message), env);
    assert.equal(response.status, 200); assert.equal(response.headers.get('mcp-session-id'), null);
    const body = await response.json(); assert.equal(body.result.protocolVersion, PROTOCOL_VERSION);
    assert.equal(body.result.capabilities.tools.listChanged, false);
  }
});

test('initialized notification has an empty 202 response; ping and tool discovery', async () => {
  const worker = createWorker();
  const notified = await worker.fetch(request('/mcp', {jsonrpc: '2.0', method: 'notifications/initialized'}), env);
  assert.equal(notified.status, 202); assert.equal(await notified.text(), '');
  const ping = await worker.fetch(request('/mcp', {jsonrpc: '2.0', id: 'p', method: 'ping'}), env);
  assert.deepEqual((await ping.json()).result, {});
  const response = await worker.fetch(request('/mcp', {jsonrpc: '2.0', id: 3, method: 'tools/list'}), env);
  const body = await response.json(); assert.equal(body.result.tools.length, data.tools.length);
  for (const t of body.result.tools) {
    assert.equal(t.annotations.readOnlyHint, true);
    assert.deepEqual(t.inputSchema, data.tools.find(v => v.name === t.name).inputSchema);
    assert.ok(Object.values(t).every(value => value !== null));
  }
});

test('all seven tools return text and structuredContent matching the catalog', async () => {
  const worker = createWorker(), sku = data.products[0].sku;
  const tests = [['get_product', {sku}, catalog.detail(sku)], ['check_inventory', {sku}, catalog.inventory(sku)], ['get_quote', {sku, quantity: 2}, catalog.quote(sku, 2)], ['audit_catalog', {}, catalog.audit()], ['export_product_jsonld', {sku}, catalog.jsonld(sku)], ['search_products', {}, catalog.search()]];
  for (const [name, args, expected] of tests) {
    const body = await (await worker.fetch(request('/mcp', tool(name, args)), env)).json();
    assert.equal(body.result.isError, false); assert.deepEqual(body.result.structuredContent, expected);
    assert.deepEqual(JSON.parse(body.result.content[0].text), expected);
  }
  const about = await (await worker.fetch(request('/mcp', tool('about_miseport')), env)).json();
  assert.equal(about.result.structuredContent.transport, 'streamable-http');
});

test('tool wrong types, null arguments, unknown fields and limits produce isError', async () => {
  const worker = createWorker();
  for (const args of [{limit: true}, {limit: '2'}, {limit: 101}, {in_stock_only: 1}, {invented: 1}, null]) {
    const body = await (await worker.fetch(request('/mcp', tool('search_products', args)), env)).json();
    assert.equal(body.result.isError, true, JSON.stringify(args));
  }
  const bad = await (await worker.fetch(request('/mcp', tool('get_quote', {sku: data.products[0].sku, quantity: 1001})), env)).json();
  assert.equal(bad.result.isError, true);
});

test('unknown tools/methods and invalid requests yield JSON-RPC errors', async () => {
  const worker = createWorker();
  for (const [message, code] of [[tool('not_a_tool'), -32602], [{jsonrpc: '2.0', id: 4, method: 'write/order'}, -32601], [[], -32600], [{jsonrpc: '2.0', id: null, method: 'ping'}, -32600]]) {
    const body = await (await worker.fetch(request('/mcp', message), env)).json(); assert.equal(body.error.code, code);
  }
  const response = await worker.fetch(request('/mcp', '{'), env); assert.equal(response.status, 400); assert.equal((await response.json()).error.code, -32700);
});

test('MCP method/content/Accept/version protections', async () => {
  const worker = createWorker();
  for (const method of ['GET', 'DELETE']) assert.equal((await worker.fetch(request('/mcp', '', {}, method), env)).status, 405);
  assert.equal((await worker.fetch(request('/mcp', init, {'content-type': 'text/plain'}), env)).status, 415);
  assert.equal((await worker.fetch(request('/mcp', init, {accept: 'application/json'}), env)).status, 406);
  assert.equal((await worker.fetch(request('/mcp', init, {accept: 'application/json;q=0, text/event-stream'}), env)).status, 406);
  assert.equal((await worker.fetch(request('/mcp', init, {'mcp-protocol-version': 'garbage'}), env)).status, 400);
  assert.equal((await worker.fetch(request('/mcp', init, {'mcp-protocol-version': '2025-03-26'}), env)).status, 200);
});

test('64 KiB body limit is enforced for declared and actual streaming bytes', async () => {
  const worker = createWorker();
  assert.equal((await worker.fetch(request('/mcp', init, {'content-length': '65537'}), env)).status, 413);
  assert.equal((await worker.fetch(request('/mcp', 'x'.repeat(65537)), env)).status, 413);
  assert.equal((await worker.fetch(request('/mcp', init, {'content-length': 'bad'}), env)).status, 400);
});

test('a stalled request body reaches its 15-second deadline and is cancelled', {timeout: 20000}, async () => {
  let cancelled = false;
  const stream = new ReadableStream({cancel() {cancelled = true;}});
  const slow = new Request('https://demo.example/mcp', {method: 'POST', body: stream, duplex: 'half',
    headers: {'content-type': 'application/json', accept: 'application/json, text/event-stream'}});
  const response = await createWorker().fetch(slow, env);
  assert.equal(response.status, 408); assert.match((await response.json()).error.message, /deadline/);
  assert.equal(cancelled, true);
});

test('exact Host configuration and own/allowlisted Origin; XFF does not change limits', async () => {
  const worker = createWorker({rateLimit: 2});
  assert.equal((await worker.fetch(request('/healthz', '', {}, 'GET'), {})).status, 503);
  assert.equal((await worker.fetch(request('/healthz', '', {host: 'evil.example'}, 'GET'), env)).status, 421);
  assert.equal((await worker.fetch(request('/healthz', '', {origin: 'https://evil.example'}, 'GET'), env)).status, 403);
  let response = await worker.fetch(request('/healthz', '', {origin: 'https://demo.example', 'x-forwarded-for': '1'}, 'GET'), env);
  assert.equal(response.status, 200); assert.equal(response.headers.get('access-control-allow-origin'), 'https://demo.example');
  response = await worker.fetch(request('/healthz', '', {origin: 'https://allowed.example', 'x-forwarded-for': '2'}, 'GET'), {...env, MISEPORT_ALLOWED_ORIGINS: 'https://allowed.example'});
  assert.equal(response.status, 200);
  assert.equal((await worker.fetch(request('/healthz', '', {'x-forwarded-for': '3'}, 'GET'), env)).status, 429);
});

test('REST endpoints match catalog and support strict read-only arguments', async () => {
  const worker = createWorker(), sku = encodeURIComponent(data.products[0].sku);
  for (const [path, expected] of [['/api/products', catalog.search()], [`/api/products/${sku}`, catalog.detail(data.products[0].sku)], [`/api/inventory/${sku}`, catalog.inventory(data.products[0].sku)], [`/api/quote/${sku}?quantity=2`, catalog.quote(data.products[0].sku, 2)], [`/api/products/${sku}/jsonld`, catalog.jsonld(data.products[0].sku)], ['/api/audit', catalog.audit()]]) {
    const response = await worker.fetch(request(path, '', {}, 'GET'), env); assert.equal(response.status, 200); assert.deepEqual(await response.json(), expected);
  }
  const absent = await worker.fetch(request('/api/products/missing', '', {}, 'GET'), env); assert.equal(absent.status, 404); assert.deepEqual(await absent.json(), catalog.detail('missing'));
  for (const path of ['/api/products?limit=true', '/api/products?limit=2&limit=3', '/api/products?other=1', `/api/quote/${sku}?quantity=0`, `/api/quote/${sku}?quantity=1.5`]) assert.equal((await worker.fetch(request(path, '', {}, 'GET'), env)).status, 400, path);
  assert.equal((await worker.fetch(request('/api/audit', {}), env)).status, 405);
  const spec = await (await worker.fetch(request('/openapi.json', '', {}, 'GET'), env)).json(); assert.equal(spec.openapi, '3.1.0'); assert.ok(spec.paths['/api/products/{sku}']);
});

test('only static routes reach the ASSETS binding; no external fetch', async () => {
  const worker = createWorker(); let calls = 0;
  const bound = {...env, ASSETS: {fetch: async () => {calls++; return new Response('static');}}};
  assert.equal(await (await worker.fetch(request('/', '', {}, 'GET'), bound)).text(), 'static');
  assert.equal((await worker.fetch(request('/api/not-found', '', {}, 'GET'), bound)).status, 404); assert.equal(calls, 1);
});
