from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from accounts.models import Profile
from jobs.ai.analyzer import analyze_job
from jobs.models import JobApplication

from .forms import JobSearchTargetForm
from .models import (
    JobRecommendation,
    JobSearchTarget,
)
from .services.importer import import_from_source
from .services.matcher import shortlist_for_user
from .services.profile_ranker import (
    rank_jobs_for_profile,
)
from .services.sources.arbeitnow import (
    ArbeitnowJobSource,
)
from .services.sources.arbeitsagentur import (
    ArbeitsagenturJobSource,
)
from .services.sources.adzuna import (
    AdzunaJobSource,
)
from .services.sources.jooble import (
    JoobleJobSource,
)
from .services.sources.external_links import (
    build_user_external_searches,
)


AI_REASON_PREFIX = "PROFILE_MATCH:"
MAX_JOB_TARGETS = 3


# =========================================================
# HELPERS
# =========================================================

def build_analysis_description(
    discovered_job,
):
    parts = []

    if discovered_job.title:
        parts.append(
            f"JOB TITLE:\n{discovered_job.title}"
        )

    if discovered_job.company:
        parts.append(
            f"COMPANY:\n{discovered_job.company}"
        )

    if discovered_job.location:
        parts.append(
            f"LOCATION:\n{discovered_job.location}"
        )

    if discovered_job.remote:
        parts.append(
            "REMOTE:\nYes"
        )

    if discovered_job.description:
        parts.append(
            "JOB DESCRIPTION:\n"
            f"{discovered_job.description}"
        )

    return "\n\n".join(
        parts
    ).strip()


def get_job_application_source(
    discovered_job,
):
    valid_sources = dict(
        JobApplication.SOURCE_CHOICES
    )

    source = (
        discovered_job.source
        or ""
    ).strip()

    if source in valid_sources:
        return source

    if "other" in valid_sources:
        return "other"

    if valid_sources:
        return next(
            iter(
                valid_sources.keys()
            )
        )

    return source or "other"


def has_profile_ranking(
    recommendation,
):
    reason = (
        recommendation.match_reason
        or ""
    )

    return reason.startswith(
        AI_REASON_PREFIX
    )


def clean_profile_reason(
    recommendation,
):
    reason = (
        recommendation.match_reason
        or ""
    )

    if reason.startswith(
        AI_REASON_PREFIX
    ):
        return reason[
            len(
                AI_REASON_PREFIX
            ):
        ].strip()

    return reason


def empty_refresh_totals():
    return {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
    }


def add_import_result(
    totals,
    result,
):
    for key in [
        "fetched",
        "created",
        "updated",
        "skipped",
        "failed",
    ]:
        totals[key] += int(
            result.get(
                key,
                0,
            )
            or 0
        )


def normalize_target_location(
    location,
):
    """
    Country-wide Germany values should not be passed
    as city/location filters to sources whose German
    endpoint already scopes the market to Germany.
    """

    if not location:
        return ""

    value = str(
        location
    ).strip()

    normalized = (
        value
        .lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )

    if normalized in {
        "germany",
        "deutschland",
        "de",
    }:
        return ""

    return value


# =========================================================
# DISCOVER PAGE
# =========================================================

