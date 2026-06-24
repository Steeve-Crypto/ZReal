# Zcash Testnet Setup for ZReal Development

## 1. Install & Run zcashd on Testnet

### Recommended: Use official binaries or Docker

**Option A: Binary (Linux/macOS)**
```bash
# Download latest zcashd for your OS from https://z.cash/download/
# Or build from source

# Run on testnet
./zcashd -testnet \
  -rpcuser=zrealuser \
  -rpcpassword=supersecurepassword123 \
  -rpcallowip=127.0.0.1 \
  -rpcport=18232 \
  -txindex=1 \
  -daemon
```

**Option B: Docker (easiest for development)**
```yaml
# docker-compose.zcash.yml
version: '3.8'
services:
  zcashd-testnet:
    image: electriccoinco/zcashd:latest
    command: >
      zcashd -testnet
      -rpcuser=zrealuser
      -rpcpassword=supersecurepassword123
      -rpcallowip=0.0.0.0
      -rpcport=18232
      -txindex=1
    ports:
      - "18232:18232"
    volumes:
      - ./zcash-data:/home/zcash/.zcash
```

Run: `docker-compose -f docker-compose.zcash.yml up -d`

## 2. Generate Shielded Addresses (z-addresses)

After zcashd is synced on testnet:

```bash
# Get new shielded address
./zcash-cli -testnet z_getnewaddress

# Example output: ztestsapling1... (or zregtest... on regtest)

# Get transparent address if needed
./zcash-cli -testnet getnewaddress
```

## 3. Fund the Address (Testnet Faucet)

Use public Zcash testnet faucets:
- https://faucet.zecpages.com/
- Or community faucets in Zcash Discord/Telegram

Send test ZEC to your z-address.

## 4. Update ZReal Settings

In `zreal/settings.py` or environment:

```python
ZCASH_RPC_URL = "http://zrealuser:supersecurepassword123@localhost:18232"
ZCASH_NETWORK = "testnet"
```

## 5. Test the Flows in ZReal

### A. Generate Sapling Address (via ZReal)
```bash
curl "http://127.0.0.1:8000/zcash/generate-sapling-address/"
```

### B. ZSA Issuance (Sapling)
```bash
curl -X POST "http://127.0.0.1:8000/properties/1/issue-zsa/?issuer_zaddr=ztestsapling1..." 
```

### C. Shielded Distribution (Rental Income)
```bash
curl -X POST "http://127.0.0.1:8000/properties/1/distribute/" \
  -d "from_zaddr=ztestsapling1..." \
  -d 'recipients=[{"zaddr":"ztestsapling2...", "amount":0.01, "investor_id":5}]' \
  -d "period=2026-Q2"
```

### D. Useful Sapling RPC Commands (via zcash-cli)
```bash
# Check Sapling balance
./zcash-cli -testnet z_getbalance ztestsapling1...

# List unspent Sapling notes
./zcash-cli -testnet z_listunspent 1

# Export viewing key (for read-only access)
./zcash-cli -testnet z_exportviewingkey ztestsapling1...
```

## 6. Verify Transactions

```bash
# Check tx in zcashd
./zcash-cli -testnet getrawtransaction <txid> 1

# Or use block explorer: https://explorer.testnet.z.cash/
```

## Important Notes for 2026

- Zcash Shielded Assets (ZSA) are in active development (ZIP 227 / NU7).
- The current implementation uses **rich memos on shielded transactions** as the on-chain record.
- When native ZSA mint/burn RPCs become available, update `zcash_client.py` — the interface is designed to be easily swapped.
- Always use **fully shielded** transactions (`AllowFullyShielded`) for maximum privacy.

## Security
- Never use these RPC credentials in production.
- For production: Run zcashd behind firewall + use authenticated RPC only from your Django server.
- Consider light clients or viewing keys for balance queries in future versions.

You're now ready to test real shielded ZSA issuance + distribution flows on Zcash testnet.
