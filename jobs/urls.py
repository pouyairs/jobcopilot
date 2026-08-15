from django.urls import path

from . import views
from . import followup_views


urlpatterns = [

    # =====================================================
    # JOB ANALYSIS
    # =====================================================

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


    # =====================================================
    # APPLICATIONS
    # =====================================================

    path(
        "applications/",
        views.applications_view,
        name="applications",
    ),


    # =====================================================
    # UPDATE STATUS
    # =====================================================

    path(
        "applications/<int:job_id>/status/",
        views.update_status_view,
        name="update_status",
    ),


    # =====================================================
    # EDIT COMPANY / JOB TITLE / CITY
    # =====================================================

    path(
        "applications/<int:job_id>/details/",
        views.update_application_details_view,
        name="update_application_details",
    ),


    # =====================================================
    # FOLLOW-UP
    # =====================================================

    path(
        "applications/<int:job_id>/follow-up/",
        followup_views.update_follow_up,
        name="update_follow_up",
    ),


    # =====================================================
    # DELETE
    # =====================================================

    path(
        "applications/<int:job_id>/delete/",
        followup_views.delete_application,
        name="delete_application",
    ),

]