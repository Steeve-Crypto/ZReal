# ZReal Readiness Checklist

## Currently Passing

- [x] Django routes import cleanly
- [x] Local SQLite migrations apply
- [x] System checks pass
- [x] Current tests pass
- [x] Issuer property creation/editing exists
- [x] Document upload is ownership-protected
- [x] Tokenization attempts are audited
- [x] Fake txids and fake asset IDs are not generated
- [x] Safe document metadata is attached to tokenization attempts
- [x] Plaintext viewing-key storage has been removed

## Required Before Handling Real Capital

- [ ] Configure a real ZSA-capable issuance tool
- [ ] Run a successful testnet issuance end to end
- [ ] Add investor purchase flow
- [ ] Add deterministic distribution/rental payout model
- [ ] Add KYC/AML and legal compliance workflow
- [ ] Add rate limiting on mutation endpoints
- [ ] Encrypt or remove viewing-key storage
- [ ] Configure production database, media storage, HTTPS, logging, and backups
- [ ] Configure Stripe products/prices/webhooks if billing is enabled
- [ ] Expand tests for authorization failures and tokenization failure states
