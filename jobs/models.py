from django.db import models
from django.contrib.auth.models import User


class JobApplication(models.Model):

    SOURCE_CHOICES = [
        ("linkedin", "LinkedIn"),
        ("indeed", "Indeed"),
        ("stepstone", "StepStone"),
        ("xing", "XING"),
        ("company", "Company Website"),
        ("other", "Other"),
    ]

    DECISION_CHOICES = [
        ("APPLY", "Apply"),
        ("STRETCH", "Stretch"),
        ("SKIP", "Skip"),
    ]

    STATUS_CHOICES = [
        ("not_applied", "Not Applied"),
        ("applied", "Applied"),
        ("interview", "Interview"),
        ("rejected", "Rejected"),
        ("offer", "Offer"),
        ("withdrawn", "Withdrawn"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="job_applications"
    )

    company = models.CharField(
        max_length=200,
        blank=True
    )

    job_title = models.CharField(
        max_length=200,
        blank=True
    )

    city = models.CharField(
        max_length=150,
        blank=True
    )

    job_description = models.TextField()

    job_url = models.URLField(
        blank=True
    )

    source = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        default="other"
    )

    score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True
    )

    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        blank=True
    )

    employer_type = models.CharField(
        max_length=100,
        blank=True
    )

    zeitarbeit_risk = models.BooleanField(
        default=False
    )

    strong_matches = models.JSONField(
        default=list,
        blank=True
    )

    gaps = models.JSONField(
        default=list,
        blank=True
    )

    risks = models.JSONField(
        default=list,
        blank=True
    )

    do_not_claim = models.JSONField(
        default=list,
        blank=True
    )

    recommended_cv = models.TextField(
        blank=True
    )

    summary = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="not_applied"
    )

    applied_date = models.DateField(
        null=True,
        blank=True
    )

    # Optional follow-up
    follow_up_date = models.DateField(
        null=True,
        blank=True
    )

    follow_up_note = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company} - {self.job_title}"