@login_required
def discover_jobs_view(request):
    user = request.user

    targets = (
        user.job_search_targets
        .filter(
            active=True
        )
        .order_by(
            "title"
        )
    )

    matches = shortlist_for_user(
        user=user,
        per_target_limit=50,
        final_limit=30,
    )

    recommendations = []
    recommendations_needing_ai = []

    for item in matches:
        discovered_job = item["job"]
        target = item["target"]

        recommendation, created = (
            JobRecommendation.objects.get_or_create(
                user=user,
                job=discovered_job,
                defaults={
                    "target": target,
                    "match_score": 0,
                    "match_reason": "",
                },
            )
        )

        if (
            recommendation.target_id
            != target.id
        ):
            recommendation.target = target

            recommendation.save(
                update_fields=[
                    "target",
                    "updated_at",
                ]
            )

        if (
            recommendation.status
            == "not_interested"
        ):
            continue

        recommendations.append(
            recommendation
        )

        if not has_profile_ranking(
            recommendation
        ):
            recommendations_needing_ai.append(
                recommendation
            )

    # -----------------------------------------------------
    # PROFILE AI RANKING
    # -----------------------------------------------------

    if recommendations_needing_ai:
        profile, created = (
            Profile.objects.get_or_create(
                user=user
            )
        )

        jobs_to_rank = [
            recommendation.job
            for recommendation
            in recommendations_needing_ai
        ]

        try:
            ranked_results = (
                rank_jobs_for_profile(
                    profile=profile,
                    jobs=jobs_to_rank,
                )
            )

            for recommendation in (
                recommendations_needing_ai
            ):
                ranking = (
                    ranked_results.get(
                        recommendation.job_id
                    )
                )

                if ranking is None:
                    continue

                recommendation.match_score = (
                    round(
                        float(
                            ranking.score
                        ),
                        1,
                    )
                )

                recommendation.match_reason = (
                    f"{AI_REASON_PREFIX} "
                    f"{ranking.reason}"
                )

                recommendation.save(
                    update_fields=[
                        "match_score",
                        "match_reason",
                        "updated_at",
                    ]
                )

        except Exception as exc:
            print(
                "DISCOVERY PROFILE RANK ERROR:",
                repr(exc),
            )

            messages.warning(
                request,
                (
                    "Some new job matches could not "
                    "be profile-ranked right now."
                ),
            )

    # -----------------------------------------------------
    # DISPLAY RESULTS
    # -----------------------------------------------------

    display_recommendations = []

    for recommendation in recommendations:
        if not has_profile_ranking(
            recommendation
        ):
            continue

        recommendation.display_match_reason = (
            clean_profile_reason(
                recommendation
            )
        )

        score = float(
            recommendation.match_score
            or 0
        )

        if score >= 8:
            recommendation.profile_fit = "GOOD"

        elif score >= 6:
            recommendation.profile_fit = "POSSIBLE"

        else:
            recommendation.profile_fit = "WEAK"

        display_recommendations.append(
            recommendation
        )

    display_recommendations.sort(
        key=lambda recommendation: float(
            recommendation.match_score
            or 0
        ),
        reverse=True,
    )

    external_searches = (
        build_user_external_searches(
            user
        )
    )

    return render(
        request,
        "discovery/discover.html",
        {
            "targets": targets,

            "recommendations": (
                display_recommendations
            ),

            "recommendation_count": len(
                display_recommendations
            ),

            "external_searches": (
                external_searches
            ),

            "target_count": (
                user.job_search_targets.count()
            ),

            "max_job_targets": (
                MAX_JOB_TARGETS
            ),
        },
    )


# =========================================================
# REFRESH DISCOVERY
# =========================================================

