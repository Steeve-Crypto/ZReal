# ZK-SNARK Audit Plan for ZReal

Zcash uses **zk-SNARKs** (Zero-Knowledge Succinct Non-Interactive Arguments of Knowledge) to enable shielded transactions while preserving privacy.

## Why ZK-SNARK Audit Matters for ZReal

Even though ZReal does **not** implement custom circuits, it interacts heavily with Zcash's shielded pool. A proper audit should verify that:

- Memos do not accidentally leak information
- Transaction construction follows best practices
- No side-channel leaks in how ZReal handles shielded data

## Recommended Audit Scope

### 1. Zcash Integration Layer
- Review of `ZcashClient` class and all `z_sendmany` calls
- Verification that `AllowFullyShielded` policy is consistently used
- Check that memo construction does not include unencrypted sensitive data

### 2. Dividend Payout Flow
- Ensure distribution amounts and recipient lists are correctly formed before calling shielded send
- Verify that `Distribution` model state transitions are secure and atomic

### 3. Data Handling
- Audit how Legal Shield extracted data is stored in ZSA memos
- Ensure only cryptographic commitments or hashes are stored on-chain when possible

### 4. Future-Proofing
- Prepare for potential migration to **Halo 2** or future Zcash proof systems

## How to Perform / Commission the Audit

### Option A: Self-Review (Internal)
- Use `zcashd` debug logs + `getrawtransaction`
- Review all places where shielded transactions are constructed
- Document memo schemas

### Option B: External Security Firm
Recommended firms with Zcash/zk-SNARK experience:
- Least Authority
- Trail of Bits
- NCC Group
- Kudelski Security

**Estimated Cost**: $25k – $60k depending on scope (recommended before mainnet with real capital).

## Deliverables from Audit

- Report on potential information leakage vectors
- Recommendations for memo encryption / commitment schemes
- Review of error handling around failed shielded transactions
- Guidance on safe upgrade paths for future Zcash protocol changes

---

**Status**: ZReal is designed to be **audit-friendly**. All critical shielded logic is centralized in `ZcashClient` and the dividend Celery tasks.
