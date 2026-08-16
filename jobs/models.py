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
        related_name="job_applications",
    )

    company = models.CharField(
        max_length=200,
        blank=True,
    )

    job_title = models.CharField(
        max_length=200,
        blank=True,
    )

    city = models.CharField(
        max_length=150,
        blank=True,
    )

    job_description = models.TextField()

    job_url = models.URLField(
        blank=True,
    )

    source = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        default="other",
    )

    score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
    )

    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        blank=True,
    )

    employer_type = models.CharField(
        max_length=100,
        blank=True,
    )

    zeitarbeit_risk = models.BooleanField(
        default=False,
    )

    strong_matches = models.JSONField(
        default=list,
        blank=True,
    )

    gaps = models.JSONField(
        default=list,
        blank=True,
    )

    risks = models.JSONField(
        default=list,
        blank=True,
    )

    do_not_claim = models.JSONField(
        default=list,
        blank=True,
    )

    recommended_cv = models.TextField(
        blank=True,
    )

    summary = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="not_applied",
    )

    applied_date = models.DateField(
        null=True,
        blank=True,
    )

    follow_up_date = models.DateField(
        null=True,
        blank=True,
    )

    follow_up_note = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        company = self.company or "Unknown Company"
        job_title = self.job_title or "Unknown Job"

        return f"{company} - {job_title}"


class CoverLetter(models.Model):

    LANGUAGE_CHOICES = [
        ("de", "German"),
        ("en", "English"),
    ]

    SIGNATURE_CHOICES = [
        ("typed", "Typed Signature"),
        ("uploaded", "Uploaded Signature"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="cover_letters",
    )

    job = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="cover_letters",
    )

    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
    )

    # =====================================================
    # RECIPIENT / COMPANY
    # =====================================================

    recipient_company = models.CharField(
        max_length=200,
        blank=True,
    )

    recipient_contact = models.CharField(
        max_length=200,
        blank=True,
    )

    recipient_street = models.CharField(
        max_length=250,
        blank=True,
    )

    recipient_postal_code = models.CharField(
        max_length=30,
        blank=True,
    )

    recipient_city = models.CharField(
        max_length=150,
        blank=True,
    )

    # =====================================================
    # LETTER
    # =====================================================

    subject = models.CharField(
        max_length=300,
        blank=True,
    )

    content = models.TextField(
        blank=True,
    )

    # =====================================================
    # SIGNATURE
    # =====================================================

    signature_type = models.CharField(
        max_length=20,
        choices=SIGNATURE_CHOICES,
        default="typed",
    )

    signature_name = models.CharField(
        max_length=200,
        blank=True,
    )

    signature_image = models.FileField(
        upload_to="signatures/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "job",
                    "language",
                ],
                name="unique_cover_letter_per_job_language",
            )
        ]

    def __str__(self):
        company = (
            self.recipient_company
            or self.job.company
            or "Unknown Company"
        )

        job_title = (
            self.job.job_title
            or "Unknown Job"
        )

        return (
            f"{self.get_language_display()} - "
            f"{company} - "
            f"{job_title}"
        )