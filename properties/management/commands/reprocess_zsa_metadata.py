"""
Review existing tokenized properties for legacy ZSA metadata.

The current Property model only stores zsa_asset_id. Older code referenced richer
metadata fields that are not present, so this command now reports candidates
without mutating nonexistent columns.
"""

from django.core.management.base import BaseCommand

from properties.models import Property


class Command(BaseCommand):
    help = "Report properties with existing zsa_asset_id values."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Kept for compatibility; this command is report-only.",
        )
        parser.add_argument(
            "--property-id",
            type=int,
            help="Only inspect a specific property by ID",
        )

    def handle(self, *args, **options):
        queryset = Property.objects.exclude(zsa_asset_id__isnull=True).exclude(zsa_asset_id="")

        if options.get("property_id"):
            queryset = queryset.filter(id=options["property_id"])

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No properties with ZSA asset IDs found."))
            return

        for prop in queryset:
            self.stdout.write(
                self.style.SUCCESS(f"Property #{prop.id} ({prop.title}) has ZSA asset ID {prop.zsa_asset_id}")
            )

        self.stdout.write(self.style.SUCCESS(f"Reviewed {total} propert(ies)."))
