from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    get_object_or_404,
    redirect,
)

from .models import JobApplication


# =========================================================
# UPDATE FOLLOW-UP DATE
# =========================================================

@login_required
def update_follow_up(
    request,
    job_id
):

    job = get_object_or_404(
        JobApplication,
        id=job_id,
        user=request.user
    )

    if request.method == "POST":

        follow_up_date = request.POST.get(
            "follow_up_date",
            ""
        ).strip()

        if follow_up_date:

            job.follow_up_date = (
                follow_up_date
            )

        else:

            job.follow_up_date = None

        job.save(
            update_fields=[
                "follow_up_date"
            ]
        )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "applications"
        )
    )


# =========================================================
# DELETE APPLICATION
# =========================================================

@login_required
def delete_application(
    request,
    job_id
):

    job = get_object_or_404(
        JobApplication,
        id=job_id,
        user=request.user
    )

    if request.method == "POST":
        job.delete()

    return redirect(
        "applications"
    )