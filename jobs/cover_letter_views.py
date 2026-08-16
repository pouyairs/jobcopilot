from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from accounts.models import Profile

from .ai.cover_letter import (
    generate_cover_letter,
    improve_cover_letter,
)
from .models import (
    CoverLetter,
    JobApplication,
)


# =========================================================
# SETTINGS
# =========================================================

VALID_LANGUAGES = {
    "de",
    "en",
}

VALID_SIGNATURE_TYPES = {
    "typed",
    "uploaded",
}

MAX_SIGNATURE_SIZE = (
    2 * 1024 * 1024
)  # 2 MB


# =========================================================
# GENERAL HELPERS
# =========================================================

def get_default_signature_name(
    request,
    profile,
):
    profile_name = (
        getattr(
            profile,
            "full_name",
            "",
        )
        or ""
    ).strip()

    if profile_name:
        return profile_name

    user_full_name = (
        request.user.get_full_name()
        or ""
    ).strip()

    if user_full_name:
        return user_full_name

    return request.user.username


def clean_post_value(
    request,
    field_name,
    max_length=None,
):
    value = (
        request.POST.get(
            field_name,
            "",
        )
        or ""
    ).strip()

    if max_length:
        value = value[:max_length]

    return value


# =========================================================
# SIGNATURE
# =========================================================

def validate_signature_image(
    uploaded_file,
):
    if uploaded_file is None:
        return None

    if (
        uploaded_file.size
        > MAX_SIGNATURE_SIZE
    ):
        return (
            "Signature image is too large. "
            "Maximum size is 2 MB."
        )

    extension = (
        Path(
            uploaded_file.name
        )
        .suffix
        .lower()
    )

    if extension != ".png":
        return (
            "Signature image must be a PNG file."
        )

    content_type = (
        getattr(
            uploaded_file,
            "content_type",
            "",
        )
        or ""
    ).lower()

    valid_content_types = {
        "image/png",
        "image/x-png",
    }

    if (
        content_type
        and content_type
        not in valid_content_types
    ):
        return (
            "Signature image must be a valid PNG file."
        )

    return None


# =========================================================
# SAVE EDITABLE FIELDS
# =========================================================

def save_letter_fields(
    request,
    letter,
    profile,
):
    """
    Save everything the user can edit on the page.

    This includes:
    - recipient information
    - subject
    - letter content
    - signature settings

    Returns:
        None -> success
        str  -> validation error
    """

    # -----------------------------------------------------
    # RECIPIENT
    # -----------------------------------------------------

    letter.recipient_company = (
        clean_post_value(
            request,
            "recipient_company",
            200,
        )
    )

    letter.recipient_contact = (
        clean_post_value(
            request,
            "recipient_contact",
            200,
        )
    )

    letter.recipient_street = (
        clean_post_value(
            request,
            "recipient_street",
            250,
        )
    )

    letter.recipient_postal_code = (
        clean_post_value(
            request,
            "recipient_postal_code",
            30,
        )
    )

    letter.recipient_city = (
        clean_post_value(
            request,
            "recipient_city",
            150,
        )
    )

    # -----------------------------------------------------
    # LETTER
    # -----------------------------------------------------

    letter.subject = (
        clean_post_value(
            request,
            "subject",
            300,
        )
    )

    letter.content = (
        clean_post_value(
            request,
            "content",
        )
    )

    # -----------------------------------------------------
    # SIGNATURE
    # -----------------------------------------------------

    signature_type = (
        clean_post_value(
            request,
            "signature_type",
            20,
        )
        or "typed"
    )

    if (
        signature_type
        not in VALID_SIGNATURE_TYPES
    ):
        signature_type = "typed"

    signature_name = (
        clean_post_value(
            request,
            "signature_name",
            200,
        )
    )

    if not signature_name:
        signature_name = (
            get_default_signature_name(
                request,
                profile,
            )
        )

    uploaded_signature = (
        request.FILES.get(
            "signature_image"
        )
    )

    upload_error = (
        validate_signature_image(
            uploaded_signature
        )
    )

    if upload_error:
        return upload_error

    letter.signature_type = (
        signature_type
    )

    letter.signature_name = (
        signature_name
    )

    if uploaded_signature is not None:

        # Remove an older uploaded signature
        # before replacing it.

        if letter.signature_image:

            try:
                letter.signature_image.delete(
                    save=False
                )
            except Exception:
                pass

        letter.signature_image = (
            uploaded_signature
        )

        letter.signature_type = (
            "uploaded"
        )

    letter.save()

    return None


# =========================================================
# SAVE NON-LETTER SETTINGS BEFORE GENERATE
# =========================================================

