# ZReal Kubernetes Secrets

Do not commit a Kubernetes Secret manifest with live credentials or example credential values.

Create the `zreal-secrets` Secret in the `zreal` namespace through your secret manager, External Secrets Operator, sealed secrets workflow, or a local `kubectl create secret` command.

Required keys:

- `SECRET_KEY`
- `DATABASE_URL`
- `ZCASH_RPC_URL` or the complete `ZCASHRPC_USER`, `ZCASHRPC_PASSWORD`, `ZCASHRPC_HOST`, `ZCASHRPC_PORT` set
- `ZCASH_TX_TOOL_PATH`

Optional keys:

- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_ISSUER_PRICE_ID`
- `DJSTRIPE_WEBHOOK_SECRET`
- `PROPERTY_DATA_API_KEY`
- `PROPERTY_DATA_REGRID_API_KEY`
- `PROPERTY_DATA_OPENCAGE_API_KEY`
- `PROPERTY_DATA_GOOGLE_API_KEY`

Example command shape, with values supplied from your shell or secret manager:

```bash
kubectl create secret generic zreal-secrets \
  --namespace zreal \
  --from-literal SECRET_KEY="$SECRET_KEY" \
  --from-literal DATABASE_URL="$DATABASE_URL" \
  --from-literal ZCASH_RPC_URL="$ZCASH_RPC_URL" \
  --from-literal ZCASH_TX_TOOL_PATH="$ZCASH_TX_TOOL_PATH"
```
