// Single-merchant read-only Cloudflare Pages Advanced Mode Worker.
// Generated code substitutes __MISEPORT_DATA__ and __MISEPORT_HOST__.
// No credentials, orders, payments, dynamic server-side catalog writes or outbound fetches.
const DATA = __MISEPORT_DATA__;
const HOST = __MISEPORT_HOST__;
const ORIGIN = "https://" + HOST;
const PRODUCTS = DATA.products;
const LOOKUP = new Map(PRODUCTS.map(p => [p.sku, p]));
const LIMIT_BYTES = 65536;

function reply(value, status = 200, origin = null) {
  const h = new Headers({
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Vary": "Origin"
  });
  if (origin) h.set("Access-Control-Allow-Origin", origin);
  return new Response(JSON.stringify(value), {status, headers: h});
}
function normalize(x) {
  return String(x).normalize("NFKC").toLowerCase().replace(/[\u30a1-\u30f6]/g,
    c => String.fromCharCode(c.charCodeAt(0) - 96));
}
function searched(args) {
  const query = args.query === undefined ? "" : args.query;
  const limit = args.limit === undefined ? 20 : args.limit;
  const offset = args.offset === undefined ? 0 : args.offset;
  if (typeof query !== "string" || query.length > 500 ||
      !Number.isInteger(limit) || limit < 1 || limit > 100 ||
      !Number.isInteger(offset) || offset < 0) throw new Error("invalid search arguments");
  const terms = normalize(query).split(/\s+/).filter(Boolean);
  const matches = PRODUCTS.filter(p => {
    const text = normalize([p.name, p.description || "", p.category || "", p.sku,
      p.origin_prefecture || "", p.caffeine_level || ""].join(" "));
    if (!terms.every(t => text.includes(t))) return false;
    if (args.category != null && normalize(args.category) !== normalize(p.category || "")) return false;
    if (args.in_stock_only === true && p.stock !== "in_stock") return false;
    if (args.gift_wrapping != null && args.gift_wrapping !== p.gift_wrapping) return false;
    if (args.origin_prefecture != null &&
        normalize(args.origin_prefecture) !== normalize(p.origin_prefecture || "")) return false;
    if (args.min_price_jpy != null && p.price_jpy < args.min_price_jpy) return false;
    if (args.max_price_jpy != null && p.price_jpy > args.max_price_jpy) return false;
    return true;
  }).sort((a,b) => a.price_jpy - b.price_jpy || a.sku.localeCompare(b.sku));
  return {products: matches.slice(offset,offset+limit), total: matches.length, offset, limit};
}
function detail(sku) { const p = LOOKUP.get(sku); return {found: !!p, product: p || null}; }
function facts(p) {
  return {product_id:p.sku,stock:p.stock,stock_quantity:p.stock_quantity,
    stock_is_live:false,is_demo:p.is_demo,source_url:p.source_url,evidence_url:p.evidence_url,
    updated_at:p.updated_at,snapshot_at:p.snapshot_at};
}
function inventory(sku) { const p=LOOKUP.get(sku); return p?{found:true,...facts(p)}:{found:false,product_id:sku}; }
function quote(sku, qty=1) {
  if (!Number.isInteger(qty) || qty<1 || qty>1000) throw new Error("quantity must be 1..1000");
  const p=LOOKUP.get(sku);
  if (!p) return {found:false,product_id:sku};
  const sub=p.price_jpy*qty;
  if (!Number.isSafeInteger(sub)) throw new Error("unsafe JPY quantity total");
  const complete=p.tax_included===true && Number.isInteger(p.shipping_jpy);
  const total=complete?sub+p.shipping_jpy:null;
  if (total!==null && !Number.isSafeInteger(total)) throw new Error("unsafe JPY total");
  const available=p.stock_quantity!=null?p.stock_quantity>=qty:(p.stock==="out_of_stock"?false:null);
  return {found:true,...facts(p),quantity:qty,currency:"JPY",unit_price_jpy:p.price_jpy,
    subtotal_jpy:sub,tax_included:p.tax_included,shipping_jpy:p.shipping_jpy,
    total_jpy:total,complete_total:complete,can_fulfill_snapshot:available,
    is_binding:false,can_purchase:false,
    shipping_basis:"catalog per-order snapshot; destination not evaluated",
    message:"Dated reference amount, not a live checkout quote or reservation."};
}
function audit() {
  const names=["tax_included","shipping_jpy","stock","evidence_url","merchant_id",
    "gift_wrapping","origin_prefecture","caffeine_level","image_url"];
  const missing={};
  for (const key of names) missing[key]=PRODUCTS.filter(p=>p[key]==null ||
    (key==="stock" && p.stock==="unknown")).map(p=>p.sku);
  return {product_count:PRODUCTS.length,demo_product_count:PRODUCTS.filter(p=>p.is_demo).length,
    stock_is_live:false,missing_fields:missing};
}
function asJsonld(sku) {
  return {found:LOOKUP.has(sku),product_id:sku,jsonld:DATA.jsonld[sku] || null};
}
function spec(name, description, properties, required=[]) {
  return {name,description,annotations:{readOnlyHint:true,destructiveHint:false,
    idempotentHint:true,openWorldHint:false},inputSchema:{type:"object",properties,required,
    additionalProperties:false}};
}
const textField={type:"string"};
const TOOLS=[
  spec("about_miseport","Describe this read-only merchant product catalog.",{},[]),
  spec("search_products","Search published merchant catalog snapshots; no live availability.",
    {query:textField,limit:{type:"integer",minimum:1,maximum:100},
     offset:{type:"integer",minimum:0},category:textField,
     in_stock_only:{type:"boolean"},gift_wrapping:{type:"boolean"},
     origin_prefecture:textField,min_price_jpy:{type:"integer",minimum:0},
     max_price_jpy:{type:"integer",minimum:0}}),
  spec("get_product","Read product detail and source timestamp by SKU.",{sku:textField},["sku"]),
  spec("check_inventory","Read dated stock record, not a live reservation.",{sku:textField},["sku"]),
  spec("get_quote","Get nonbinding JPY reference amount with unknown shipping preserved.",
    {sku:textField,quantity:{type:"integer",minimum:1,maximum:1000}},["sku"]),
  spec("audit_catalog","Review catalog missingness and limitations.",{},[]),
  spec("export_product_jsonld","Return product/offer JSON-LD snapshot.",{sku:textField},["sku"])
];
function callTool(name, args) {
  const tool=TOOLS.find(t=>t.name===name);
  if (!tool) throw new Error("unknown tool");
  if (args===null || typeof args!=="object" || Array.isArray(args)) throw new Error("bad arguments");
  if (Object.keys(args).some(k=>!(k in tool.inputSchema.properties))) throw new Error("unknown argument");
  for (const key of tool.inputSchema.required) {
    if (typeof args[key]!=="string") throw new Error("missing required string argument");
  }
  if (name==="about_miseport") return {name:"MisePort merchant read-only catalog",
    demo_only:DATA.demo_only,products:PRODUCTS.length,snapshot_at:DATA.snapshot_at,
    live_stock:false,checkout:false};
  if (name==="search_products") return searched(args);
  if (name==="get_product") return detail(args.sku);
  if (name==="check_inventory") return inventory(args.sku);
  if (name==="get_quote") return quote(args.sku,args.quantity===undefined?1:args.quantity);
  if (name==="audit_catalog") return audit();
  if (name==="export_product_jsonld") return asJsonld(args.sku);
  throw new Error("unsupported tool");
}
function rpc(id, result) { return {jsonrpc:"2.0",id,result}; }
function rpcError(id, code, message) {return {jsonrpc:"2.0",id,error:{code,message}};}
async function handleRpc(request, origin) {
  const ct=request.headers.get("content-type") || "";
  const accept=request.headers.get("accept") || "";
  if (!ct.includes("application/json") || !accept.includes("application/json") ||
      !accept.includes("text/event-stream")) return reply({error:"MCP headers required"},406,origin);
  const length=Number(request.headers.get("content-length") || "0");
  if (!Number.isFinite(length) || length>LIMIT_BYTES) return reply({error:"request too large"},413,origin);
  const bytes=await request.arrayBuffer();
  if (bytes.byteLength>LIMIT_BYTES) return reply({error:"request too large"},413,origin);
  let msg;
  try {msg=JSON.parse(new TextDecoder().decode(bytes));}
  catch (_) {return reply(rpcError(null,-32700,"parse error"),400,origin);}
  if (!msg || msg.jsonrpc!=="2.0" || typeof msg.method!=="string") {
    return reply(rpcError(null,-32600,"invalid request"),400,origin);
  }
  if (msg.id===undefined) return new Response(null,{status:202});
  if (msg.method==="initialize") return reply(rpc(msg.id,{protocolVersion:"2025-11-25",
    capabilities:{tools:{listChanged:false}},serverInfo:{name:"MisePort Merchant",version:"0.1"}}),200,origin);
  if (msg.method==="ping") return reply(rpc(msg.id,{}),200,origin);
  if (msg.method==="tools/list") return reply(rpc(msg.id,{tools:TOOLS}),200,origin);
  if (msg.method==="tools/call") {
    try {
      const value=callTool(msg.params?.name,msg.params?.arguments||{});
      return reply(rpc(msg.id,{content:[{type:"text",text:JSON.stringify(value)}],
        structuredContent:value,isError:false}),200,origin);
    } catch (_) {
      return reply(rpc(msg.id,{content:[{type:"text",text:"Invalid tool or arguments"}],
        isError:true}),200,origin);
    }
  }
  return reply(rpcError(msg.id,-32601,"method not found"),200,origin);
}
export default {
  async fetch(request, env, ctx) {
    let url;
    try {url=new URL(request.url);} catch (_) {return reply({error:"bad url"},400);}
    if (url.protocol!=="https:" || url.host!==HOST) return reply({error:"host not allowed"},403);
    const origin=request.headers.get("origin");
    if (origin && origin!==ORIGIN && origin!=="https://muse.ai") return reply({error:"origin not allowed"},403);
    if (request.method==="OPTIONS") return new Response(null,{status:204,headers:{
      "Access-Control-Allow-Origin":origin||ORIGIN,
      "Access-Control-Allow-Methods":"GET, POST, OPTIONS",
      "Access-Control-Allow-Headers":"Content-Type, Accept, MCP-Protocol-Version",
      "Vary":"Origin"}});
    if (url.pathname==="/mcp") {
      if (request.method!=="POST") return reply({error:"method not allowed"},405,origin);
      return handleRpc(request,origin);
    }
    if (request.method!=="GET") return reply({error:"read-only service"},405,origin);
    if (url.pathname==="/healthz") return reply({ok:true,read_only:true,
      demo_only:DATA.demo_only,product_count:PRODUCTS.length},200,origin);
    if (url.pathname==="/api/products") {
      try {return reply(searched({query:url.searchParams.get("query")||""}),200,origin);}
      catch (_) {return reply({error:"bad query"},400,origin);}
    }
    const match=/^\/api\/products\/([^/]+)(\/jsonld)?$/.exec(url.pathname);
    if (match) {
      let sku;
      try {sku=decodeURIComponent(match[1]);} catch (_) {return reply({error:"bad SKU"},400,origin);}
      const result=match[2]?asJsonld(sku):detail(sku);
      return reply(result,result.found?200:404,origin);
    }
    if (env?.ASSETS && ["/","/index.html","/catalog.json","/manifest.json",
      "/robots.txt","/sitemap.xml"].includes(url.pathname)) {
      return env.ASSETS.fetch(request);
    }
    return reply({error:"not found"},404,origin);
  }
};
