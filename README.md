# ZReal - Zcash Real Estate RWA Tokenization Platform

**Private fractional ownership of real estate on Zcash using Shielded Assets (ZSA).**

Built with Python Django + PostGIS + Leaflet maps + Zcash RPC integration.

## Vision & Revenue Model
- **Solve**: Illiquidity + privacy issues in real estate investment.
- **How**: Issuers tokenize properties as Zcash Shielded Assets (private tokens). Investors buy fractional shares with shielded ZEC. Rental income distributed privately.
- **Revenue**: SaaS subscriptions for issuers ($199–999/mo + success fees), premium investor tools, API access, compliance add-ons.
- **Differentiation**: Full zk-privacy on Zcash vs transparent chains.

## Current Status (Advanced Production-Ready MVP)

ZReal has evolved into a **feature-rich, privacy-first real estate RWA platform** with:

### Core Features
- **Zcash Shielded Assets (ZSA)** support with `zcash_tx_tool` integration
- **Legal Shield** — Document intelligence using pdfplumber + OCR
- Automatic enrichment of ZSA metadata from uploaded legal documents
- Role-based access (Issuer vs Investor dashboards)
- Stripe subscription billing for issuers
- Premium glassmorphism UI with futuristic design
- Interactive geospatial maps (Folium + OSMnx)
- Visual timeline of documents + ZSA events per property
- One-click CSV export of Legal Shield reports
- Dynamic ZSA strategy configuration via Admin
- Management command to backfill metadata on existing properties

### Technical Foundation
- Full Docker + docker-compose setup (Web, PostgreSQL + PostGIS, Redis, Celery)
- Kubernetes manifests (Deployment, Service, Ingress, HPA, Celery, Redis)
- GitHub Actions CI/CD pipeline
- Production settings with `django-environ` + Whitenoise
- Comprehensive test suite for critical flows
- Health check endpoint ready for orchestration

## Tech Stack
- Django 5 + DRF
- PostgreSQL + PostGIS (GeoDjango)
- Leaflet.js (Google Maps alternative - free & open)
- Zcash (zcashd RPC via Python)
- Celery (future async/ZSA jobs)
- Stripe (future billing)

## Quick Start (Local)

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 15+ with PostGIS extension
- Running zcashd node (testnet recommended first) or access to RPC
- Git

### 2. Setup Database
```bash
sudo -u postgres psql
CREATE DATABASE zreal;
CREATE USER zrealuser WITH PASSWORD 'yourpassword';
ALTER ROLE zrealuser SET client_encoding TO 'utf8';
ALTER ROLE zrealuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE zrealuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE zreal TO zrealuser;
\c zreal
CREATE EXTENSION postgis;
```

### 3. Install & Run
```bash
cd /path/to/zreal
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Edit zreal/settings.py with your DB credentials and ZCASH_RPC_URL

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

python manage.py runserver
```

Visit http://127.0.0.1:8000/admin/ and http://127.0.0.1:8000/properties/map/

### 4. Zcash Setup (Testnet First)
1. Run zcashd on testnet.
2. Get RPC credentials.
3. Set in settings.py: ZCASH_RPC_URL = "http://user:pass@localhost:18232"

Example shielded tx via Django view coming soon.

## Project Structure
```
zreal/
├── zreal/                  # Project settings
├── properties/             # Core real estate models, views, maps
├── core/                   # Users, billing, common
├── zcash_integration/      # Zcash RPC client + ZSA logic
├── ai_valuation/           # ML price prediction
├── templates/              # HTML + Leaflet map
├── static/                 # CSS/JS
├── manage.py
├── requirements.txt
└── README.md
```

## Key Features Implemented in Starter
- Property model with PointField + PolygonField (PostGIS)
- Interactive property map (Leaflet + OSM)
- Basic property list/create API + views
- Zcash RPC wrapper (z_sendmany example for shielded transfers)
- Placeholder for ZSA issuance (update when full RPC available)
- Simple AI valuation endpoint stub
- Admin customization ready for geospatial

## Next Development Priorities (Revenue-Focused)
1. Full ZSA issuance flow (mint property shares as shielded asset)
2. User authentication + roles (issuer vs investor)
3. Stripe subscription integration
4. Investor portfolio dashboard with private balance viewing
5. Rental distribution simulation via shielded tx
6. KYC/Compliance module
7. Production deployment (Docker + VPS with zcashd)

## Zcash / ZSA Integration Notes
- Use `zcash_integration/zcash_client.py` for all RPC calls.
- For ZSA: Monitor ZIP 227 / NU7. Current code uses z_sendmany + memo for metadata. Full custom asset support via protocol tools or updated zcashd RPC.
- Privacy first: All sensitive ops use shielded addresses where possible.

## Legal / Compliance Warning
Real estate tokenization involves securities laws. This platform provides the technical layer. Always use proper legal SPVs and consult lawyers for KYC/AML/accreditation. ZSA issuance must comply with applicable regulations.

## Contributing & Roadmap
This is the foundation. Let's iterate fast toward a revenue-generating MVP.

Built for programmers who want to ship complex, monetizable Web3 + real-world software.

---

**Let's build the future of private real estate.** Start with the code below and expand.
