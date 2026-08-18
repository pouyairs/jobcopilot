from django.contrib import admin

from .models import (
    DiscoveredJob,
    JobRecommendation,
    JobSearchTarget,
)


@admin.register(JobSearchTarget)
class JobSearchTargetAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "title",
        "location",
        "radius_km",
        "remote",
        "exclude_zeitarbeit",
        "minimum_match_score",
        "active",
        "updated_at",
    )

    list_filter = (
        "active",
        "remote",
        "exclude_zeitarbeit",
    )

    search_fields = (
        "user__username",
        "user__email",
        "title",
        "location",
    )

    ordering = (
        "user",
        "title",
    )

    list_per_page = 50


@admin.register(DiscoveredJob)
class DiscoveredJobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "location",
        "source",
        "remote",
        "published_at",
        "is_active",
        "first_seen_at",
    )

    list_filter = (
        "source",
        "remote",
        "is_active",
    )

    search_fields = (
        "title",
        "company",
        "location",
        "external_id",
        "url",
    )

    ordering = (
        "-published_at",
        "-first_seen_at",
    )

    readonly_fields = (
        "first_seen_at",
        "last_seen_at",
    )

    list_per_page = 50


@admin.register(JobRecommendation)
class JobRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "job",
        "target",
        "match_score",
        "status",
        "recommended_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "recommended_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "job__title",
        "job__company",
        "job__location",
        "target__title",
    )

    ordering = (
        "-recommended_at",
        "-match_score",
    )

    readonly_fields = (
        "recommended_at",
        "viewed_at",
        "updated_at",
    )

    list_select_related = (
        "user",
        "job",
        "target",
    )

    list_per_page = 50