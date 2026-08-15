from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):

    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("fa", "فارسی"),
    ]

    PLAN_CHOICES = [
        ("free", "Free"),
        ("pro", "Pro"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    full_name = models.CharField(
        max_length=150,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    country = models.CharField(
        max_length=100,
        blank=True
    )

    relocation = models.BooleanField(
        default=False
    )

    professional_summary = models.TextField(
        blank=True
    )

    # Legacy fields
    # فعلاً نگه می‌داریم تا اطلاعات قبلی از بین نرود.

    education = models.TextField(
        blank=True
    )

    experience = models.TextField(
        blank=True
    )

    strong_skills = models.TextField(
        blank=True
    )

    basic_skills = models.TextField(
        blank=True
    )

    languages = models.TextField(
        blank=True
    )

    do_not_claim = models.TextField(
        blank=True
    )

    preferred_language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="en"
    )

    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default="free"
    )

    def __str__(self):
        return self.full_name or self.user.username


# =========================================================
# EXPERIENCE
# =========================================================

class Experience(models.Model):

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="experiences"
    )

    job_title = models.CharField(
        max_length=200
    )

    company = models.CharField(
        max_length=200
    )

    location = models.CharField(
        max_length=200,
        blank=True
    )

    start_date = models.CharField(
        max_length=30,
        blank=True
    )

    end_date = models.CharField(
        max_length=30,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    technologies = models.TextField(
        blank=True
    )

    order = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        ordering = [
            "order",
            "-id"
        ]

    def __str__(self):
        return f"{self.job_title} - {self.company}"


# =========================================================
# EDUCATION
# =========================================================

class Education(models.Model):

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="educations"
    )

    degree = models.CharField(
        max_length=200
    )

    institution = models.CharField(
        max_length=200
    )

    location = models.CharField(
        max_length=200,
        blank=True
    )

    start_date = models.CharField(
        max_length=30,
        blank=True
    )

    end_date = models.CharField(
        max_length=30,
        blank=True
    )

    details = models.TextField(
        blank=True
    )

    order = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        ordering = [
            "order",
            "-id"
        ]

    def __str__(self):
        return f"{self.degree} - {self.institution}"


# =========================================================
# SKILLS
# =========================================================

class Skill(models.Model):

    LEVEL_CHOICES = [
        ("unclassified", "Not Classified"),
        ("basic", "Basic"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
        ("expert", "Expert"),
    ]

    SOURCE_CHOICES = [
        ("professional", "Professional Experience"),
        ("education", "Education"),
        ("project", "Personal Project"),
        ("course", "Course / Certification"),
        ("self_taught", "Self-taught"),
        ("unspecified", "Not Specified"),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="skills"
    )

    name = models.CharField(
        max_length=120
    )

    level = models.CharField(
        max_length=30,
        choices=LEVEL_CHOICES,
        default="unclassified"
    )

    source = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        default="unspecified"
    )

    do_not_claim = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.name} - {self.get_level_display()}"


# =========================================================
# LANGUAGES
# =========================================================

class LanguageEntry(models.Model):

    LEVEL_CHOICES = [
        ("unspecified", "Not Specified"),
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("B2", "B2"),
        ("C1", "C1"),
        ("C2", "C2"),
        ("native", "Native"),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="language_entries"
    )

    language = models.CharField(
        max_length=100
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="unspecified"
    )

    original_level = models.CharField(
        max_length=100,
        blank=True
    )

    def __str__(self):
        return f"{self.language} - {self.get_level_display()}"


# =========================================================
# CERTIFICATIONS
# =========================================================

class Certification(models.Model):

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="certifications"
    )

    name = models.CharField(
        max_length=200
    )

    issuer = models.CharField(
        max_length=200,
        blank=True
    )

    date = models.CharField(
        max_length=50,
        blank=True
    )

    def __str__(self):
        return self.name