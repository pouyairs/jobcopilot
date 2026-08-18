from django.urls import path

from . import views


urlpatterns = [
    # =====================================================
    # DISCOVERY
    # =====================================================

    path(
        "",
        views.discover_jobs_view,
        name="discover_jobs",
    ),

    path(
        "refresh/",
        views.refresh_discovery_view,
        name="refresh_discovery",
    ),

    # =====================================================
    # JOB TARGETS
    # =====================================================

    path(
        "targets/",
        views.targets_view,
        name="discovery_targets",
    ),

    path(
        "targets/add/",
        views.add_target_view,
        name="add_discovery_target",
    ),

    path(
        "targets/<int:target_id>/edit/",
        views.edit_target_view,
        name="edit_discovery_target",
    ),

    path(
        "targets/<int:target_id>/toggle/",
        views.toggle_target_view,
        name="toggle_discovery_target",
    ),

    path(
        "targets/<int:target_id>/delete/",
        views.delete_target_view,
        name="delete_discovery_target",
    ),

    # =====================================================
    # RECOMMENDATIONS
    # =====================================================

    path(
        "recommendation/<int:recommendation_id>/save/",
        views.save_recommendation_view,
        name="save_recommendation",
    ),

    path(
        "recommendation/<int:recommendation_id>/not-interested/",
        views.not_interested_view,
        name="not_interested",
    ),

    path(
        "recommendation/<int:recommendation_id>/analyze/",
        views.analyze_recommendation_view,
        name="analyze_recommendation",
    ),
]