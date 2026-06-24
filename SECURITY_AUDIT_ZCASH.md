# Security Audit Checklist – Zcash Integration

## 1. Key Management
- [ ] Issuer/platform shielded addresses are never exposed in frontend
- [ ] Private keys / spending keys are stored securely (HSM or encrypted env)
- [ ] `from_zaddr` used in payouts is properly funded and monitored
- [ ] No hardcoded testnet/mainnet addresses in production code

## 2. Transaction Security
- [ ] All Zcash calls use `AllowFullyShielded` policy where possible
- [ ] Memos do not leak sensitive PII (only hashes or encrypted data)
- [ ] Transaction amounts are validated server-side before sending
- [ ] Failed transactions are properly retried or marked as failed

## 3. API & RPC Security
- [ ] Zcash RPC is not exposed publicly
- [ ] Strong authentication on Zcash node (username + password or cookie)
- [ ] Rate limiting on all endpoints that trigger Zcash transactions
- [ ] Input validation on all shielded addresses

## 4. Dividend Payout Flow
- [ ] Payout calculation is deterministic and auditable
- [ ] Distribution records are created **before** sending funds (idempotency)
- [ ] Monitoring task properly updates status based on on-chain data
- [ ] No double-spend risk in concurrent payout runs

## 5. General Application Security
- [ ] All sensitive endpoints require authentication + authorization
- [ ] CSRF protection enabled on all state-changing requests
- [ ] OpenTelemetry + structured logging for audit trails
- [ ] Falco rules monitoring for anomalous Zcash RPC behavior

## Recommended Tools for Audit
- **Zcash-specific**: `zcash-cli` debugging, `z_getoperationstatus`
- **General**: `bandit`, `safety`, `pip-audit`, OWASP ZAP
- **Runtime**: Falco + eBPF monitoring

**Next Step**: Engage a security firm familiar with Zcash / zk-SNARKs for a formal audit before mainnet.
