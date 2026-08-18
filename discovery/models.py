from django.conf import settings
from django.db import models


class JobSearchTarget(models.Model):
    """
    A job title / search preference that a user wants
    JobCopilot to search for regularly.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_search_targets",
    )

    title = models.CharField(
        max_length=200,
    )

    location = models.CharField(
        max_length=200,
        blank=True,
    )

    radius_km = models.PositiveIntegerField(
        default=50,
    )

    remote = models.BooleanField(
        default=True,
    )

    exclude_zeitarbeit = models.BooleanField(
        default=False,
    )

    minimum_match_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=6.0,
    )

    active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "title",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "title",
                    "location",
                ],
                name="unique_job_search_target",
            ),
        ]

    def __str__(self):
        location = (
            self.location
            or "Any location"
        )

        return (
            f"{self.user} - "
            f"{self.title} - "
            f"{location}"
        )


class DiscoveredJob(models.Model):
    """
    A job vacancy collected from an external source.

    This model is shared between users.
    One vacancy should not be downloaded and stored
    separately for every user.
    """

    SOURCE_CHOICES = [
        (
            "arbeitnow",
            "Arbeitnow",
        ),
        (
            "arbeitsagentur",
            "Bundesagentur für Arbeit",
        ),
        (
            "indeed",
            "Indeed",
        ),
        (
            "stepstone",
            "StepStone",
        ),
        (
            "linkedin",
            "LinkedIn",
        ),
        (
            "company",
            "Company Website",
        ),
        (
            "other",
            "Other",
        ),
    ]

    source = models.CharField(
        max_length=40,
        choices=SOURCE_CHOICES,
        default="other",
    )

    external_id = models.CharField(
        max_length=300,
    )

    title = models.CharField(
        max_length=300,
    )

    company = models.CharField(
        max_length=250,
        blank=True,
    )

    location = models.CharField(
        max_length=250,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    url = models.URLField(
        max_length=1500,
    )

    remote = models.BooleanField(
        default=False,
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    first_seen_at = models.DateTimeField(
        auto_now_add=True,
    )

    last_seen_at = models.DateTimeField(
        auto_now=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            "-published_at",
            "-first_seen_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source",
                    "external_id",
                ],
                name="unique_discovered_job_source_id",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "source",
                    "published_at",
                ],
            ),
            models.Index(
                fields=[
                    "is_active",
                ],
            ),
        ]

    def __str__(self):
        company = (
            self.company
            or "Unknown Company"
        )

        return (
            f"{company} - "
            f"{self.title}"
        )


class JobRecommendation(models.Model):
    """
    Connects a discovered vacancy to a specific user.

    The same DiscoveredJob may be recommended to
    multiple users with different match scores.
    """

    STATUS_CHOICES = [
        (
            "new",
            "New",
        ),
        (
            "viewed",
            "Viewed",
        ),
        (
            "saved",
            "Saved",
        ),
        (
            "analyzed",
            "Analyzed",
        ),
        (
            "not_interested",
            "Not Interested",
        ),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_recommendations",
    )

    job = models.ForeignKey(
        DiscoveredJob,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )

    target = models.ForeignKey(
        JobSearchTarget,
        on_delete=models.SET_NULL,
        related_name="recommendations",
        null=True,
        blank=True,
    )

    match_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
    )

    match_reason = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="new",
    )

    recommended_at = models.DateTimeField(
        auto_now_add=True,
    )

    viewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-recommended_at",
            "-match_score",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "job",
                ],
                name="unique_job_recommendation_per_user",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "user",
                    "recommended_at",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.job.title} - "
            f"{self.match_score or '-'}"
        )