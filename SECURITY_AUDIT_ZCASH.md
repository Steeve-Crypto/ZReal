# Zcash Security Notes

ZReal does not store spending keys and does not generate fake tokenization IDs.

## Current Protections

- issuer mutations require authentication
- issuers can only mutate their own properties
- tokenization uses POST + CSRF
- document upload is ownership-protected
- ZSA attempts are recorded in `TokenizationOperation`
- missing ZSA configuration fails loudly
- tokenization metadata uses document hashes and selected structured fields, not raw legal text
- plaintext viewing-key storage is not present

## Required Before Production

- verify the configured ZSA tool on testnet
- ensure the Zcash RPC service is not public
- keep private keys outside the Django app
- add rate limiting to tokenization and upload endpoints
- viewing keys are not currently stored; review any future encrypted storage design before enabling them
- add structured audit logs for ZSA operations
- run formal security review before mainnet or real capital
