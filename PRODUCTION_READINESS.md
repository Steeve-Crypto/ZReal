# Production Readiness

ZReal is runnable locally, but it is not production-ready yet.

## Ready

- Django system checks pass.
- Local SQLite development works.
- Routes import cleanly.
- Issuer property creation/editing works.
- Address-first property enrichment works in local fixture mode and requires issuer review before tokenization readiness.
- Document upload is ownership-protected.
- Dashboards use persisted application records.
- Tokenization attempts are auditable and record only identifiers returned by configured tooling.

## Required Before Production

- Configure and verify ZSA issuance tooling on testnet.
- Run at least one real end-to-end ZSA issuance.
- Approve and configure licensed live property data providers before relying on parcel/tax enrichment in production.
- Add KYC/AML and securities compliance workflows.
- Add authorization and audit coverage beyond the current core tests.
- Configure production database, static/media storage, HTTPS, email, logging, and backups.
- Decide whether viewing keys should ever be stored. If yes, add encrypted storage first.
- Configure Stripe products, prices, and webhooks if billing is enabled.
