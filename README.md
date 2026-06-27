# ZReal

ZReal is a privacy-oriented real estate tokenization system.

The intended architecture is:
- Django: backend, admin, database, auth, property/document/tokenization logic, ZSA integration boundary, tests
- Next.js: product frontend for issuers and investors

Implemented today:
- user signup/login through django-allauth
- role selection: investor or issuer
- staff-only local setup/status checklist
- issuer-facing ZSA configuration validation
- issuer dashboards sourced from application records
- issuer property create/edit flows
- address-first property data autofill with reviewable provider provenance
- document upload and text extraction for issuer-owned properties
- tokenization operation detail/history pages
- investor browse page that shows only tokenized or active properties
- property map using stored latitude/longitude; public/investor views show tokenized or active properties, issuers also see their own drafts
- auditable ZSA tokenization attempts
- safe document-to-tokenization metadata using document hashes, document types, timestamps, and selected structured fields
- Stripe checkout integration when Stripe keys are configured
- JSON endpoints for the product frontend
- a Next.js frontend in `frontend/`

ZSA issuance only runs when you configure an external ZSA-capable tool. If required configuration is missing or invalid, tokenization is blocked before operation creation. If the configured tool runs and fails, ZReal records a failed operation with a safe error message.

## Install

```bash
py -3 -m pip install -r requirements.txt
```

Optional but recommended:

```bash
copy .env.example .env
```

Local development defaults to SQLite if `DATABASE_URL` is not set.

## Configure

Minimum local config:

```env
SECRET_KEY=change-me
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
```

For real Zcash/ZSA issuance, configure:

```env
ZCASH_NETWORK=testnet
ZCASH_RPC_URL=http://rpcuser:rpcpassword@127.0.0.1:18232
ZSA_ISSUANCE_BACKEND=zcash_tx_tool
ZCASH_TX_TOOL_PATH=C:\path\to\zcash_tx_tool.exe
ZCASH_ZSA_ISSUE_COMMAND={tool} create-zsa-issuance --from {issuer_zaddr} --asset-symbol {asset_symbol} --total-shares {total_shares} --network {network}
ZCASH_ZSA_STATUS_COMMAND={tool} status --operation-id {operation_id} --network {network}
```

The issue/status commands must print a JSON object. Issuance output must include at least one of:

```json
{
  "status": "pending|broadcast|confirmed",
  "operation_id": "...",
  "txid": "...",
  "asset_id": "..."
}
```

Safe tokenization metadata is stored with the operation and passed to the command in `ZREAL_ZSA_METADATA_JSON`. The command template may also reference `{metadata_json}` if your tool expects metadata as an argument. ZReal includes document hashes and selected structured fields, not full legal document text.

Stripe checkout is optional. Configure it only if you want billing:

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_ISSUER_PRICE_ID=price_...
DJSTRIPE_WEBHOOK_SECRET=whsec_...
REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA=0
```

Property data enrichment defaults to fixture mode for local development and CI:

```env
PROPERTY_DATA_PROVIDER=mock
PROPERTY_DATA_ENABLE_LIVE_CALLS=0
PROPERTY_DATA_API_KEY=
PROPERTY_DATA_REGRID_API_KEY=
PROPERTY_DATA_OPENCAGE_API_KEY=
PROPERTY_DATA_GOOGLE_API_KEY=
REGRID_API_KEY=
OPENCAGE_API_KEY=
GOOGLE_GEOCODING_API_KEY=
```

Supported provider modes are `mock`, `fixture`, `census`, `regrid`, `opencage`, and `google`. `mock`/`fixture` return local fixture data for tests and development checks. `census` can resolve live addresses only when `PROPERTY_DATA_ENABLE_LIVE_CALLS=1`. Regrid, OpenCage, and Google are keyed provider interfaces until live integration and licensing are approved; the shorter `REGRID_API_KEY`, `OPENCAGE_API_KEY`, and `GOOGLE_GEOCODING_API_KEY` aliases are also accepted.

## Run

Backend:

```bash
py -3 manage.py migrate
py -3 manage.py runserver 127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000/
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:3000/
```

## Test

Backend:

```bash
py -3 manage.py check
py -3 manage.py test
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

## Frontend Authentication

Local frontend development uses Django session authentication.

1. Start Django at `http://127.0.0.1:8000`.
2. Start Next.js at `http://127.0.0.1:3000`.
3. Sign in through the styled Django allauth page at `http://127.0.0.1:8000/accounts/login/`.
4. Signup, logout, password reset, and email confirmation are still handled by allauth, but use ZReal dark auth templates.
5. Redirects from the frontend can use `?next=...`; after login, allauth respects that `next` value.
6. Open `http://127.0.0.1:3000/account` after login to confirm the Next.js frontend can read the Django session.
7. The frontend API client calls Django with `credentials: "include"`.
8. Unsafe frontend requests call `GET /api/csrf/` first and send `X-CSRFToken`.

