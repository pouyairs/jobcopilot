import re
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.models import Profile

from .ai.analyzer import analyze_job
from .forms import JobAnalysisForm
from .models import JobApplication


# =========================================================
# HELPERS
# =========================================================

def normalize_text(value):
    """
    Normalize text so we can safely check whether an AI-extracted
    job title actually appears in the pasted vacancy.
    """

    if not value:
        return ""

    value = value.casefold()

    value = re.sub(
        r"[^a-z0-9äöüßà-ÿ]+",
        " ",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def verified_extracted_title(
    job_title,
    job_description,
):
    """
    Do not store a hallucinated job title.

    The title returned by AI is accepted only when the normalized
    title can actually be found inside the pasted vacancy.

    If the vacancy does not contain a clear title, return an empty
    string. The user can later correct it manually from
    My Applications.
    """

    title = (
        job_title or ""
    ).strip()

    description = (
        job_description or ""
    ).strip()

    if not title:
        return ""

    normalized_title = normalize_text(
        title
    )

    normalized_description = normalize_text(
        description
    )

    if not normalized_title:
        return ""

    if normalized_title in normalized_description:
        return title

    return ""


def redirect_back_or_applications(
    request,
):
    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "applications",
        )
    )


# =========================================================
# ANALYZE JOB
# =========================================================

