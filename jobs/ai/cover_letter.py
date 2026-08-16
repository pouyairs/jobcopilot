import json
import os

from openai import OpenAI
from pydantic import BaseModel

from .cover_letter_prompts import (
    get_cover_letter_prompt,
    get_improve_cover_letter_prompt,
)


# =========================================================
# STRUCTURED OUTPUTS
# =========================================================

class CoverLetterResult(BaseModel):
    subject: str
    content: str

    recipient_company: str
    recipient_contact: str
    recipient_street: str
    recipient_postal_code: str
    recipient_city: str


class ImprovedCoverLetterResult(BaseModel):
    subject: str
    content: str


# =========================================================
# HELPERS
# =========================================================

def _get_client():
    return OpenAI()


def _get_model():
    model = (
        os.getenv("OPENAI_MODEL", "")
        or ""
    ).strip()

    if not model:
        raise RuntimeError(
            "OPENAI_MODEL environment variable is not configured."
        )

    return model


def _related_items(
    profile,
    related_name,
):
    relation = getattr(
        profile,
        related_name,
        None,
    )

    if relation is None:
        return []

    if hasattr(
        relation,
        "all",
    ):
        return list(
            relation.all()
        )

    return []


def _first_available_related_items(
    profile,
    names,
):
    for name in names:

        items = _related_items(
            profile,
            name,
        )

        if items:
            return items

    return []


# =========================================================
# PROFILE DATA
# =========================================================

def build_profile_data(profile):

    # -----------------------------------------------------
    # EXPERIENCE
    # -----------------------------------------------------

    experiences = []

    for item in _related_items(
        profile,
        "experiences",
    ):

        experiences.append(
            {
                "job_title": getattr(
                    item,
                    "job_title",
                    "",
                ),
                "company": getattr(
                    item,
                    "company",
                    "",
                ),
                "location": getattr(
                    item,
                    "location",
                    "",
                ),
                "start_date": getattr(
                    item,
                    "start_date",
                    "",
                ),
                "end_date": getattr(
                    item,
                    "end_date",
                    "",
                ),
                "description": getattr(
                    item,
                    "description",
                    "",
                ),
                "technologies": getattr(
                    item,
                    "technologies",
                    "",
                ),
            }
        )

    # -----------------------------------------------------
    # EDUCATION
    # -----------------------------------------------------

    educations = []

    for item in _related_items(
        profile,
        "educations",
    ):

        educations.append(
            {
                "degree": getattr(
                    item,
                    "degree",
                    "",
                ),
                "institution": getattr(
                    item,
                    "institution",
                    "",
                ),
                "location": getattr(
                    item,
                    "location",
                    "",
                ),
                "start_date": getattr(
                    item,
                    "start_date",
                    "",
                ),
                "end_date": getattr(
                    item,
                    "end_date",
                    "",
                ),
                "details": getattr(
                    item,
                    "details",
                    "",
                ),
            }
        )

    # -----------------------------------------------------
    # SKILLS
    # -----------------------------------------------------

    skills = []

    for item in _related_items(
        profile,
        "skills",
    ):

        skills.append(
            {
                "name": getattr(
                    item,
                    "name",
                    "",
                ),
                "level": getattr(
                    item,
                    "level",
                    "",
                ),
                "source": getattr(
                    item,
                    "source",
                    "",
                ),
                "do_not_claim": getattr(
                    item,
                    "do_not_claim",
                    False,
                ),
            }
        )

    # -----------------------------------------------------
    # LANGUAGES
    # -----------------------------------------------------

    language_items = (
        _first_available_related_items(
            profile,
            [
                "language_entries",
                "languages_entries",
                "structured_languages",
                "languages_list",
            ],
        )
    )

    languages = []

    for item in language_items:

        languages.append(
            {
                "language": getattr(
                    item,
                    "language",
                    "",
                ),
                "level": getattr(
                    item,
                    "level",
                    "",
                ),
                "original_level": getattr(
                    item,
                    "original_level",
                    "",
                ),
            }
        )

    # -----------------------------------------------------
    # CERTIFICATIONS
    # -----------------------------------------------------

    certifications = []

    for item in _related_items(
        profile,
        "certifications",
    ):

        certifications.append(
            {
                "name": getattr(
                    item,
                    "name",
                    "",
                ),
                "issuer": getattr(
                    item,
                    "issuer",
                    "",
                ),
                "date": getattr(
                    item,
                    "date",
                    "",
                ),
            }
        )

    # -----------------------------------------------------
    # MAIN PROFILE
    # -----------------------------------------------------

    data = {
        "full_name": getattr(
            profile,
            "full_name",
            "",
        ),
        "city": getattr(
            profile,
            "city",
            "",
        ),
        "country": getattr(
            profile,
            "country",
            "",
        ),
        "relocation": getattr(
            profile,
            "relocation",
            False,
        ),
        "professional_summary": getattr(
            profile,
            "professional_summary",
            "",
        ),
        "experience": experiences,
        "education": educations,
        "skills": skills,
        "languages": languages,
        "certifications": certifications,
    }

    # -----------------------------------------------------
    # LEGACY FALLBACK
    # -----------------------------------------------------

    if not experiences:

        data[
            "legacy_experience"
        ] = getattr(
            profile,
            "experience",
            "",
        )

    if not educations:

        data[
            "legacy_education"
        ] = getattr(
            profile,
            "education",
            "",
        )

    if not skills:

        data[
            "legacy_strong_skills"
        ] = getattr(
            profile,
            "strong_skills",
            "",
        )

        data[
            "legacy_basic_skills"
        ] = getattr(
            profile,
            "basic_skills",
            "",
        )

    if not languages:

        legacy_languages = getattr(
            profile,
            "languages",
            "",
        )

        if isinstance(
            legacy_languages,
            str,
        ):

            data[
                "legacy_languages"
            ] = legacy_languages

    legacy_do_not_claim = getattr(
        profile,
        "do_not_claim",
        "",
    )

    if legacy_do_not_claim:

        data[
            "legacy_do_not_claim"
        ] = legacy_do_not_claim

    return data


