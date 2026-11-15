# Web Application (Merchant Dashboard)

React 19 + TypeScript + Vite + TailwindCSS merchant frontend for SabBazaar.

## Features

- **Catalogue Management**: Upload product photos/bills, generate AI drafts, view missing field warnings, edit attributes, and approve items.
- **Channel Publishing**: Multi-channel selector (Shopify active; ONDC & Meesho upcoming) with status monitoring and retry triggers.
- **Audit Activity Feed**: Chronological log of all events and approvals with relative time formatting.
- **Price Threshold Safeguards**: Configurable ±% threshold slider to require human approval for high variance price modifications.
- **Demo / Offline Mode**: Instant offline simulation switch with pre-seeded fixtures for reliable judging without external dependencies.

## Running Locally

```bash
# Navigate to the web app
cd apps/web

# Install dependencies
npm install

# Start Vite development server (runs on http://localhost:3000)
npm run dev

# Type check
npx tsc --noEmit

# Production build
npm run build
```

The Vite dev server proxies `/v1` and `/health` requests to `http://localhost:8000` (FastAPI backend).
