from django.contrib import admin

from .models import JobApplication


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "job_title",
        "city",
        "user",
        "score",
        "decision",
        "status",
        "source",
        "applied_date",
        "follow_up_date",
        "created_at",
    )

    list_filter = (
        "decision",
        "status",
        "source",
        "employer_type",
        "zeitarbeit_risk",
        "created_at",
    )

    search_fields = (
        "company",
        "job_title",
        "city",
        "user__username",
        "user__email",
        "job_description",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "User & Job",
            {
                "fields": (
                    "user",
                    "company",
                    "job_title",
                    "city",
                    "job_url",
                    "source",
                    "job_description",
                )
            },
        ),
        (
            "Analysis",
            {
                "fields": (
                    "score",
                    "decision",
                    "employer_type",
                    "zeitarbeit_risk",
                    "summary",
                    "recommended_cv",
                )
            },
        ),
        (
            "Analysis Details",
            {
                "fields": (
                    "strong_matches",
                    "gaps",
                    "risks",
                    "do_not_claim",
                )
            },
        ),
        (
            "Application Tracking",
            {
                "fields": (
                    "status",
                    "applied_date",
                    "follow_up_date",
                    "follow_up_note",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    ordering = ("-created_at",)

    list_per_page = 50


admin.site.site_header = "JobCopilot Administration"
admin.site.site_title = "JobCopilot Admin"
admin.site.index_title = "JobCopilot Management"