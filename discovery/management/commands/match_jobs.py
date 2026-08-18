from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from discovery.models import JobSearchTarget
from discovery.services.matcher import shortlist_for_user


class Command(BaseCommand):
    help = (
        "Show the best non-AI discovered job matches "
        "for one user."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            required=True,
            help=(
                "Username or email of the user."
            ),
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help=(
                "Maximum number of matches to show. "
                "Default: 20"
            ),
        )

    def handle(self, *args, **options):
        user_value = (
            options["user"]
            .strip()
        )

        limit = options["limit"]

        if limit < 1:
            raise CommandError(
                "--limit must be at least 1."
            )

        if limit > 100:
            raise CommandError(
                "--limit cannot be greater than 100."
            )

        User = get_user_model()

        user = (
            User.objects
            .filter(
                username=user_value
            )
            .first()
        )

        if user is None:
            user = (
                User.objects
                .filter(
                    email__iexact=user_value
                )
                .first()
            )

        if user is None:
            raise CommandError(
                f"User not found: {user_value}"
            )

        targets = (
            JobSearchTarget.objects
            .filter(
                user=user,
                active=True,
            )
        )

        if not targets.exists():
            raise CommandError(
                "This user has no active job search targets."
            )

        self.stdout.write("")

        self.stdout.write(
            self.style.NOTICE(
                f"Matching jobs for: {user}"
            )
        )

        self.stdout.write(
            f"Active targets: {targets.count()}"
        )

        self.stdout.write("")

        results = shortlist_for_user(
            user=user,
            final_limit=limit,
        )

        if not results:
            self.stdout.write(
                self.style.WARNING(
                    "No matching jobs found."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(results)} matches:"
            )
        )

        self.stdout.write("")

        for index, item in enumerate(
            results,
            start=1,
        ):
            job = item["job"]
            target = item["target"]
            score = item["score"]
            reason = item["reason"]

            self.stdout.write(
                (
                    f"{index:>2}. "
                    f"{score:>5.1f}%  "
                    f"{job.title}"
                )
            )

            self.stdout.write(
                (
                    f"    Company: "
                    f"{job.company or '-'}"
                )
            )

            self.stdout.write(
                (
                    f"    Location: "
                    f"{job.location or '-'}"
                )
            )

            self.stdout.write(
                (
                    f"    Target: "
                    f"{target.title}"
                )
            )

            self.stdout.write(
                (
                    f"    Reason: "
                    f"{reason}"
                )
            )

            self.stdout.write(
                (
                    f"    Source: "
                    f"{job.get_source_display()}"
                )
            )

            self.stdout.write(
                (
                    f"    URL: "
                    f"{job.url}"
                )
            )

            self.stdout.write("")