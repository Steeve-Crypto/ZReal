# Zcash/ZSA Testnet Setup

ZReal requires external Zcash/ZSA infrastructure for real tokenization.

## Required

1. A Zcash testnet node or service endpoint.
2. RPC credentials, exposed as either:

```env
ZCASH_RPC_URL=http://rpcuser:rpcpassword@127.0.0.1:18232
```

or:

```env
ZCASHRPC_USER=rpcuser
ZCASHRPC_PASSWORD=rpcpassword
ZCASHRPC_HOST=127.0.0.1
ZCASHRPC_PORT=18232
```

3. A ZSA-capable issuance tool.
4. A command template that prints JSON with real issuance identifiers:

```env
ZCASH_TX_TOOL_PATH=/path/to/zcash_tx_tool
ZCASH_ZSA_ISSUE_COMMAND={tool} create-zsa-issuance --from {issuer_zaddr} --asset-symbol {asset_symbol} --total-shares {total_shares} --network {network}
ZCASH_ZSA_STATUS_COMMAND={tool} status --operation-id {operation_id} --network {network}
```

Required ZReal configuration:

- `ZSA_ISSUANCE_BACKEND=zcash_tx_tool`
- `ZCASH_NETWORK`
- `ZCASH_RPC_URL` or the complete `ZCASHRPC_USER`, `ZCASHRPC_PASSWORD`, `ZCASHRPC_HOST`, `ZCASHRPC_PORT` set
- `ZCASH_TX_TOOL_PATH` or `zcash_tx_tool` available on `PATH`
- `ZCASH_ZSA_ISSUE_COMMAND`
- `ZCASH_ZSA_STATUS_COMMAND`

Optional ZReal configuration:

- `REQUIRE_ACTIVE_SUBSCRIPTION_FOR_ZSA=1` to require issuer billing before tokenization
- `{metadata_json}` in `ZCASH_ZSA_ISSUE_COMMAND` if the external tool expects metadata as an argument

Expected issuance output:

```json
{
  "status": "broadcast",
  "operation_id": "real-operation-id",
  "txid": "real-transaction-id",
  "asset_id": "real-asset-id"
}
```

ZReal passes safe operation metadata through the `ZREAL_ZSA_METADATA_JSON` environment variable. It contains document hashes and selected structured fields, not raw legal text. If your tool requires metadata as an argument, add `{metadata_json}` to `ZCASH_ZSA_ISSUE_COMMAND`.

If your tool uses different flags, update the command templates. ZReal supplies these placeholders:

- `{tool}`
- `{issuer_zaddr}`
- `{asset_symbol}`
- `{total_shares}`
- `{network}`
- `{operation_id}` for status refresh
- `{metadata_json}` for compact safe metadata JSON

## What ZReal Stores

- operation ID
- transaction ID
- asset ID
- status
- backend response
- error message if the call fails

ZReal must not store private spending keys.

## Current Lifecycle And Readiness

The current property lifecycle is:

`draft -> documents_uploaded -> ready_for_review -> ready_for_tokenization -> tokenization_pending -> tokenized -> active`

`suspended` and `archived` are terminal/control states for operational handling.

Readiness blocks tokenization unless:

- at least one completed document with a SHA-256 hash exists
- estimated value is present
- total shares is valid
- the owner has issuer role
- the requester owns the property
- ZSA backend configuration is ready

Missing or invalid ZSA configuration blocks before a `TokenizationOperation` is created. If configuration is ready and the external tool is invoked, then tool/runtime failure is recorded as a failed operation.

## Local Verification

1. Configure the env vars above in `.env`.
2. Run `py -3 manage.py check`.
3. Run `py -3 manage.py test properties.tests.ProductApiTest`.
4. Start Django and Next.js.
5. Sign in as an issuer.
6. Create a property using real information.
7. Upload a real property/legal document.
8. Confirm the property detail page shows `Ready for tokenization`.
9. Submit tokenization with a real shielded issuer address.
10. Open the tokenization operation detail page.
11. Refresh operation status until the configured backend reports `confirmed` or a safe error.

Mocked tests prove app-side behavior only. They do not prove native ZSA issuance works. Real beta readiness requires at least one successful testnet issuance through your configured ZSA-capable tool.

## Remaining Beta Blockers

- real ZSA RPC/tool configuration
- one successful end-to-end testnet issuance
- real investor purchase/settlement flow
- human review workflow
- production deployment, HTTPS, secrets, media storage, logging, and backups