@login_required
@require_POST
def refresh_discovery_view(request):
    """
    Refresh all internal discovery sources.

    Sources:
    - Arbeitnow
    - Arbeitsagentur
    - Adzuna
    - Jooble

    Arbeitsagentur, Adzuna and Jooble search
    every active target independently.

    Arbeitnow is refreshed once as a shared feed.

    One source failure must not stop the rest.
    """

    user = request.user

    active_targets = list(
        JobSearchTarget.objects.filter(
            user=user,
            active=True,
        ).order_by(
            "title"
        )
    )

    if not active_targets:
        messages.warning(
            request,
            (
                "Please create and activate at least "
                "one Job Target before refreshing jobs."
            ),
        )

        return redirect(
            "discover_jobs"
        )

    # =====================================================
    # STATS
    # =====================================================

    grand_totals = (
        empty_refresh_totals()
    )

    arbeitnow_totals = (
        empty_refresh_totals()
    )

    arbeitsagentur_totals = (
        empty_refresh_totals()
    )

    adzuna_totals = (
        empty_refresh_totals()
    )

    jooble_totals = (
        empty_refresh_totals()
    )

    errors = []

    # =====================================================
    # 1. ARBEITNOW
    # =====================================================

    try:
        arbeitnow_result = (
            import_from_source(
                ArbeitnowJobSource(),
                pages=2,
            )
        )

        add_import_result(
            arbeitnow_totals,
            arbeitnow_result,
        )

        add_import_result(
            grand_totals,
            arbeitnow_result,
        )

    except Exception as exc:
        print(
            "ARBEITNOW REFRESH ERROR:",
            repr(exc),
        )

        errors.append(
            "Arbeitnow"
        )

        arbeitnow_totals[
            "failed"
        ] += 1

        grand_totals[
            "failed"
        ] += 1

    # =====================================================
    # 2. TARGET-BASED SOURCES
    # =====================================================

    for target in active_targets:
        query = (
            target.title
            or ""
        ).strip()

        raw_location = (
            target.location
            or ""
        ).strip()

        normalized_location = (
            normalize_target_location(
                raw_location
            )
        )

        if not query:
            continue

        # -------------------------------------------------
        # ARBEITSAGENTUR
        # -------------------------------------------------

        try:
            ba_source = (
                ArbeitsagenturJobSource(
                    fetch_details=True,
                    reuse_existing_description=True,
                )
            )

            ba_result = (
                import_from_source(
                    ba_source,
                    query=query,
                    location=(
                        raw_location
                        or None
                    ),
                    pages=1,
                )
            )

            add_import_result(
                arbeitsagentur_totals,
                ba_result,
            )

            add_import_result(
                grand_totals,
                ba_result,
            )

            print(
                "ARBEITSAGENTUR TARGET REFRESH:",
                {
                    "target": query,
                    "location": raw_location,
                    "result": ba_result,
                },
            )

        except Exception as exc:
            print(
                "ARBEITSAGENTUR TARGET ERROR:",
                query,
                raw_location,
                repr(exc),
            )

            errors.append(
                (
                    "Arbeitsagentur "
                    f"({query})"
                )
            )

            arbeitsagentur_totals[
                "failed"
            ] += 1

            grand_totals[
                "failed"
            ] += 1

        # -------------------------------------------------
        # ADZUNA
        # -------------------------------------------------

        try:
            adzuna_source = (
                AdzunaJobSource(
                    results_per_page=50,
                )
            )

            adzuna_result = (
                import_from_source(
                    adzuna_source,
                    query=query,
                    location=(
                        normalized_location
                        or None
                    ),
                    pages=1,
                )
            )

            add_import_result(
                adzuna_totals,
                adzuna_result,
            )

            add_import_result(
                grand_totals,
                adzuna_result,
            )

            print(
                "ADZUNA TARGET REFRESH:",
                {
                    "target": query,
                    "location": normalized_location,
                    "result": adzuna_result,
                },
            )

        except Exception as exc:
            print(
                "ADZUNA TARGET ERROR:",
                query,
                normalized_location,
                repr(exc),
            )

            errors.append(
                (
                    "Adzuna "
                    f"({query})"
                )
            )

            adzuna_totals[
                "failed"
            ] += 1

            grand_totals[
                "failed"
            ] += 1

        # -------------------------------------------------
        # JOOBLE
        # -------------------------------------------------

        try:
            jooble_source = (
                JoobleJobSource()
            )

            jooble_result = (
                import_from_source(
                    jooble_source,
                    query=query,
                    location=(
                        normalized_location
                        or None
                    ),
                    pages=1,
                )
            )

            add_import_result(
                jooble_totals,
                jooble_result,
            )

            add_import_result(
                grand_totals,
                jooble_result,
            )

            print(
                "JOOBLE TARGET REFRESH:",
                {
                    "target": query,
                    "location": normalized_location,
                    "result": jooble_result,
                },
            )

        except Exception as exc:
            print(
                "JOOBLE TARGET ERROR:",
                query,
                normalized_location,
                repr(exc),
            )

            errors.append(
                (
                    "Jooble "
                    f"({query})"
                )
            )

            jooble_totals[
                "failed"
            ] += 1

            grand_totals[
                "failed"
            ] += 1

    # =====================================================
    # SUMMARY
    # =====================================================

    fetched = (
        grand_totals[
            "fetched"
        ]
    )

    created = (
        grand_totals[
            "created"
        ]
    )

    updated = (
        grand_totals[
            "updated"
        ]
    )

    source_summary = (
        "Arbeitnow: "
        f"{arbeitnow_totals['created']} new, "
        f"{arbeitnow_totals['updated']} updated"
        " | "
        "Arbeitsagentur: "
        f"{arbeitsagentur_totals['created']} new, "
        f"{arbeitsagentur_totals['updated']} updated"
        " | "
        "Adzuna: "
        f"{adzuna_totals['created']} new, "
        f"{adzuna_totals['updated']} updated"
        " | "
        "Jooble: "
        f"{jooble_totals['created']} new, "
        f"{jooble_totals['updated']} updated"
    )

    if errors:
        messages.warning(
            request,
            (
                "Job refresh completed with some "
                "source errors. "
                f"{fetched} fetched, "
                f"{created} new, "
                f"{updated} updated. "
                f"{source_summary}"
            ),
        )

    elif created > 0:
        messages.success(
            request,
            (
                "Job discovery refreshed successfully. "
                f"{fetched} jobs fetched, "
                f"{created} new, "
                f"{updated} updated. "
                f"{source_summary}"
            ),
        )

    else:
        messages.success(
            request,
            (
                "Job discovery is up to date. "
                f"{fetched} jobs fetched, "
                f"{updated} updated. "
                f"{source_summary}"
            ),
        )

    return redirect(
        "discover_jobs"
    )