def save_generation_settings(
    request,
    letter,
    profile,
):
    """
    Preserve manual recipient and signature information
    when Generate AI is clicked.

    We deliberately do NOT save subject/content here,
    because AI is about to generate them.
    """

    # -----------------------------------------------------
    # RECIPIENT
    # -----------------------------------------------------

    recipient_company = (
        clean_post_value(
            request,
            "recipient_company",
            200,
        )
    )

    recipient_contact = (
        clean_post_value(
            request,
            "recipient_contact",
            200,
        )
    )

    recipient_street = (
        clean_post_value(
            request,
            "recipient_street",
            250,
        )
    )

    recipient_postal_code = (
        clean_post_value(
            request,
            "recipient_postal_code",
            30,
        )
    )

    recipient_city = (
        clean_post_value(
            request,
            "recipient_city",
            150,
        )
    )

    if recipient_company:
        letter.recipient_company = (
            recipient_company
        )

    if recipient_contact:
        letter.recipient_contact = (
            recipient_contact
        )

    if recipient_street:
        letter.recipient_street = (
            recipient_street
        )

    if recipient_postal_code:
        letter.recipient_postal_code = (
            recipient_postal_code
        )

    if recipient_city:
        letter.recipient_city = (
            recipient_city
        )

    # -----------------------------------------------------
    # SIGNATURE
    # -----------------------------------------------------

    signature_type = (
        clean_post_value(
            request,
            "signature_type",
            20,
        )
        or "typed"
    )

    if (
        signature_type
        in VALID_SIGNATURE_TYPES
    ):
        letter.signature_type = (
            signature_type
        )

    signature_name = (
        clean_post_value(
            request,
            "signature_name",
            200,
        )
    )

    if signature_name:
        letter.signature_name = (
            signature_name
        )

    elif not letter.signature_name:
        letter.signature_name = (
            get_default_signature_name(
                request,
                profile,
            )
        )

    uploaded_signature = (
        request.FILES.get(
            "signature_image"
        )
    )

    upload_error = (
        validate_signature_image(
            uploaded_signature
        )
    )

    if upload_error:
        return upload_error

    if uploaded_signature is not None:

        if letter.signature_image:

            try:
                letter.signature_image.delete(
                    save=False
                )
            except Exception:
                pass

        letter.signature_image = (
            uploaded_signature
        )

        letter.signature_type = (
            "uploaded"
        )

    letter.save()

    return None


# =========================================================
# APPLY EXTRACTED RECIPIENT DATA
# =========================================================

def apply_generated_recipient_data(
    letter,
    result,
    job,
):
    """
    AI-extracted recipient information is used only
    when a non-empty value was returned.

    Existing manual values are preserved when AI returns
    an empty field.

    Company name may safely fall back to the company already
    stored on the analyzed JobApplication.

    We DO NOT use job.city as recipient_city automatically,
    because job location is not necessarily a postal address.
    """

    generated_company = (
        result.recipient_company
        or ""
    ).strip()

    generated_contact = (
        result.recipient_contact
        or ""
    ).strip()

    generated_street = (
        result.recipient_street
        or ""
    ).strip()

    generated_postal_code = (
        result.recipient_postal_code
        or ""
    ).strip()

    generated_city = (
        result.recipient_city
        or ""
    ).strip()

    if generated_company:

        letter.recipient_company = (
            generated_company
        )

    elif not letter.recipient_company:

        letter.recipient_company = (
            job.company
            or ""
        ).strip()

    if generated_contact:
        letter.recipient_contact = (
            generated_contact
        )

    if generated_street:
        letter.recipient_street = (
            generated_street
        )

    if generated_postal_code:
        letter.recipient_postal_code = (
            generated_postal_code
        )

    if generated_city:
        letter.recipient_city = (
            generated_city
        )


# =========================================================
# COVER LETTER EDITOR
# =========================================================