# =========================================================
# JOB DATA
# =========================================================

def build_job_data(job):

    return {
        "company": (
            job.company
            or ""
        ),
        "job_title": (
            job.job_title
            or ""
        ),
        "city": (
            job.city
            or ""
        ),
        "job_description": (
            job.job_description
            or ""
        ),
        "job_url": (
            job.job_url
            or ""
        ),
        "source": (
            job.source
            or ""
        ),
        "score": (
            str(job.score)
            if job.score is not None
            else ""
        ),
        "decision": (
            job.decision
            or ""
        ),
        "employer_type": (
            job.employer_type
            or ""
        ),
        "zeitarbeit_risk": (
            job.zeitarbeit_risk
        ),
        "strong_matches": (
            job.strong_matches
            or []
        ),
        "gaps": (
            job.gaps
            or []
        ),
        "risks": (
            job.risks
            or []
        ),
        "do_not_claim": (
            job.do_not_claim
            or []
        ),
        "recommended_cv": (
            job.recommended_cv
            or ""
        ),
        "summary": (
            job.summary
            or ""
        ),
    }


# =========================================================
# GENERATE COVER LETTER
# =========================================================

def generate_cover_letter(
    profile,
    job,
    language,
):

    if language not in {
        "de",
        "en",
    }:

        raise ValueError(
            "Language must be 'de' or 'en'."
        )

    client = _get_client()
    model = _get_model()

    payload = {
        "requested_language": language,
        "candidate_profile": (
            build_profile_data(
                profile
            )
        ),
        "job": (
            build_job_data(
                job
            )
        ),
    }

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    get_cover_letter_prompt(
                        language
                    )
                ),
            },
            {
                "role": "user",
                "content": (
                    "Write the cover letter "
                    "using only the verified "
                    "information below.\n\n"
                    + json.dumps(
                        payload,
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    )
                ),
            },
        ],
        text_format=CoverLetterResult,
    )

    result = (
        response.output_parsed
    )

    if result is None:

        raise RuntimeError(
            "The AI did not return "
            "a valid cover letter."
        )

    result.subject = (
        result.subject
        or ""
    ).strip()

    result.content = (
        result.content
        or ""
    ).strip()

    result.recipient_company = (
        result.recipient_company
        or ""
    ).strip()

    result.recipient_contact = (
        result.recipient_contact
        or ""
    ).strip()

    result.recipient_street = (
        result.recipient_street
        or ""
    ).strip()

    result.recipient_postal_code = (
        result.recipient_postal_code
        or ""
    ).strip()

    result.recipient_city = (
        result.recipient_city
        or ""
    ).strip()

    if not result.content:

        raise RuntimeError(
            "The generated cover letter "
            "is empty."
        )

    return result


# =========================================================
# IMPROVE EXISTING COVER LETTER
# =========================================================

def improve_cover_letter(
    profile,
    job,
    letter,
    user_instruction,
):

    instruction = (
        user_instruction
        or ""
    ).strip()

    if not instruction:

        raise ValueError(
            "Please enter an instruction "
            "for improving the cover letter."
        )

    language = (
        letter.language
        or "de"
    ).strip()

    if language not in {
        "de",
        "en",
    }:

        raise ValueError(
            "Unsupported cover letter language."
        )

    client = _get_client()
    model = _get_model()

    payload = {
        "requested_language": language,

        "candidate_profile": (
            build_profile_data(
                profile
            )
        ),

        "job": (
            build_job_data(
                job
            )
        ),

        "current_cover_letter": {
            "subject": (
                letter.subject
                or ""
            ),
            "content": (
                letter.content
                or ""
            ),
        },

        "user_editing_request": (
            instruction
        ),
    }

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    get_improve_cover_letter_prompt(
                        language
                    )
                ),
            },
            {
                "role": "user",
                "content": (
                    "Improve the existing "
                    "cover letter according "
                    "to the user's request.\n\n"
                    + json.dumps(
                        payload,
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    )
                ),
            },
        ],
        text_format=ImprovedCoverLetterResult,
    )

    result = (
        response.output_parsed
    )

    if result is None:

        raise RuntimeError(
            "The AI did not return "
            "a valid edited cover letter."
        )

    result.subject = (
        result.subject
        or ""
    ).strip()

    result.content = (
        result.content
        or ""
    ).strip()

    if not result.content:

        raise RuntimeError(
            "The edited cover letter "
            "is empty."
        )

    return result