# =========================================================
# TARGETS
# =========================================================

@login_required
def targets_view(request):
    targets = (
        JobSearchTarget.objects.filter(
            user=request.user
        )
        .order_by(
            "-active",
            "title",
        )
    )

    return render(
        request,
        "discovery/targets.html",
        {
            "targets": targets,

            "target_count": (
                targets.count()
            ),

            "max_job_targets": (
                MAX_JOB_TARGETS
            ),
        },
    )


@login_required
def add_target_view(request):
    current_count = (
        JobSearchTarget.objects.filter(
            user=request.user
        ).count()
    )

    if (
        current_count
        >= MAX_JOB_TARGETS
    ):
        messages.warning(
            request,
            (
                f"You can create up to "
                f"{MAX_JOB_TARGETS} job targets."
            ),
        )

        return redirect(
            "discovery_targets"
        )

    if request.method == "POST":
        form = JobSearchTargetForm(
            request.POST
        )

        if form.is_valid():
            target = form.save(
                commit=False
            )

            target.user = request.user

            target.save()

            messages.success(
                request,
                "Job target created successfully.",
            )

            return redirect(
                "discovery_targets"
            )

    else:
        form = JobSearchTargetForm(
            initial={
                "radius_km": 50,
                "remote": True,
                "minimum_match_score": 6.0,
                "active": True,
            }
        )

    return render(
        request,
        "discovery/target_form.html",
        {
            "form": form,
            "page_title": "Add Job Target",
            "submit_label": "Add Target",
            "is_edit": False,
        },
    )


@login_required
def edit_target_view(
    request,
    target_id,
):
    target = get_object_or_404(
        JobSearchTarget,
        id=target_id,
        user=request.user,
    )

    if request.method == "POST":
        form = JobSearchTargetForm(
            request.POST,
            instance=target,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Job target updated successfully.",
            )

            return redirect(
                "discovery_targets"
            )

    else:
        form = JobSearchTargetForm(
            instance=target
        )

    return render(
        request,
        "discovery/target_form.html",
        {
            "form": form,
            "target": target,
            "page_title": "Edit Job Target",
            "submit_label": "Save Changes",
            "is_edit": True,
        },
    )


@login_required
@require_POST
def toggle_target_view(
    request,
    target_id,
):
    target = get_object_or_404(
        JobSearchTarget,
        id=target_id,
        user=request.user,
    )

    target.active = not target.active

    target.save(
        update_fields=[
            "active",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "active": target.active,

            "message": (
                "Target activated."
                if target.active
                else "Target paused."
            ),
        }
    )


@login_required
@require_POST
def delete_target_view(
    request,
    target_id,
):
    target = get_object_or_404(
        JobSearchTarget,
        id=target_id,
        user=request.user,
    )

    target.delete()

    return JsonResponse(
        {
            "ok": True,
            "message": "Job target deleted.",
        }
    )


