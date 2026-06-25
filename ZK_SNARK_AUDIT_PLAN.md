# Zcash / ZK Audit Notes

ZReal does not implement custom zk-SNARK circuits.

The audit scope is the application boundary around Zcash/ZSA tooling:

- issuer address validation
- external ZSA command configuration
- tokenization state transitions
- avoiding sensitive legal/property data in public metadata
- ensuring private keys stay outside Django
- checking that failed issuance attempts are recorded truthfully

Before mainnet or real capital:

- run a real testnet issuance
- review the configured ZSA tool
- verify command output parsing
- review logs and database records for sensitive data leakage
- commission an external security review if assets of meaningful value are involved
