import { useEffect, useMemo, useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type Product = {
  id: number;
  title: string;
  description: string;
  vendor: string;
  product_type: string;
  tags: string[];
  handle: string;
  status: string;
  price_inr: string | number;
  external_product_id?: string | null;
  admin_url?: string | null;
  variants: { sku: string; price_inr: string | number }[];
};

type Activity = {
  id: number;
  event_type: string;
  message: string;
  created_at: string;
};

const fixture = {
  title: 'Kanjivaram Silk Saree',
  description: '<p>Handwoven Kanjivaram silk saree with a rich zari border.</p>',
  vendor: "Meena's Sarees",
  product_type: 'Sarees',
  tags: ['saree', 'kanjivaram', 'silk'],
  price_inr: 8999,
  sku: 'SBZ-SARI-0001',
  evidence: { source: 'demo fixture' },
  confidence: 0.95,
  missing_fields: [],
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export default function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const selected = useMemo(() => products.find((p) => p.id === selectedId) ?? products[0] ?? null, [products, selectedId]);

  async function refresh() {
    const [nextProducts, nextActivity] = await Promise.all([
      api<Product[]>('/v1/products'),
      api<Activity[]>('/v1/activity'),
    ]);
    setProducts(nextProducts);
    setSelectedId((current) => current && nextProducts.some((p) => p.id === current) ? current : nextProducts[0]?.id ?? null);
    setActivity(nextActivity);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function seedFixture() {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const product = await api<Product>('/v1/products', { method: 'POST', body: JSON.stringify(fixture) });
      setNotice(`Draft #${product.id} created from the demo fixture.`);
      setSelectedId(product.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the draft.');
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      await api(`/v1/products/${selected.id}/approve`, { method: 'POST' });
      setNotice('Publication approved. SabBazaar can now request Shopify to create a draft product.');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Approval failed.');
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      const result = await api<{ admin_url?: string; reused?: boolean }>(`/v1/products/${selected.id}/publish`, { method: 'POST' });
      setNotice(result.reused ? 'Already in Shopify; existing draft returned.' : 'Shopify draft product created. Open it in the Shopify admin.');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Shopify publication failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Origin: Paytm Build for India AI Hackathon · Track 3</p>
          <h1>SabBazaar</h1>
          <p className="subtitle">One AI teammate for catalogue creation and safe Shopify publication.</p>
        </div>
        <span className="local-pill">Local development</span>
      </header>

      {(error || notice) && <div role="status" className={error ? 'alert error' : 'alert'}>{error || notice}</div>}

      <section className="grid">
        <aside className="panel catalog-panel">
          <div className="panel-head">
            <div><p className="eyebrow">Catalogue</p><h2>Product drafts</h2></div>
            <button onClick={seedFixture} disabled={busy}>+ Demo fixture</button>
          </div>
          <div className="product-list">
            {products.length === 0 && <p className="empty">No drafts yet. Create one from the demo fixture.</p>}
            {products.map((product) => (
              <button key={product.id} className={`product-row ${selected?.id === product.id ? 'selected' : ''}`} onClick={() => setSelectedId(product.id)}>
                <strong>{product.title}</strong>
                <span>₹{Number(product.price_inr).toLocaleString('en-IN')} · {product.status}</span>
              </button>
            ))}
          </div>
        </aside>

        <section className="panel detail-panel">
          {selected ? (
            <>
              <div className="panel-head">
                <div><p className="eyebrow">Review before approval</p><h2>{selected.title}</h2></div>
                <span className={`status ${selected.status}`}>{selected.status.replaceAll('_', ' ')}</span>
              </div>
              <div className="editor">
                <label>Title<input value={selected.title} readOnly /></label>
                <label>Description<textarea value={selected.description.replace(/<[^>]+>/g, '')} readOnly rows={4} /></label>
                <div className="field-grid">
                  <label>Price (₹)<input value={String(selected.price_inr)} readOnly /></label>
                  <label>Vendor<input value={selected.vendor} readOnly /></label>
                  <label>Type<input value={selected.product_type} readOnly /></label>
                  <label>SKU<input value={selected.variants[0]?.sku ?? ''} readOnly /></label>
                </div>
                <p className="tags">{selected.tags.map((tag) => <span key={tag}>{tag}</span>)}</p>
                <div className="actions">
                  <button className="secondary" onClick={approve} disabled={busy || selected.status === 'shopify_draft'}>Approve for Shopify</button>
                  <button onClick={publish} disabled={busy || selected.status === 'shopify_draft'}>Create Shopify draft</button>
                </div>
                {selected.admin_url && <a className="shopify-link" href={selected.admin_url} target="_blank" rel="noreferrer">Open in Shopify admin →</a>}
              </div>
            </>
          ) : (
            <div className="empty-state"><h2>Ready when you are</h2><p>Create the demo catalogue draft, review it, approve it, then create a draft product in your Shopify development store.</p></div>
          )}
        </section>

        <aside className="panel activity-panel">
          <div className="panel-head"><div><p className="eyebrow">Audit trail</p><h2>Activity</h2></div></div>
          <ol className="timeline">
            {activity.length === 0 && <li><span>No events yet.</span></li>}
            {activity.map((event) => (
              <li key={event.id}>
                <time>{new Date(event.created_at).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })}</time>
                <p>{event.message}</p>
                <small>{event.event_type}</small>
              </li>
            ))}
          </ol>
        </aside>
      </section>
    </main>
  );
}
