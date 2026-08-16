from django.contrib import admin

from .models import (
    Profile,
    Experience,
    Education,
    Skill,
    LanguageEntry,
    Certification,
)


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0


class LanguageEntryInline(admin.TabularInline):
    model = LanguageEntry
    extra = 0


class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "city",
        "country",
        "preferred_language",
        "plan",
    )

    search_fields = (
        "user__username",
        "user__email",
        "full_name",
        "city",
        "country",
    )

    list_filter = (
        "preferred_language",
        "plan",
        "country",
    )

    inlines = [
        ExperienceInline,
        EducationInline,
        SkillInline,
        LanguageEntryInline,
        CertificationInline,
    ]


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = (
        "job_title",
        "company",
        "location",
        "profile",
        "start_date",
        "end_date",
    )

    search_fields = (
        "job_title",
        "company",
        "profile__full_name",
        "profile__user__username",
        "profile__user__email",
    )


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = (
        "degree",
        "institution",
        "location",
        "profile",
    )

    search_fields = (
        "degree",
        "institution",
        "profile__full_name",
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "level",
        "source",
        "do_not_claim",
        "profile",
    )

    list_filter = (
        "level",
        "source",
        "do_not_claim",
    )

    search_fields = (
        "name",
        "profile__full_name",
        "profile__user__username",
    )


@admin.register(LanguageEntry)
class LanguageEntryAdmin(admin.ModelAdmin):
    list_display = (
        "language",
        "level",
        "original_level",
        "profile",
    )

    search_fields = (
        "language",
        "profile__full_name",
    )


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "issuer",
        "date",
        "profile",
    )

    search_fields = (
        "name",
        "issuer",
        "profile__full_name",
    )


admin.site.site_header = "JobCopilot Administration"
admin.site.site_title = "JobCopilot Admin"
admin.site.index_title = "JobCopilot Management"