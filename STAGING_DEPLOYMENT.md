# ZReal Staging Deployment Guide (Zcash Testnet)

## Prerequisites
- Zcash testnet node running (or use a reliable testnet provider)
- Funded testnet shielded address for payouts
- PostgreSQL + PostGIS
- Redis
- Docker / Kubernetes cluster (recommended)

## 1. Environment Setup

```bash
# Clone and enter project
git clone <your-repo>
cd zreal

# Copy environment
cp .env.example .env

# Edit .env with testnet values
ZCASHTESTNET_RPC_URL=http://your-testnet-node:18232
ZCASHTESTNET_RPC_USER=youruser
ZCASHTESTNET_RPC_PASSWORD=yourpass
VALUATION_API_KEY=optional
```

## 2. Database & Migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

## 3. Run with Docker Compose (Recommended for Staging)

```bash
docker-compose -f docker-compose.yml up -d --build
```

Key services:
- `web` → Django + Gunicorn
- `celery` → Background tasks (dividends, monitoring, re-valuation)
- `redis`
- `db` (PostGIS)

## 4. Zcash Testnet Configuration

- Use `zcash.conf` with `testnet=1`
- Ensure `rpcallowip` and authentication are set
- Fund a shielded address for dividend testing:
  ```bash
  zcash-cli z_getnewaddress
  zcash-cli z_shieldcoinbase "*" your_zaddr
  ```

## 5. Run Dividend Payouts on Testnet

```bash
# Manual trigger
python manage.py process_dividends --property-id 1

# Or via Celery
python manage.py process_dividends --async
```

## 6. Monitoring on Staging

- Access Grafana at `http://your-staging:3000`
- Check Falco alerts
- Monitor Celery flower (if enabled)

## 7. Testnet Best Practices

- Use small amounts for testing
- Monitor transaction confirmations
- Test failure scenarios (invalid address, insufficient funds)
- Keep testnet addresses documented

**Next Step after Staging**: Full security audit + load testing before mainnet.
