from django.core.management.base import BaseCommand
from properties.tasks import process_dividend_payouts


class Command(BaseCommand):
    help = 'Trigger automated dividend payouts with real Zcash shielded payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--property-id',
            type=int,
            help='Process dividends for a specific property ID only',
        )
        parser.add_argument(
            '--from-zaddr',
            type=str,
            help='Shielded address to send payouts from (issuer/platform address)',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run as Celery background task instead of synchronously',
        )

    def handle(self, *args, **options):
        property_id = options.get('property_id')
        from_zaddr = options.get('from_zaddr')
        run_async = options.get('async', False)

        self.stdout.write(self.style.WARNING("Starting dividend payout process..."))

        if run_async:
            # Run via Celery
            result = process_dividend_payouts.delay(
                property_id=property_id,
                from_zaddr=from_zaddr
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Task submitted to Celery. Task ID: {result.id}"
                )
            )
        else:
            # Run synchronously (useful for testing)
            result = process_dividend_payouts(
                property_id=property_id,
                from_zaddr=from_zaddr
            )
            self.stdout.write(
                self.style.SUCCESS(f"Completed: {result}")
            )
