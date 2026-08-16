from django.urls import path

from . import views
from . import followup_views
from . import cover_letter_views


urlpatterns = [
    path(
        "analyze/",
        views.analyze_job_view,
        name="analyze_job",
    ),

    path(
        "result/<int:job_id>/",
        views.job_result_view,
        name="job_result",
    ),

    path(
        "applications/",
        views.applications_view,
        name="applications",
    ),

    path(
        "applications/<int:job_id>/status/",
        views.update_status_view,
        name="update_status",
    ),

    path(
        "applications/<int:job_id>/details/",
        views.update_application_details_view,
        name="update_application_details",
    ),

    path(
        "applications/<int:job_id>/follow-up/",
        followup_views.update_follow_up,
        name="update_follow_up",
    ),

    path(
        "applications/<int:job_id>/delete/",
        followup_views.delete_application,
        name="delete_application",
    ),

    path(
        "applications/<int:job_id>/cover-letter/",
        cover_letter_views.cover_letter_view,
        name="cover_letter",
    ),
]