@login_required
def cover_letter_view(
    request,
    job_id,
):

    # -----------------------------------------------------
    # JOB
    # -----------------------------------------------------

    job = get_object_or_404(
        JobApplication,
        id=job_id,
        user=request.user,
    )

    # -----------------------------------------------------
    # PROFILE
    # -----------------------------------------------------

    profile, _ = (
        Profile.objects.get_or_create(
            user=request.user
        )
    )

    # -----------------------------------------------------
    # LANGUAGE
    # -----------------------------------------------------

    if request.method == "POST":

        language = (
            request.POST.get(
                "language",
                "de",
            )
            or "de"
        ).strip()

    else:

        language = (
            request.GET.get(
                "language",
                "de",
            )
            or "de"
        ).strip()

    if (
        language
        not in VALID_LANGUAGES
    ):
        language = "de"

    # -----------------------------------------------------
    # DEFAULT NAME
    # -----------------------------------------------------

    default_signature_name = (
        get_default_signature_name(
            request,
            profile,
        )
    )

    # -----------------------------------------------------
    # LETTER
    # -----------------------------------------------------

    letter, _ = (
        CoverLetter.objects.get_or_create(
            user=request.user,
            job=job,
            language=language,
            defaults={
                "recipient_company": (
                    job.company
                    or ""
                ),
                "signature_name": (
                    default_signature_name
                ),
                "signature_type": (
                    "typed"
                ),
            },
        )
    )

    if not letter.signature_name:

        letter.signature_name = (
            default_signature_name
        )

        letter.save(
            update_fields=[
                "signature_name",
                "updated_at",
            ]
        )

    # -----------------------------------------------------
    # MESSAGES
    # -----------------------------------------------------

    error = None
    success = None

    # Keep user's AI editing request visible
    # after form submission.

    ai_instruction = ""

    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        action = (
            request.POST.get(
                "action",
                "",
            )
            or ""
        ).strip()

        # =================================================
        # GENERATE NEW LETTER
        # =================================================

        if action == "generate":

            settings_error = (
                save_generation_settings(
                    request=request,
                    letter=letter,
                    profile=profile,
                )
            )

            if settings_error:

                error = settings_error

            else:

                try:

                    result = (
                        generate_cover_letter(
                            profile=profile,
                            job=job,
                            language=language,
                        )
                    )

                    letter.subject = (
                        result.subject
                    )

                    letter.content = (
                        result.content
                    )

                    apply_generated_recipient_data(
                        letter=letter,
                        result=result,
                        job=job,
                    )

                    letter.save()

                    success = (
                        "Cover letter generated successfully."
                    )

                except Exception as exc:

                    print(
                        "COVER LETTER AI ERROR:",
                        repr(exc),
                    )

                    print(
                        "COVER LETTER AI CAUSE:",
                        repr(
                            getattr(
                                exc,
                                "__cause__",
                                None,
                            )
                        ),
                    )

                    error = (
                        "The cover letter could not "
                        "be generated. Please try again."
                    )

        # =================================================
        # IMPROVE EXISTING LETTER WITH AI
        # =================================================

        elif action == "improve":

            ai_instruction = (
                clean_post_value(
                    request,
                    "ai_instruction",
                )
            )

            # Save whatever the user currently sees
            # in the editor BEFORE sending it to AI.

            save_error = (
                save_letter_fields(
                    request=request,
                    letter=letter,
                    profile=profile,
                )
            )

            if save_error:

                error = save_error

            elif not letter.content.strip():

                error = (
                    "Generate or write the cover letter "
                    "before asking AI to improve it."
                )

            elif not ai_instruction:

                error = (
                    "Tell AI what you want to change."
                )

            else:

                try:

                    result = (
                        improve_cover_letter(
                            profile=profile,
                            job=job,
                            letter=letter,
                            user_instruction=(
                                ai_instruction
                            ),
                        )
                    )

                    letter.subject = (
                        result.subject
                    )

                    letter.content = (
                        result.content
                    )

                    letter.save(
                        update_fields=[
                            "subject",
                            "content",
                            "updated_at",
                        ]
                    )

                    success = (
                        "Cover letter improved successfully."
                    )

                except Exception as exc:

                    print(
                        "COVER LETTER IMPROVE ERROR:",
                        repr(exc),
                    )

                    print(
                        "COVER LETTER IMPROVE CAUSE:",
                        repr(
                            getattr(
                                exc,
                                "__cause__",
                                None,
                            )
                        ),
                    )

                    error = (
                        "The cover letter could not "
                        "be improved. Please try again."
                    )

        # =================================================
        # SAVE
        # =================================================

        elif action == "save":

            save_error = (
                save_letter_fields(
                    request=request,
                    letter=letter,
                    profile=profile,
                )
            )

            if save_error:

                error = save_error

            else:

                success = (
                    "Cover letter saved successfully."
                )

        # =================================================
        # REMOVE SIGNATURE
        # =================================================

        elif action == "remove_signature":

            if letter.signature_image:

                try:

                    letter.signature_image.delete(
                        save=False
                    )

                except Exception as exc:

                    print(
                        "SIGNATURE DELETE ERROR:",
                        repr(exc),
                    )

            letter.signature_image = None
            letter.signature_type = (
                "typed"
            )

            signature_name = (
                clean_post_value(
                    request,
                    "signature_name",
                    200,
                )
            )

            letter.signature_name = (
                signature_name
                or default_signature_name
            )

            letter.save(
                update_fields=[
                    "signature_image",
                    "signature_type",
                    "signature_name",
                    "updated_at",
                ]
            )

            success = (
                "Uploaded signature removed."
            )

        # =================================================
        # DOWNLOAD PDF
        # =================================================

        elif action == "download_pdf":

            save_error = (
                save_letter_fields(
                    request=request,
                    letter=letter,
                    profile=profile,
                )
            )

            if save_error:

                error = save_error

            elif not letter.content.strip():

                error = (
                    "Generate or write the cover letter "
                    "before downloading the PDF."
                )

            else:

                from .cover_letter_pdf import (
                    build_cover_letter_pdf_response,
                )

                return (
                    build_cover_letter_pdf_response(
                        profile=profile,
                        job=job,
                        letter=letter,
                        user=request.user,
                    )
                )

    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "jobs/cover_letter.html",
        {
            "job": job,
            "profile": profile,
            "letter": letter,

            "language": language,

            "language_choices": (
                CoverLetter.LANGUAGE_CHOICES
            ),

            "signature_choices": (
                CoverLetter.SIGNATURE_CHOICES
            ),

            "ai_instruction": (
                ai_instruction
            ),

            "error": error,
            "success": success,
        },
    )