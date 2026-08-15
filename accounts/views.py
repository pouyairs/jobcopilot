from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,

)
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm

from .forms import RegisterForm, ProfileForm
from .models import Profile
from django.http import Http404
from .utils.cv_reader import extract_cv_text
from .ai.cv_parser import parse_cv_with_ai

from .models import (
    Profile,
    Experience,
    Education,
    Skill,
    LanguageEntry,
    Certification,
)

from .forms import (
    RegisterForm,
    ProfileForm,
    ExperienceForm,
    EducationForm,
    SkillForm,
    LanguageEntryForm,
    CertificationForm,
    CVUploadForm,
)

def home(request):
    return render(
        request,
        "home.html"
    )

    if request.user.is_authenticated:
        return redirect("dashboard")

    return render(request, "home.html")


def register_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save()

            Profile.objects.create(
                user=user,
                preferred_language=request.session.get(
                    "ui_language",
                    "en"
                )
            )

            login(request, user)

            return redirect("profile")

    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form}
    )


def login_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(
        request,
        data=request.POST or None
    )

    if request.method == "POST" and form.is_valid():

        user = form.get_user()

        login(request, user)

        profile, created = Profile.objects.get_or_create(
            user=user
        )

        request.session["ui_language"] = (
            profile.preferred_language
        )

        return redirect("dashboard")

    return render(
        request,
        "accounts/login.html",
        {"form": form}
    )


@login_required
def logout_view(request):

    if request.method == "POST":
        logout(request)

    return redirect("home")


@login_required
def dashboard(request):

    return render(
        request,
        "accounts/dashboard.html"
    )


@login_required
@login_required
def profile_view(request):

    profile, created = Profile.objects.get_or_create(
        user=request.user
    )

    saved = False

    if request.method == "POST":

        form = ProfileForm(
            request.POST,
            instance=profile
        )

        if form.is_valid():
            form.save()
            saved = True

    else:
        form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "profile": profile,
            "saved": saved,
        }
    )

    profile, created = Profile.objects.get_or_create(
        user=request.user
    )

    saved = False

    if request.method == "POST":

        form = ProfileForm(
            request.POST,
            instance=profile
        )

        if form.is_valid():

            form.save()

            saved = True

    else:

        form = ProfileForm(
            instance=profile
        )

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "saved": saved,
        }
    )


def set_language(request, lang):

    if lang not in ["en", "fa"]:
        lang = "en"

    request.session["ui_language"] = lang

    if request.user.is_authenticated:

        profile, created = Profile.objects.get_or_create(
            user=request.user
        )

        profile.preferred_language = lang
        profile.save(
            update_fields=["preferred_language"]
        )

        return redirect("dashboard")

    return redirect("home")
PROFILE_SECTIONS = {

    "experience": {
        "model": Experience,
        "form": ExperienceForm,
        "title": "Work Experience",
    },

    "education": {
        "model": Education,
        "form": EducationForm,
        "title": "Education",
    },

    "skill": {
        "model": Skill,
        "form": SkillForm,
        "title": "Skill",
    },

    "language": {
        "model": LanguageEntry,
        "form": LanguageEntryForm,
        "title": "Language",
    },

    "certification": {
        "model": Certification,
        "form": CertificationForm,
        "title": "Certification",
    },
}


@login_required
def profile_item_form(
    request,
    section,
    item_id=None
):

    config = PROFILE_SECTIONS.get(section)

    if not config:
        raise Http404

    profile, created = Profile.objects.get_or_create(
        user=request.user
    )

    model = config["model"]
    form_class = config["form"]

    item = None

    if item_id:

        item = get_object_or_404(
            model,
            id=item_id,
            profile=profile
        )

    if request.method == "POST":

        form = form_class(
            request.POST,
            instance=item
        )

        if form.is_valid():

            new_item = form.save(commit=False)

            new_item.profile = profile

            new_item.save()

            return redirect("profile")

    else:

        form = form_class(
            instance=item
        )

    return render(
        request,
        "accounts/profile_item_form.html",
        {
            "form": form,
            "section": section,
            "item": item,
            "page_title": config["title"],
        }
    )


@login_required
def delete_profile_item(
    request,
    section,
    item_id
):

    config = PROFILE_SECTIONS.get(section)

    if not config:
        raise Http404

    profile = get_object_or_404(
        Profile,
        user=request.user
    )

    item = get_object_or_404(
        config["model"],
        id=item_id,
        profile=profile
    )

    if request.method == "POST":
        item.delete()

    return redirect("profile")
@login_required
def upload_cv_view(request):

    error = None

    if request.method == "POST":

        form = CVUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            uploaded_file = (
                form.cleaned_data["cv_file"]
            )

            try:

                cv_text = extract_cv_text(
                    uploaded_file
                )

                parsed = parse_cv_with_ai(
                    cv_text
                )

                request.session[
                    "cv_import_preview"
                ] = parsed.model_dump()

                return redirect(
                    "cv_import_preview"
                )

            except Exception as exc:

                print(
                    "CV IMPORT ERROR:",
                    repr(exc)
                )

                error = str(exc)

    else:

        form = CVUploadForm()

    return render(
        request,
        "accounts/upload_cv.html",
        {
            "form": form,
            "error": error,
        }
    )