# =========================================================
# RECOMMENDATION ACTIONS
# =========================================================

@login_required
@require_POST
def save_recommendation_view(
    request,
    recommendation_id,
):
    recommendation = get_object_or_404(
        JobRecommendation,
        id=recommendation_id,
        user=request.user,
    )

    if (
        recommendation.status
        != "analyzed"
    ):
        recommendation.status = "saved"

        recommendation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return JsonResponse(
        {
            "ok": True,
            "status": recommendation.status,
            "message": "Job saved successfully.",
        }
    )


@login_required
@require_POST
def not_interested_view(
    request,
    recommendation_id,
):
    recommendation = get_object_or_404(
        JobRecommendation,
        id=recommendation_id,
        user=request.user,
    )

    recommendation.status = (
        "not_interested"
    )

    recommendation.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "ok": True,

            "status": (
                "not_interested"
            ),

            "message": (
                "Job removed from recommendations."
            ),
        }
    )


# =========================================================
# FULL ANALYZE
# =========================================================

@login_required
@require_POST
def analyze_recommendation_view(
    request,
    recommendation_id,
):
    recommendation = get_object_or_404(
        JobRecommendation.objects.select_related(
            "job",
            "target",
        ),
        id=recommendation_id,
        user=request.user,
    )

    discovered_job = (
        recommendation.job
    )

    if (
        recommendation.status
        == "analyzed"
        and discovered_job.url
    ):
        existing_application = (
            JobApplication.objects.filter(
                user=request.user,
                job_url=discovered_job.url,
            )
            .order_by(
                "-created_at"
            )
            .first()
        )

        if existing_application:
            return redirect(
                "job_result",
                job_id=existing_application.id,
            )

    if not discovered_job.description:
        messages.error(
            request,
            (
                "This vacancy does not contain enough "
                "job-description text to analyze."
            ),
        )

        return redirect(
            "discover_jobs"
        )

    profile, created = (
        Profile.objects.get_or_create(
            user=request.user
        )
    )

    job_description = (
        build_analysis_description(
            discovered_job
        )
    )

    try:
        result = analyze_job(
            profile=profile,

            job_description=job_description,

            analysis_language=(
                request.session.get(
                    "ui_language",
                    "en",
                )
            ),
        )

        application_source = (
            get_job_application_source(
                discovered_job
            )
        )

        application = (
            JobApplication.objects.create(
                user=request.user,

                company=(
                    discovered_job.company
                    or result.company
                    or ""
                ),

                job_title=(
                    discovered_job.title
                    or result.job_title
                    or ""
                ),

                city=(
                    discovered_job.location
                    or result.city
                    or ""
                ),

                job_description=(
                    job_description
                ),

                job_url=(
                    discovered_job.url
                    or ""
                ),

                source=(
                    application_source
                ),

                score=result.score,

                decision=result.decision,

                employer_type=(
                    result.employer_type
                ),

                zeitarbeit_risk=(
                    result.zeitarbeit_risk
                ),

                strong_matches=(
                    result.strong_matches
                ),

                gaps=result.gaps,

                risks=result.risks,

                recommended_cv=(
                    result.recommended_cv
                ),

                do_not_claim=(
                    result.do_not_claim
                ),

                summary=result.summary,
            )
        )

        recommendation.status = "analyzed"

        recommendation.match_score = (
            result.score
        )

        recommendation.match_reason = (
            f"{AI_REASON_PREFIX} "
            "Full profile analysis completed."
        )

        recommendation.save(
            update_fields=[
                "status",
                "match_score",
                "match_reason",
                "updated_at",
            ]
        )

        return redirect(
            "job_result",
            job_id=application.id,
        )

    except Exception as exc:
        print(
            "DISCOVERY ANALYZE ERROR:",
            repr(exc),
        )

        messages.error(
            request,
            (
                "The job analysis could not be completed. "
                "Please check your API configuration "
                "and try again."
            ),
        )

        return redirect(
            "discover_jobs"
        )