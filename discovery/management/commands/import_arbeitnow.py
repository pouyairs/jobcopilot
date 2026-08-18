from django.core.management.base import BaseCommand, CommandError

from discovery.services.arbeitnow import import_arbeitnow_jobs


class Command(BaseCommand):
    help = (
        "Import job vacancies from Arbeitnow "
        "into the JobCopilot discovery database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--pages",
            type=int,
            default=3,
            help=(
                "Number of Arbeitnow result pages "
                "to import. Default: 3"
            ),
        )

    def handle(self, *args, **options):
        pages = options["pages"]

        if pages < 1:
            raise CommandError(
                "--pages must be at least 1."
            )

        if pages > 20:
            raise CommandError(
                "--pages cannot be greater than 20 "
                "for this MVP command."
            )

        self.stdout.write(
            self.style.NOTICE(
                f"Importing Arbeitnow jobs "
                f"from {pages} page(s)..."
            )
        )

        try:
            result = import_arbeitnow_jobs(
                pages=pages,
            )

        except Exception as exc:
            raise CommandError(
                f"Arbeitnow import failed: {exc}"
            ) from exc

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Arbeitnow import completed."
            )
        )

        self.stdout.write(
            f"Fetched: {result['fetched']}"
        )

        self.stdout.write(
            f"Created: {result['created']}"
        )

        self.stdout.write(
            f"Updated: {result['updated']}"
        )

        self.stdout.write(
            f"Skipped: {result['skipped']}"
        )