@login_required
def cv_import_preview_view(request):

    data = request.session.get(
        "cv_import_preview"
    )

    if not data:
        return redirect("upload_cv")

    if request.method == "POST":

        profile, created = (
            Profile.objects.get_or_create(
                user=request.user
            )
        )

        # Update basic profile data
        if data.get("full_name"):
            profile.full_name = (
                data["full_name"]
            )

        if data.get("city"):
            profile.city = data["city"]

        if data.get("country"):
            profile.country = (
                data["country"]
            )

        if data.get(
            "professional_summary"
        ):
            profile.professional_summary = (
                data[
                    "professional_summary"
                ]
            )

        profile.save()


        # Replace current structured data
        profile.experiences.all().delete()
        profile.educations.all().delete()
        profile.skills.all().delete()
        profile.language_entries.all().delete()
        profile.certifications.all().delete()


        # Experiences
        for index, item in enumerate(
            data.get("experiences", [])
        ):

            Experience.objects.create(
                profile=profile,
                job_title=item.get(
                    "job_title",
                    ""
                ),
                company=item.get(
                    "company",
                    ""
                ),
                location=item.get(
                    "location",
                    ""
                ),
                start_date=item.get(
                    "start_date",
                    ""
                ),
                end_date=item.get(
                    "end_date",
                    ""
                ),
                description=item.get(
                    "description",
                    ""
                ),
                technologies=item.get(
                    "technologies",
                    ""
                ),
                order=index,
            )


        # Education
        for index, item in enumerate(
            data.get("educations", [])
        ):

            Education.objects.create(
                profile=profile,
                degree=item.get(
                    "degree",
                    ""
                ),
                institution=item.get(
                    "institution",
                    ""
                ),
                location=item.get(
                    "location",
                    ""
                ),
                start_date=item.get(
                    "start_date",
                    ""
                ),
                end_date=item.get(
                    "end_date",
                    ""
                ),
                details=item.get(
                    "details",
                    ""
                ),
                order=index,
            )


                # -------------------------
        # Skills
        # -------------------------

        skill_count = int(
            request.POST.get(
                "skill_count",
                0
            )
        )

        valid_levels = [
            "unclassified",
            "basic",
            "intermediate",
            "advanced",
            "expert",
        ]

        valid_sources = [
            "professional",
            "education",
            "project",
            "course",
            "self_taught",
            "unspecified",
        ]

        for index in range(skill_count):

            include = request.POST.get(
                f"skill_{index}_include"
            )

            if include != "1":
                continue

            name = request.POST.get(
                f"skill_{index}_name",
                ""
            ).strip()

            if not name:
                continue

            level = request.POST.get(
                f"skill_{index}_level",
                "unclassified"
            )

            source = request.POST.get(
                f"skill_{index}_source",
                "unspecified"
            )

            if level not in valid_levels:
                level = "unclassified"

            if source not in valid_sources:
                source = "unspecified"

            do_not_claim = (
                request.POST.get(
                    f"skill_{index}_do_not_claim"
                ) == "1"
            )

            Skill.objects.create(
                profile=profile,
                name=name,
                level=level,
                source=source,
                do_not_claim=do_not_claim,
            )

            if not item.get("name"):
                continue

            Skill.objects.create(
                profile=profile,
                name=item["name"],
                category=item.get(
                    "category",
                    "strong"
                ),
            )


               # -------------------------
        # Languages
        # -------------------------

        language_count = int(
            request.POST.get(
                "language_count",
                0
            )
        )

        valid_language_levels = [
            "unspecified",
            "A1",
            "A2",
            "B1",
            "B2",
            "C1",
            "C2",
            "native",
        ]

        for index in range(language_count):

            include = request.POST.get(
                f"language_{index}_include"
            )

            if include != "1":
                continue

            language = request.POST.get(
                f"language_{index}_language",
                ""
            ).strip()

            if not language:
                continue

            level = request.POST.get(
                f"language_{index}_level",
                "unspecified"
            )

            if level not in valid_language_levels:
                level = "unspecified"

            original_level = request.POST.get(
                f"language_{index}_original_level",
                ""
            ).strip()

            LanguageEntry.objects.create(
                profile=profile,
                language=language,
                level=level,
                original_level=original_level,
            )

            if not item.get("language"):
                continue

            LanguageEntry.objects.create(
                profile=profile,
                language=item[
                    "language"
                ],
                level=item.get(
                    "level",
                    ""
                ),
            )


        # Certifications
        for item in data.get(
            "certifications",
            []
        ):

            if not item.get("name"):
                continue

            Certification.objects.create(
                profile=profile,
                name=item["name"],
                issuer=item.get(
                    "issuer",
                    ""
                ),
                date=item.get(
                    "date",
                    ""
                ),
            )


        del request.session[
            "cv_import_preview"
        ]

        return redirect("profile")


    return render(
        request,
        "accounts/cv_import_preview.html",
        {
            "cv": data
        }
    )