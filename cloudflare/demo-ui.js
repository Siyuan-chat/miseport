const form = document.getElementById('demo-form');
const results = document.getElementById('demo-results');
const status = document.getElementById('demo-status');
form.addEventListener('submit', async event => {
  event.preventDefault(); results.replaceChildren(); status.textContent = '検索中 / Searching…';
  const controller = new AbortController(); const timer = setTimeout(()=>controller.abort(), 10000);
  try {
    const response = await fetch('/api/products?query=' + encodeURIComponent(form.elements.query.value), {signal: controller.signal});
    if (!response.ok) throw new Error('Service returned HTTP ' + response.status);
    const data = await response.json();
    status.textContent = `${data.total} 件 / results · DEMO`;
    for (const product of data.products) {
      const card = document.createElement('article'); card.className = 'card';
      const title = document.createElement('h3'); title.textContent = product.name; card.append(title);
      const price = document.createElement('p'); price.textContent = '¥' + product.price_jpy.toLocaleString('ja-JP') + ' JPY · DEMO'; card.append(price);
      const detail = document.createElement('dl');
      for (const [name, value] of [['Stock / 在庫', product.stock], ['Tax included / 税込', product.tax_included ?? 'unknown / 不明'], ['Shipping / 送料', product.shipping_jpy === null ? 'unknown / 不明' : '¥' + product.shipping_jpy], ['Updated / 更新', product.updated_at], ['Source / 出典', product.source_url]]) {
        const term = document.createElement('dt'); term.textContent = name;
        const description = document.createElement('dd'); description.textContent = String(value); detail.append(term, description);
      }
      card.append(detail); results.append(card);
    }
  } catch (error) { status.textContent = error.name === 'AbortError' ? 'Timeout / タイムアウト' : '取得できません / Could not fetch results'; }
  finally { clearTimeout(timer); }
});
