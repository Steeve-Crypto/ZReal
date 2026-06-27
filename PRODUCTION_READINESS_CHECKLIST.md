# ZReal Readiness Checklist

## Currently Passing

- [x] Django routes import cleanly
- [x] Local SQLite migrations apply
- [x] System checks pass
- [x] Current tests pass
- [x] Issuer property creation/editing exists
- [x] Document upload is ownership-protected
- [x] Tokenization attempts are audited
- [x] Simulated txids and asset IDs are not generated
- [x] Safe document metadata is attached to tokenization attempts
- [x] Plaintext viewing-key storage has been removed
- [x] Property lifecycle/readiness blocks unsafe tokenization
- [x] Address-first property enrichment is review-gated before tokenization readiness
- [x] Missing ZSA configuration blocks before tokenization operation creation
- [x] Invalid ZSA configuration returns safe errors
- [x] Failed external tool calls are recorded as failed operations

## Required Before Handling Real Capital

- [ ] Configure a real ZSA-capable issuance tool
- [ ] Run a successful testnet issuance end to end
- [ ] Add investor purchase flow
- [ ] Add deterministic distribution/rental payout model
- [ ] Add KYC/AML and legal compliance workflow
- [ ] Add rate limiting on mutation endpoints
- [ ] Configure licensed live property enrichment providers and compliance registry
- [ ] Encrypt or remove viewing-key storage
- [ ] Configure production database, media storage, HTTPS, logging, and backups
- [ ] Configure Stripe products/prices/webhooks if billing is enabled
- [ ] Run browser/manual QA against a real configured ZSA backend
