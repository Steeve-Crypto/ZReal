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
