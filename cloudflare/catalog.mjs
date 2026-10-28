// Dependency-free mirror of Python Catalog/commerce for generated, validated demos.
const copy = value => structuredClone(value);
const integer = value => typeof value === 'number' && Number.isSafeInteger(value);
const count = value => [...value].length;
const equal = (a, b) => a < b ? -1 : a > b ? 1 : 0;
// Product.model_dump emits Z for UTC; commerce.datetime.isoformat emits +00:00.
const isoformat = value => value === null ? null : value.replace(/Z$/, '+00:00');
export function normalize(text) {
  // Common Python casefold differences after NFKC, then katakana -> hiragana.
  return text.normalize('NFKC').toLowerCase().replace(/ß/g, 'ss').replace(/ς/g, 'σ')
    .replace(/[\u0345]/g, 'ι').replace(/[ァ-ヶ]/g, c => String.fromCodePoint(c.codePointAt(0) - 0x60));
}
function freeze(value) {
  if (value && typeof value === 'object') { Object.freeze(value); Object.values(value).forEach(freeze); }
  return value;
}
export function createCatalog(data) {
  if (!data || !Array.isArray(data.products) || !data.products.length || data.products.length > 10000)
    throw new Error('public demo requires 1..10000 validated products');
  if (data.metadata?.demo_only === false || data.products.some(p => p.is_demo !== true))
    throw new Error('public Worker refuses non-demo catalogs');
  const products = freeze(copy(data.products)), bySku = new Map();
  for (const p of products) {
    if (typeof p.sku !== 'string' || !p.sku || bySku.has(p.sku)) throw new Error('invalid or duplicate SKU');
    if (!integer(p.price_jpy) || p.price_jpy < 0 || p.currency !== 'JPY' ||
      !['in_stock', 'out_of_stock', 'unknown'].includes(p.stock) ||
      (p.tax_included !== null && typeof p.tax_included !== 'boolean') ||
      !['source_url', 'updated_at', 'name', 'description', 'category'].every(k => typeof p[k] === 'string'))
      throw new Error('catalog must be generated from Python-validated Product records');
    for (const k of ['stock_quantity', 'shipping_jpy']) {
      if (p[k] !== null && (!integer(p[k]) || p[k] < 0)) throw new Error(`${k} must be a safe nonnegative integer or null`);
    }
    if (p.stock_quantity !== null && p.stock !== (p.stock_quantity > 0 ? 'in_stock' : 'out_of_stock'))
      throw new Error('stock_quantity contradicts stock');
    bySku.set(p.sku, p);
  }
  const facts = p => ({product_id: p.sku, stock: p.stock, stock_quantity: p.stock_quantity,
    stock_is_live: false, is_demo: p.is_demo, source_url: p.source_url,
    evidence_url: p.evidence_url, updated_at: isoformat(p.updated_at), snapshot_at: isoformat(p.snapshot_at)});
  const api = {
    products, metadata: freeze(copy(data.metadata || {})),
    search(query = '', category = null, min_price_jpy = null, max_price_jpy = null,
      in_stock_only = false, limit = 20, offset = 0, gift_wrapping = null, origin_prefecture = null) {
      if (typeof query !== 'string' || (category !== null && typeof category !== 'string')) throw new Error('query and category must be text');
      if (typeof in_stock_only !== 'boolean' || (gift_wrapping !== null && typeof gift_wrapping !== 'boolean')) throw new Error('stock/gift filters must be booleans');
      if (origin_prefecture !== null && (typeof origin_prefecture !== 'string' || count(origin_prefecture) > 200)) throw new Error('origin_prefecture must be text at most 200 characters');
      if (count(query) > 500 || !integer(limit) || !integer(offset) || limit < 1 || limit > 100 || offset < 0) throw new Error('query max 500 chars; limit 1..100; offset >= 0');
      if ([min_price_jpy, max_price_jpy].some(v => v !== null && (!integer(v) || v < 0))) throw new Error('prices must be nonnegative integer JPY');
      if (min_price_jpy !== null && max_price_jpy !== null && min_price_jpy > max_price_jpy) throw new Error('min price exceeds max price');
      const terms = normalize(query).split(/\s+/u).filter(Boolean);
      const matches = products.filter(p => {
        const haystack = normalize([p.name, p.description, p.category, p.sku, p.origin_prefecture || '', p.caffeine_level || ''].join(' '));
        return terms.every(t => haystack.includes(t)) &&
          (category === null || normalize(category) === normalize(p.category)) &&
          (min_price_jpy === null || p.price_jpy >= min_price_jpy) && (max_price_jpy === null || p.price_jpy <= max_price_jpy) &&
          (!in_stock_only || p.stock === 'in_stock') && (gift_wrapping === null || p.gift_wrapping === gift_wrapping) &&
          (origin_prefecture === null || normalize(p.origin_prefecture || '') === normalize(origin_prefecture));
      }).sort((a, b) => a.price_jpy - b.price_jpy || equal(a.sku, b.sku));
      return copy({products: matches.slice(offset, offset + limit), total: matches.length, offset, limit});
    },
    detail(sku) { const p = bySku.get(sku); return copy({product: p || null, found: !!p}); },
    inventory(sku) { const p = bySku.get(sku); return copy(p ? {found: true, ...facts(p)} : {found: false, product_id: sku}); },
    quote(sku, quantity = 1) {
      if (!integer(quantity) || quantity < 1 || quantity > 1000) throw new Error('quantity must be an integer in 1..1000');
      const p = bySku.get(sku); if (!p) return {found: false, product_id: sku};
      const subtotal = p.price_jpy * quantity;
      const total = p.tax_included === true && p.shipping_jpy !== null ? subtotal + p.shipping_jpy : null;
      if (!integer(subtotal) || (total !== null && !integer(total))) throw new Error('amount exceeds safe integer precision');
      const available = p.stock_quantity !== null ? p.stock_quantity >= quantity : p.stock === 'out_of_stock' ? false : null;
      return copy({found: true, ...facts(p), quantity, currency: 'JPY', unit_price_jpy: p.price_jpy,
        subtotal_jpy: subtotal, tax_included: p.tax_included, shipping_jpy: p.shipping_jpy,
        total_jpy: total, complete_total: total !== null, can_fulfill_snapshot: available,
        is_binding: false, can_purchase: false,
        shipping_basis: 'catalog per-order snapshot; destination not evaluated',
        message: 'Dated reference amount, not a live checkout quote or reservation.'});
    },
    audit() {
      const fields = ['tax_included', 'shipping_jpy', 'stock', 'evidence_url', 'merchant_id', 'gift_wrapping', 'origin_prefecture', 'caffeine_level', 'image_url'];
      const missing = Object.fromEntries(fields.map(f => [f, []])), issues = [];
      for (const p of products) {
        for (const f of fields) if (p[f] === null || (f === 'stock' && p.stock === 'unknown')) missing[f].push(p.sku);
        if (p.tax_included !== true) issues.push({product_id: p.sku, code: 'TAX_UNRESOLVED_FOR_TOTAL'});
        if (p.evidence_url && new URL(p.source_url).hostname !== new URL(p.evidence_url).hostname) issues.push({product_id: p.sku, code: 'DIFFERENT_EVIDENCE_HOST'});
      }
      return {product_count: products.length, demo_product_count: products.length, stock_is_live: false,
        missing_fields: missing, issues, checks: {schema: 'validated', crawlability: 'not_tested', indexing: 'not_tested', muse_discoverability: 'not_tested', transactions: 'not_implemented'},
        note: 'Missingness is not an AI ranking or merchant verification score.'};
    },
    jsonld(sku) {
      const p = bySku.get(sku); if (!p) return {found: false, product_id: sku, jsonld: null};
      const offer = {'@type': 'Offer', price: String(p.price_jpy), priceCurrency: 'JPY', url: p.source_url};
      if (p.stock !== 'unknown') offer.availability = p.stock === 'in_stock' ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock';
      const properties = {is_demo: p.is_demo, stock_is_live: false, updated_at: isoformat(p.updated_at), evidence_url: p.evidence_url, snapshot_at: isoformat(p.snapshot_at)};
      const value = {'@context': 'https://schema.org', '@type': 'Product', sku: p.sku, name: p.name,
        description: p.description, url: p.source_url, offers: offer,
        additionalProperty: Object.entries(properties).filter(([, v]) => v !== null).map(([name, value]) => ({'@type': 'PropertyValue', name, value}))};
      if (p.image_url) value.image = p.image_url;
      return copy({found: true, product_id: sku, jsonld: value});
    }
  };
  return Object.freeze(api);
}
