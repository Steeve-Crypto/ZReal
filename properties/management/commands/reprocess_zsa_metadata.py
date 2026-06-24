"""
Django management command to re-process existing properties
and populate the new ZSA metadata fields.

Usage:
    python manage.py reprocess_zsa_metadata
    python manage.py reprocess_zsa_metadata --dry-run
    python manage.py reprocess_zsa_metadata --property-id 5
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from properties.models import Property, PropertyDocument


class Command(BaseCommand):
    help = "Re-process existing properties to populate new ZSA metadata fields (zsa_issuance_method, zsa_metadata, etc.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )
        parser.add_argument(
            "--property-id",
            type=int,
            help="Only process a specific property by ID",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update even if zsa_issuance_method is already set",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        property_id = options.get("property_id")
        force = options["force"]

        queryset = Property.objects.filter(zsa_asset_id__isnull=False)

        if property_id:
            queryset = queryset.filter(id=property_id)

        if not force:
            queryset = queryset.filter(zsa_issuance_method="")

        total = queryset.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No properties found that need re-processing."))
            return

        self.stdout.write(f"Found {total} property(ies) to process...")

        updated_count = 0

        for prop in queryset:
            changes = {}

            # Infer issuance method if missing
            if not prop.zsa_issuance_method:
                if "zcash_tx_tool" in (prop.zsa_asset_id or "").lower():
                    method = "zcash_tx_tool"
                else:
                    method = "rich_memo"  # Most common fallback
                changes["zsa_issuance_method"] = method

            # Populate zsa_metadata if empty but we have related documents
            if not prop.zsa_metadata:
                latest_doc = (
                    PropertyDocument.objects.filter(property=prop, processing_status="completed")
                    .order_by("-processed_at")
                    .first()
                )
                if latest_doc and latest_doc.extracted_data:
                    metadata = {
                        "legal_shield": {
                            "document_type": latest_doc.document_type,
                            "extracted": latest_doc.extracted_data,
                            "processed_at": str(latest_doc.processed_at),
                            "source": "pdfplumber + OCR (reprocessed)",
                        }
                    }
                    changes["zsa_metadata"] = metadata

            # Set last_zsa_txid if missing
            if not prop.last_zsa_txid and prop.zsa_asset_id:
                changes["last_zsa_txid"] = prop.zsa_asset_id

            # Set zsa_issued_at if missing
            if not prop.zsa_issued_at:
                changes["zsa_issued_at"] = prop.updated_at or timezone.now()

            if changes:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f"[DRY RUN] Would update Property #{prop.id} ({prop.title}): {changes}")
                    )
                else:
                    for field, value in changes.items():
                        setattr(prop, field, value)
                    prop.save(update_fields=list(changes.keys()))
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Updated Property #{prop.id} ({prop.title}) with: {list(changes.keys())}")
                    )

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDry run complete. {total} properties would be updated."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nSuccessfully updated {updated_count} out of {total} properties.")
            )
