# Production Readiness

ZReal is runnable locally, but it is not production-ready yet.

## Ready

- Django system checks pass.
- Local SQLite development works.
- Routes import cleanly.
- Issuer property creation/editing works.
- Document upload is ownership-protected.
- Dashboards use database-backed values.
- Tokenization attempts are auditable and do not generate fake IDs.

## Required Before Production

- Configure and verify a real ZSA issuance backend on testnet.
- Run at least one real end-to-end ZSA issuance.
- Add KYC/AML and securities compliance workflows.
- Add authorization and audit coverage beyond the current core tests.
- Configure production database, static/media storage, HTTPS, email, logging, and backups.
- Decide whether viewing keys should ever be stored. If yes, add encrypted storage first.
- Configure Stripe products, prices, and webhooks if billing is enabled.