@login_required
def analyze_job_view(request):

    profile, created = (
        Profile.objects.get_or_create(
            user=request.user
        )
    )

    error = None

    if request.method == "POST":

        form = JobAnalysisForm(
            request.POST
        )

        if form.is_valid():

            job_description = (
                form.cleaned_data[
                    "job_description"
                ]
            )

            source = (
                form.cleaned_data[
                    "source"
                ]
            )

            job_url = (
                form.cleaned_data[
                    "job_url"
                ]
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

                # -------------------------------------------------
                # JOB TITLE SAFETY
                # -------------------------------------------------
                #
                # AI must not invent a vacancy title.
                # If its extracted title does not actually appear
                # in the pasted vacancy, we keep the title empty.
                #

                safe_job_title = (
                    verified_extracted_title(
                        result.job_title,
                        job_description,
                    )
                )

                job = (
                    JobApplication.objects.create(
                        user=request.user,

                        company=(
                            result.company
                            or ""
                        ),

                        job_title=(
                            safe_job_title
                        ),

                        city=(
                            result.city
                            or ""
                        ),

                        job_description=(
                            job_description
                        ),

                        job_url=job_url,

                        source=source,

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

                        gaps=(
                            result.gaps
                        ),

                        risks=(
                            result.risks
                        ),

                        recommended_cv=(
                            result.recommended_cv
                        ),

                        do_not_claim=(
                            result.do_not_claim
                        ),

                        summary=(
                            result.summary
                        ),
                    )
                )

                return redirect(
                    "job_result",
                    job_id=job.id,
                )

            except Exception as exc:

                print(
                    "AI ERROR:",
                    repr(exc),
                )

                error = (
                    "The job analysis could not be completed. "
                    "Please check your API configuration "
                    "and try again."
                )

    else:

        form = JobAnalysisForm()

    return render(
        request,
        "jobs/analyze.html",
        {
            "form": form,
            "error": error,
        },
    )


# =========================================================
# ANALYSIS RESULT
# =========================================================

@login_required
def job_result_view(
    request,
    job_id,
):

    job = get_object_or_404(
        JobApplication,
        id=job_id,
        user=request.user,
    )

    return render(
        request,
        "jobs/result.html",
        {
            "job": job,
        },
    )


# =========================================================
# MY APPLICATIONS
# =========================================================

@login_required
def applications_view(request):

    applications = (
        JobApplication.objects.filter(
            user=request.user
        )
    )

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    query = (
        request.GET.get(
            "q",
            "",
        )
        .strip()
    )

    if query:

        applications = (
            applications.filter(
                Q(
                    company__icontains=query
                )
                |
                Q(
                    job_title__icontains=query
                )
            )
        )

    # -----------------------------------------------------
    # CITY
    # -----------------------------------------------------

    city = (
        request.GET.get(
            "city",
            "",
        )
        .strip()
    )

    if city:

        applications = (
            applications.filter(
                city__icontains=city
            )
        )

    # -----------------------------------------------------
    # SOURCE
    # -----------------------------------------------------

    source = (
        request.GET.get(
            "source",
            "",
        )
        .strip()
    )

    valid_sources = dict(
        JobApplication.SOURCE_CHOICES
    )

    if source in valid_sources:

        applications = (
            applications.filter(
                source=source
            )
        )

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    status = (
        request.GET.get(
            "status",
            "",
        )
        .strip()
    )

    valid_statuses = dict(
        JobApplication.STATUS_CHOICES
    )

    if status in valid_statuses:

        applications = (
            applications.filter(
                status=status
            )
        )

    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

    score_min = (
        request.GET.get(
            "score_min",
            "",
        )
        .strip()
    )

    if score_min:

        try:

            score_value = float(
                score_min
            )

            applications = (
                applications.filter(
                    score__gte=score_value
                )
            )

        except ValueError:
            pass

    # -----------------------------------------------------
    # FOLLOW-UP
    # -----------------------------------------------------

    followup = (
        request.GET.get(
            "followup",
            "",
        )
        .strip()
    )

    if followup == "with":

        applications = (
            applications.filter(
                follow_up_date__isnull=False
            )
        )

    elif followup == "without":

        applications = (
            applications.filter(
                follow_up_date__isnull=True
            )
        )

    elif followup == "due":

        applications = (
            applications.filter(
                follow_up_date__isnull=False,
                follow_up_date__lte=(
                    date.today()
                ),
            )
        )

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    sort = request.GET.get(
        "sort",
        "newest",
    )

    sort_options = {
        "newest": "-created_at",
        "oldest": "created_at",
        "score_high": "-score",
        "score_low": "score",
        "company": "company",
    }

    applications = (
        applications.order_by(
            sort_options.get(
                sort,
                "-created_at",
            )
        )
    )

    # -----------------------------------------------------
    # ROWS / PAGINATION
    # -----------------------------------------------------

    rows = request.GET.get(
        "rows",
        "50",
    )

    allowed_rows = [
        "25",
        "50",
        "100",
        "all",
    ]

    if rows not in allowed_rows:
        rows = "50"

    page_obj = None

    if rows == "all":

        jobs = applications

    else:

        paginator = Paginator(
            applications,
            int(rows),
        )

        page_number = (
            request.GET.get(
                "page"
            )
        )

        page_obj = (
            paginator.get_page(
                page_number
            )
        )

        jobs = (
            page_obj.object_list
        )

    return render(
        request,
        "jobs/applications.html",
        {
            "jobs": jobs,

            # compatibility with older templates
            "applications": jobs,

            "page_obj": page_obj,

            "source_choices": (
                JobApplication.SOURCE_CHOICES
            ),

            "status_choices": (
                JobApplication.STATUS_CHOICES
            ),

            "filters": {
                "q": query,
                "city": city,
                "source": source,
                "status": status,
                "score_min": score_min,
                "followup": followup,
                "sort": sort,
                "rows": rows,
            },
        },
    )


# =========================================================
# UPDATE STATUS
# =========================================================

@login_required
def update_status_view(
    request,
    job_id,
):

    job = get_object_or_404(
        JobApplication,
        id=job_id,
        user=request.user,
    )

    if request.method != "POST":

        if (
            request.headers.get(
                "x-requested-with"
            )
            == "XMLHttpRequest"
        ):

            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "POST request required."
                    ),
                },
                status=405,
            )

        return redirect_back_or_applications(
            request
        )

    new_status = (
        request.POST.get(
            "status",
            "",
        )
        .strip()
    )

    valid_statuses = dict(
        JobApplication.STATUS_CHOICES
    )

    if new_status not in valid_statuses:

        if (
            request.headers.get(
                "x-requested-with"
            )
            == "XMLHttpRequest"
        ):

            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "Invalid application status."
                    ),
                },
                status=400,
            )

        return redirect_back_or_applications(
            request
        )

    # -----------------------------------------------------
    # UPDATE STATUS
    # -----------------------------------------------------

    job.status = new_status

    # If the user moves the application away from
    # "Not Applied", automatically record today's date
    # if an applied date does not already exist.

    if (
        new_status != "not_applied"
        and job.applied_date is None
    ):

        job.applied_date = (
            date.today()
        )

    # Going back to "Not Applied" removes the applied date.

    if new_status == "not_applied":

        job.applied_date = None

    job.save(
        update_fields=[
            "status",
            "applied_date",
            "updated_at",
        ]
    )

    # -----------------------------------------------------
    # AJAX RESPONSE
    # -----------------------------------------------------

    if (
        request.headers.get(
            "x-requested-with"
        )
        == "XMLHttpRequest"
    ):

        return JsonResponse(
            {
                "ok": True,

                "status": (
                    job.status
                ),

                "status_label": (
                    job.get_status_display()
                ),

                "applied_date": (
                    job.applied_date.strftime(
                        "%d.%m.%Y"
                    )
                    if job.applied_date
                    else ""
                ),
            }
        )

    return redirect_back_or_applications(
        request
    )


# =========================================================
# UPDATE COMPANY / JOB TITLE / CITY
# =========================================================

@login_required
def update_application_details_view(
    request,
    job_id,
):

    job = get_object_or_404(
        JobApplication,
        id=job_id,
        user=request.user,
    )

    if request.method != "POST":

        return redirect_back_or_applications(
            request
        )

    company = (
        request.POST.get(
            "company",
            "",
        )
        .strip()
    )

    job_title = (
        request.POST.get(
            "job_title",
            "",
        )
        .strip()
    )

    city = (
        request.POST.get(
            "city",
            "",
        )
        .strip()
    )

    # Avoid extremely long accidental input.
    company = company[:255]
    job_title = job_title[:255]
    city = city[:255]

    job.company = company
    job.job_title = job_title
    job.city = city

    job.save(
        update_fields=[
            "company",
            "job_title",
            "city",
            "updated_at",
        ]
    )

    if (
        request.headers.get(
            "x-requested-with"
        )
        == "XMLHttpRequest"
    ):

        return JsonResponse(
            {
                "ok": True,
                "company": job.company,
                "job_title": job.job_title,
                "city": job.city,
            }
        )

    return redirect_back_or_applications(
        request
    )