The backend permits local frontend origins through `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

Production must configure:
- real `SECRET_KEY`
- real `ALLOWED_HOSTS`
- real frontend origin in `CORS_ALLOWED_ORIGINS`
- real frontend origin in `CSRF_TRUSTED_ORIGINS`
- secure cookies/HTTPS settings

## API Endpoints

Frontend-facing API endpoints are mounted under `/api/`:

- `GET /api/health/`
- `GET /api/csrf/`
- `GET /api/me/`
- `GET/PATCH /api/role/`
- `GET /api/dashboard/issuer/`
- `GET /api/dashboard/investor/`
- `GET /api/setup/status/` staff only
- `GET /api/properties/`
- `GET /api/properties/browse/`
- `POST /api/properties/resolve-address/`
- `POST /api/properties/new/`
- `GET /api/properties/<id>/`
- `PATCH/PUT /api/properties/<id>/edit/`
- `POST /api/properties/<id>/enrich/`
- `GET /api/properties/<id>/enrichment/`
- `POST /api/properties/<id>/confirm-enrichment/`
- `GET /api/properties/<id>/documents/`
- `POST /api/properties/<id>/documents/upload/`
- `GET /api/zsa/config/`
- `POST /api/properties/<id>/tokenize/`
- `GET /api/tokenization/operations/<id>/`
- `POST /api/tokenization/operations/<id>/refresh/`

The product endpoints return persisted application data. Empty states are represented as empty arrays or `null` values.

## Tokenization Flow

1. User signs in.
2. User chooses the issuer role.
3. Issuer creates a property.
4. Issuer uploads legal/property documents.
5. ZReal stores the document and its SHA-256 hash, then extracts local structured metadata.
6. Issuer checks ZSA readiness on the dashboard or staff setup/configuration views.
7. If configuration is missing, ZReal blocks blind issuance in the dashboard and reports the missing values.
8. If configuration is ready, issuer enters a shielded issuer address and submits `Issue ZSA`.
9. ZReal creates a `TokenizationOperation` audit record.
10. ZReal attaches safe metadata: property ID, asset symbol, total shares, document types, document SHA-256 hashes, timestamps, and selected non-text extracted fields.
11. ZReal calls the configured ZSA issuance command.
12. ZReal stores real returned `operation_id`, `txid`, `asset_id`, status, and errors.
13. Pending operations can be refreshed from the dashboard or operation detail page.

No private keys should be stored in ZReal. The external ZSA-capable tool is responsible for signing and broadcasting.

## Manual QA Script

1. Install backend dependencies: `py -3 -m pip install -r requirements.txt`.
2. Run migrations: `py -3 manage.py migrate`.
3. Start Django: `py -3 manage.py runserver 127.0.0.1:8000`.
4. Install frontend dependencies: `cd frontend && npm install`.
5. Start Next.js: `npm run dev`.
6. Open `http://127.0.0.1:8000/accounts/signup/` and confirm it uses the ZReal dark auth UI.
7. Create an account with your own email and password.
8. Sign out and sign back in at `http://127.0.0.1:8000/accounts/login/?next=/profile/role/` to confirm the `next` redirect is preserved.
9. Open `http://127.0.0.1:3000/account`.
10. Confirm the frontend shows the authenticated profile.
11. Choose the issuer role in the frontend.
12. Open `http://127.0.0.1:3000/properties/new`.
13. Enter a property address, run `Autofill property details`, review the normalized address/source/confidence, then create the draft.
14. Open the created property detail page.
15. Edit the property from the frontend, run saved-property enrichment if needed, confirm autofill, and confirm the saved values reload.
16. Upload a real legal/property document from the property detail page.
17. Confirm the frontend shows document hash, processing status, and safe metadata only.
18. Inspect ZSA readiness on the property detail page.
19. Attempt tokenization with missing ZSA config and confirm the clear blocked/error state.
20. Configure the ZSA environment variables listed above if you have issuance tooling.
21. Submit tokenization with a real issuer shielded address.
22. Open the tokenization operation detail page.
23. Refresh operation status and confirm the page shows operation IDs, txids, asset IDs, timestamps, and safe errors.
24. Create or log into an investor account and open `http://127.0.0.1:3000/properties`.
25. Confirm no draft properties are shown. If no real tokenized properties exist, the page should say: `No tokenized properties are available yet.`

For the staff-only local setup checklist, create or use a staff/superuser account and open:

```text
http://127.0.0.1:8000/setup/status/
```

## Implemented

- Django app boot and routing
- SQLite local development
- auth and role selection
- issuer property management
- provider-agnostic property data enrichment foundation with fixture mode
- ownership-protected document upload
- PDF/image text extraction path
- local setup/status checklist
- ZSA configuration validation endpoint
- dashboard metrics from persisted records
- frontend API layer
- Next.js product frontend scaffold
- investor tokenized-property browsing
- property map
- tokenization audit model
- tokenization operation detail/status refresh pages
- external ZSA tool integration boundary
- tests for document upload, tokenization success/failure/status refresh, permissions, investor holdings, and Stripe missing configuration

## Pending

- a real native ZSA backend/tool must be supplied and configured
- richer investor purchase flow
- real rental/dividend distribution model
- live parcel/geocoder provider integrations beyond fixture mode
- production hardening for KYC/AML and securities compliance
- viewing keys are not currently stored; add encrypted custody/read-only access if that feature is needed

## Future Property Data Features

- Regrid live parcel API integration
- ATTOM/ICE/Cotality enrichment provider
- official county/state ArcGIS connector layer
- PostGIS parcel boundary storage
- flood/elevation/climate risk enrichment
- zoning/land-use module
- MLS/RESO listing overlay
- provider confidence scoring dashboard
- provider license/compliance registry
- background enrichment jobs
- map-based parcel confirmation
