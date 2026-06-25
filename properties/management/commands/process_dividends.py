from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Report dividend payout availability. Real payout distribution is not implemented yet.'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Dividend/rental payouts are not implemented. No Zcash transactions were created."
            )
        )
