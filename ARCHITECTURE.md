# ZReal Architecture

## Runtime Components

- Django views/templates provide the web app.
- SQLite is the default local database. `DATABASE_URL` can point to Postgres for deployments.
- Uploaded documents are stored under `MEDIA_ROOT`.
- Zcash/ZSA issuance is delegated to a configured external tool.
- Stripe checkout is optional and disabled until Stripe settings are present.

## Core Models

- `core.UserProfile`: role, subscription status, optional viewing key field.
- `properties.Property`: issuer-owned property record, map coordinates, estimated value, tokenization state.
- `properties.PropertyDocument`: uploaded document plus extracted text/data.
- `properties.PropertyInvestment`: investor share positions.
- `properties.TokenizationOperation`: auditable record of each ZSA issuance attempt.

## Request Flow

1. `/accounts/` handles authentication via django-allauth.
2. `/profile/role/` lets users choose investor or issuer.
3. `/issuer/dashboard/` shows issuer-owned properties and real database metrics.
4. `/properties/new/` and `/properties/<id>/edit/` manage issuer-owned property data.
5. `/properties/<id>/upload-document/` accepts documents only from the owning issuer.
6. `/properties/<id>/issue-zsa/` creates a `TokenizationOperation` and calls the configured ZSA backend.
7. `/properties/<id>/refresh-zsa-status/` refreshes pending operation state.

## ZSA Boundary

ZReal does not create fake txids or fake asset IDs. The external ZSA command must return JSON containing real identifiers. If configuration is missing or the tool fails, ZReal records the failed operation and shows the issuer a clear error.

Tokenization metadata is generated from safe fields only: property identifier, asset symbol, share count, uploaded document types, document SHA-256 hashes, timestamps, and selected structured extraction fields. Full legal text is not passed to tokenization metadata.

## Not Implemented Yet

- native in-process ZSA minting
- investor purchase checkout
- dividend/rental distribution execution
- KYC/AML workflow
