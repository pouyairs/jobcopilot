from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "register/",
        views.register_view,
        name="register"
    ),

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
    ),

    path(
        "profile/",
        views.profile_view,
        name="profile"
    ),

    path(
        "language/<str:lang>/",
        views.set_language,
        name="set_language"
    ),
    path(
    "profile/<str:section>/add/",
    views.profile_item_form,
    name="profile_item_add"
),

path(
    "profile/<str:section>/<int:item_id>/edit/",
    views.profile_item_form,
    name="profile_item_edit"
),

path(
    "profile/<str:section>/<int:item_id>/delete/",
    views.delete_profile_item,
    name="profile_item_delete"
),
path(
    "profile/upload-cv/",
    views.upload_cv_view,
    name="upload_cv"
),

path(
    "profile/upload-cv/preview/",
    views.cv_import_preview_view,
    name="cv_import_preview"
),
]