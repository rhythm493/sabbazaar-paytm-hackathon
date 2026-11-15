# SabBazaar — One AI Teammate for Every Marketplace

**Paytm Build for India AI Hackathon · Track 3: Autonomous AI Teammates**

Team Big Ben · Harsimar, Kedar, Rythm

---

## 1 · Title

**SabBazaar**
*One AI teammate that takes an offline shop online on every marketplace, and runs it there.*

---

## 2 · An everyday scene

*Illustrative example.*

Meena runs a saree shop on Laxmi Road, Pune. Her regulars now buy online.

**Today**
400 sarees, one phone, no time. Every app wants its own forms, photos and price lists, so she never starts.

**With SabBazaar**
She photographs her racks and says “haan” on the Soundbox. By evening her shop is live on four platforms.

---

## 3 · Problem statement

**Customers have moved online. Small shops can’t follow them everywhere.**

- **60%** of Mumbai grocery stores surveyed saw sales fall as quick commerce grew
- **82%** of shoppers have moved at least a quarter of their grocery spend to apps
- **1 week+** to list on several marketplaces, each with its own catalogue format

**Every platform is separate**
Each has its own forms, photo rules and dashboard.

**Each AI helps only itself**
Amazon’s and Meesho’s assistants only list you on their own platform.

**Running it is the hard part**
Stock, prices and buyer questions must stay in sync everywhere.

*Sources: JP Morgan survey (Business Standard); Datum Intelligence; Vinculum marketplace guide (2026)*

---

## 4 · Proposed solution

**One teammate takes the shop online everywhere, then keeps it running.**

1. **Snap** — Owner photographs racks or bills and talks in Hindi or Marathi.
2. **Catalogue** — Builds titles, photos and prices, guided by what actually sells in the shop’s Paytm data.
3. **Paperwork** — Checks PAN, GST and bank details; flags gaps and guides the fix.
4. **List everywhere** — Publishes once to ONDC, Meesho, Amazon and Google Maps in each one’s format.
5. **Sell & answer** — Replies to buyer questions and brings every order into one inbox and onto the Soundbox.
6. **Sync & settle** — Updates stock everywhere after each sale and reconciles payouts into Paytm.

> Owner stays in charge: returns, disputes, big price changes and legal paperwork go to the owner, with the details ready.

---

## 5 · How it acts safely

**Does the routine work on its own, asks before anything that costs money.**

| Action | Who decides |
|---|---|
| Draft listings | AI; owner approves first batch |
| Answer buyer questions | AI, automatically |
| Update stock after a sale | AI, automatically |
| Change a price | AI within ±[__]%; owner beyond |
| Accept a return or refund | Owner only |

**Guardrails**

- Owner’s consent before listing
- No fake reviews or claims
- Every action logged and undoable
- Pauses a listing when stock is unsure
- Follows each platform’s rules

---

## 6 · Technology stack

**Specialist agents behind one voice the owner already trusts.**

| Layer | Details |
|---|---|
| **Channels** | Paytm AI Soundbox voice, Paytm for Business app, WhatsApp; Sarvam AI speech in Indian languages |
| **Vision** | Recognises products from rack photos and bills; cleans up images to each platform’s rules |
| **Agent brain** | LLM planner directing Cataloguer, Lister, Order Desk and Stock Keeper agents (LangGraph) |
| **Integrations** | ONDC seller protocol, marketplace seller APIs, Google Business Profile |
| **Data** | Paytm sales history for prices and best-sellers; one master catalogue in PostgreSQL |
| **Prototype build** | Python FastAPI, React web app, sample shop data for the demo |

*In the prototype, marketplace connections are simulated; no live Paytm production data is used.*

---

## 7 · Unique selling proposition

**Why SabBazaar, and why it belongs inside Paytm.**

- **Neutral: every marketplace, one teammate** — Amazon’s or Meesho’s AI lists you only on their own platform; SabBazaar lists you on all of them.
- **Starts from real sales** — Paytm already sees what the shop sells and at what price, so the catalogue starts with proven items.
- **Lives on the counter** — Runs through the Soundbox and app the owner already uses, in their language: no new dashboard.
- **Runs the shop, not just the setup** — Keeps stock, prices and buyer replies in sync every day: the part listing tools leave to the owner.

**Why not WhatsApp?** WhatsApp’s business AI answers chats for one shop on one app. SabBazaar puts the shop on every marketplace and keeps them in sync.

---

## 8 · Impact & benefits

**More customers for the shop, more merchants online for India.**

**For shop owners**
- Buyers beyond their street
- Online in a day, not weeks
- Less reliance on one platform
- Hours saved every week

**For Paytm**
- More merchants on ONDC
- More sellers inside the Paytm app
- Online sales data for lending
- Merchants who stay longer

**For India**
- Supports ONDC’s goal of small-seller inclusion
- Local shops compete with apps

Built on open rails: one ONDC listing is visible across many buyer apps, including Paytm’s.

**Pilot goals:** shop live within [__] hours; [__]% of pilot shops get an online order in 30 days.

*Source: ONDC network guides (PhonePe Business, 2026)*

---

## 9 · Business model

**Free to start, earns as the shop sells.**

- **Subscription** — SabBazaar plan on the Soundbox. First listings free; ₹[__] a month for multi-marketplace sync and the order inbox.
- **Per order** — ONDC seller-app fee. Paytm acts as the shop’s ONDC seller app and earns [__]% on each order it handles.
- **Lending** — Stock loans from online sales. Online and counter sales together show demand, so Paytm can offer working-capital loans for stock.
- **Partnerships** — Government onboarding programmes. Work with schemes such as the MSME ministry’s TEAM scheme that fund small-seller onboarding.

---

## 10 · Roadmap & closing

**Every shop in India deserves to be in every market. SabBazaar takes it there and keeps it running.**

- **Phase 1** — Pilot with [__] Pune shops on ONDC and Google Maps
- **Phase 2** — Add Meesho and Amazon, with stock sync across all
- **Phase 3** — Delivery partners and stock loans built in

**Thank you · Team Big Ben · Harsimar, Kedar, Rythm**

---

## Open placeholders in the deck

These `[__]` values are undecided and will matter for the build/demo:

- Price-change autonomy threshold (slide 5): AI within ±[__]%
- Business model numbers (slide 9): ₹[__]/month subscription; [__]% ONDC seller-app fee
- Pilot goals (slide 8): live within [__] hours; [__]% of pilot shops get an online order in 30 days
- Phase 1 scope (slide 10): [__] Pune shops
