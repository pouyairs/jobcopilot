"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView


urlpatterns = [

    # =====================================================
    # ADMIN
    # =====================================================

    path(
        "admin/",
        admin.site.urls
    ),


    # =====================================================
    # HOME / LANDING PAGE
    # =====================================================

    path(
        "",
        TemplateView.as_view(
            template_name="home.html"
        ),
        name="home"
    ),


    # =====================================================
    # ACCOUNTS
    # =====================================================

    path(
        "",
        include("accounts.urls")
    ),


    # =====================================================
    # JOBS
    # =====================================================

    path(
        "jobs/",
        include("jobs.urls")
    ),

]