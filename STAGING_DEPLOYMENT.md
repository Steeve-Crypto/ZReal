# ZReal Staging Deployment

Staging requires the same configuration as local development plus a real database, HTTPS, media storage, and optional ZSA/Stripe integrations.

## Minimum

- Python dependencies installed
- `SECRET_KEY`
- `DEBUG=0`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- static/media storage plan

## Optional Integrations

- `ZCASH_RPC_URL`
- `ZCASH_TX_TOOL_PATH`
- `ZCASH_ZSA_ISSUE_COMMAND`
- `ZCASH_ZSA_STATUS_COMMAND`
- `STRIPE_SECRET_KEY`
- `STRIPE_ISSUER_PRICE_ID`
- `DJSTRIPE_WEBHOOK_SECRET`
- `PROPERTY_DATA_PROVIDER`
- `PROPERTY_DATA_ENABLE_LIVE_CALLS`
- provider-specific property data API keys if live enrichment is enabled: `REGRID_API_KEY`, `OPENCAGE_API_KEY`, `GOOGLE_GEOCODING_API_KEY`, or the `PROPERTY_DATA_*` aliases

## Deploy

```bash
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn zreal.wsgi:application --bind 0.0.0.0:8000
```

## Staging Verification

- create an account
- choose issuer role
- create a property
- upload a document
- attempt ZSA issuance with the configured testnet tool
- verify success/failure is recorded in `TokenizationOperation`

Dividend payouts are not implemented yet and should not be staged as a working feature.
