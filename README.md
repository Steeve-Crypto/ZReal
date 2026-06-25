# ZReal

ZReal is a privacy-oriented real estate tokenization system.

The intended architecture is:
- Django: backend, admin, database, auth, property/document/tokenization logic, ZSA integration boundary, tests
- Next.js: product frontend for issuers and investors

The app currently supports:
- user signup/login through django-allauth
- role selection: investor or issuer
- staff-only local setup/status checklist
- issuer-facing ZSA configuration validation
- issuer dashboards backed by real database values
- issuer property create/edit flows
- document upload and text extraction for issuer-owned properties
- tokenization operation detail/history pages
- investor browse page that shows only tokenized or active properties
- property map using stored latitude/longitude; public/investor views show tokenized or active properties, issuers also see their own drafts
- auditable ZSA tokenization attempts
- safe document-to-tokenization metadata using document hashes, document types, timestamps, and selected structured fields
- Stripe checkout integration when Stripe keys are configured
- JSON API endpoints for the product frontend
- a separate Next.js frontend scaffold in `frontend/`

ZReal does **not** fake tokenization. ZSA issuance only runs when you configure a real external ZSA-capable backend/tool. If that backend is missing, the app records a failed tokenization attempt with a clear configuration error.

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
3. Sign in through Django allauth at `http://127.0.0.1:8000/accounts/login/`.
4. The frontend API client calls Django with `credentials: "include"`.

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
- `GET /api/me/`
- `GET/PATCH /api/role/`
- `GET /api/dashboard/issuer/`
- `GET /api/dashboard/investor/`
- `GET /api/setup/status/` staff only
- `GET /api/properties/`
- `GET /api/properties/browse/`
- `POST /api/properties/new/`
- `GET /api/properties/<id>/`
- `PATCH/PUT /api/properties/<id>/edit/`
- `GET /api/properties/<id>/documents/`
- `POST /api/properties/<id>/documents/upload/`
- `GET /api/zsa/config/`
- `POST /api/properties/<id>/tokenize/`
- `GET /api/tokenization/operations/<id>/`
- `POST /api/tokenization/operations/<id>/refresh/`

The API returns real database-backed data only. Empty states are represented as empty arrays or `null` values.

## Tokenization Flow

1. User signs in.
2. User chooses the issuer role.
3. Issuer creates a property.
4. Issuer uploads legal/property documents.
5. ZReal stores the document and its SHA-256 hash, then extracts local structured metadata.
6. Issuer checks ZSA readiness on the dashboard or via `/zcash/zsa-config/validate/`.
7. If configuration is missing, ZReal blocks blind issuance in the dashboard and reports the missing values.
8. If configuration is ready, issuer enters a shielded issuer address and submits `Issue ZSA`.
9. ZReal creates a `TokenizationOperation` audit record.
10. ZReal attaches safe metadata: property ID, asset symbol, total shares, document types, document SHA-256 hashes, timestamps, and selected non-text extracted fields.
11. ZReal calls the configured ZSA backend command.
12. ZReal stores real returned `operation_id`, `txid`, `asset_id`, status, and errors.
13. Pending operations can be refreshed from the dashboard or operation detail page.

No private keys should be stored in ZReal. The external ZSA backend/tool is responsible for signing and broadcasting.

## Manual QA Script

1. Install dependencies: `py -3 -m pip install -r requirements.txt`.
2. Run migrations: `py -3 manage.py migrate`.
3. Start the server: `py -3 manage.py runserver 127.0.0.1:8000`.
4. Open `http://127.0.0.1:8000/accounts/signup/`.
5. Create an account with your own email and password.
6. Choose the issuer role at `http://127.0.0.1:8000/profile/role/`.
7. Open `http://127.0.0.1:8000/issuer/dashboard/`.
8. Create a property using real property information you are authorized to use.
9. Upload a real legal/property document through Legal Shield.
10. Confirm the upload response shows extracted safe fields and the document hash exists in Django admin or the database.
11. Attempt tokenization only after the dashboard reports ZSA readiness. Without config, the UI should explain the missing values instead of offering a blind issue button.
12. Open `http://127.0.0.1:8000/zcash/zsa-config/validate/` while logged in as issuer to inspect structured validation JSON.
13. Configure the ZSA environment variables listed above, restart the server, and re-open the validation endpoint.
14. Submit tokenization with a real issuer shielded address.
15. Open the tokenization operation detail link from the dashboard.
16. Refresh status from the operation detail page.
17. Confirm operation history shows real operation IDs, txids, asset IDs, statuses, timestamps, and any backend errors.
18. Create or log into an investor account and open `http://127.0.0.1:8000/properties/browse/`.
19. Confirm no draft properties are shown. If no real tokenized properties exist, the page should say: `No tokenized properties are available yet.`

For the staff-only local setup checklist, create or use a staff/superuser account and open:

```text
http://127.0.0.1:8000/setup/status/
```

## Implemented

- Django app boot and routing
- SQLite local development
- auth and role selection
- issuer property management
- ownership-protected document upload
- PDF/image text extraction path
- local setup/status checklist
- ZSA configuration validation endpoint
- database-backed dashboards
- frontend API layer
- Next.js product frontend scaffold
- investor tokenized-property browsing
- property map
- tokenization audit model
- tokenization operation detail/status refresh pages
- real external ZSA tool integration boundary
- tests for document upload, tokenization success/failure/status refresh, permissions, investor holdings, and Stripe missing configuration

## Pending

- a real native ZSA backend/tool must be supplied and configured
- richer investor purchase flow
- real rental/dividend distribution model
- production hardening for KYC/AML and securities compliance
- viewing keys are not currently stored; add encrypted custody/read-only access if that feature is needed
