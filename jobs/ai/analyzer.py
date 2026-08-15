import json
from typing import Literal

from django.conf import settings

from openai import OpenAI
from pydantic import BaseModel, Field


from .prompts import SYSTEM_PROMPT


# =========================================================
# STRUCTURED AI RESULT
# =========================================================

class JobAnalysisResult(BaseModel):

    company: str = ""

    job_title: str = ""

    city: str = ""

    score: float = Field(
        ge=1,
        le=10
    )

    decision: Literal[
        "APPLY",
        "STRETCH",
        "SKIP"
    ]

    employer_type: Literal[
        "Direct Employer",
        "Recruitment Agency",
        "Unclear"
    ]

    zeitarbeit_risk: bool = False

    strong_matches: list[str] = Field(
        default_factory=list
    )

    gaps: list[str] = Field(
        default_factory=list
    )

    risks: list[str] = Field(
        default_factory=list
    )

    recommended_cv: str = ""

    do_not_claim: list[str] = Field(
        default_factory=list
    )

    summary: str = ""


# =========================================================
# EXPERIENCE
# =========================================================

def build_experiences(profile):

    experiences = []

    for item in profile.experiences.all():

        responsibilities = []

        if item.description:

            for raw_line in item.description.splitlines():

                line = raw_line.strip()

                line = line.lstrip(
                    "•-*–— "
                ).strip()

                if line:
                    responsibilities.append(
                        line
                    )

        technologies = []

        if item.technologies:

            for raw_line in item.technologies.splitlines():

                line = raw_line.strip()

                line = line.lstrip(
                    "•-*–— "
                ).strip()

                if line:
                    technologies.append(
                        line
                    )

        experiences.append(
            {
                "job_title": item.job_title,
                "company": item.company,
                "location": item.location,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "responsibilities": responsibilities,
                "technologies": technologies,
            }
        )

    return experiences


# =========================================================
# EDUCATION
# =========================================================

def build_education(profile):

    education = []

    for item in profile.educations.all():

        education.append(
            {
                "degree": item.degree,
                "institution": item.institution,
                "location": item.location,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "details": item.details,
            }
        )

    return education


# =========================================================
# SKILLS
# =========================================================

def build_skills(profile):

    skills = []

    for item in profile.skills.all():

        skills.append(
            {
                "name": item.name,

                "level": item.level,

                "level_label": (
                    item.get_level_display()
                ),

                "source": item.source,

                "source_label": (
                    item.get_source_display()
                ),

                "do_not_claim": (
                    item.do_not_claim
                ),
            }
        )

    return skills


# =========================================================
# LANGUAGES
# =========================================================

def build_languages(profile):

    languages = []

    for item in profile.language_entries.all():

        languages.append(
            {
                "language": item.language,

                "level": item.level,

                "level_label": (
                    item.get_level_display()
                ),

                "original_level": (
                    item.original_level
                ),
            }
        )

    return languages


# =========================================================
# CERTIFICATIONS
# =========================================================

def build_certifications(profile):

    certifications = []

    for item in profile.certifications.all():

        certifications.append(
            {
                "name": item.name,
                "issuer": item.issuer,
                "date": item.date,
            }
        )

    return certifications


# =========================================================
# LEGACY PROFILE FALLBACK
# =========================================================

def build_legacy_profile(profile):

    return {
        "education": (
            profile.education.strip()
            if profile.education
            else ""
        ),

        "experience": (
            profile.experience.strip()
            if profile.experience
            else ""
        ),

        "strong_skills": (
            profile.strong_skills.strip()
            if profile.strong_skills
            else ""
        ),

        "basic_skills": (
            profile.basic_skills.strip()
            if profile.basic_skills
            else ""
        ),

        "languages": (
            profile.languages.strip()
            if profile.languages
            else ""
        ),

        "do_not_claim": (
            profile.do_not_claim.strip()
            if profile.do_not_claim
            else ""
        ),
    }


# =========================================================
# BUILD VERIFIED USER PROFILE
# =========================================================

def build_user_profile(profile):

    experiences = build_experiences(
        profile
    )

    education = build_education(
        profile
    )

    skills = build_skills(
        profile
    )

    languages = build_languages(
        profile
    )

    certifications = build_certifications(
        profile
    )


    profile_data = {
        "personal": {
            "full_name": profile.full_name,
            "city": profile.city,
            "country": profile.country,
            "willing_to_relocate": (
                profile.relocation
            ),
        },

        "professional_summary": (
            profile.professional_summary
        ),

        "work_experience": experiences,

        "education": education,

        "skills": skills,

        "languages": languages,

        "certifications": certifications,
    }


    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------
    #
    # The old Profile text fields are used ONLY when
    # structured profile sections are empty.
    #

    structured_empty = (
        not experiences
        and not education
        and not skills
        and not languages
        and not certifications
    )

    if structured_empty:

        profile_data[
            "legacy_profile_fallback"
        ] = build_legacy_profile(
            profile
        )


    return profile_data


# =========================================================
# ANALYSIS LANGUAGE
# =========================================================

def get_analysis_language(
    analysis_language
):

    if analysis_language == "fa":

        return (
            "Write all explanations in Persian (Farsi). "
            "Keep company names, job titles, technology names "
            "and certification names in their original form."
        )

    return (
        "Write all explanations in English. "
        "Keep company names, job titles, technology names "
        "and certification names in their original form."
    )


# =========================================================
# ANALYZE JOB
# =========================================================

def analyze_job(
    profile,
    job_description,
    analysis_language="en"
):

    if not settings.OPENAI_API_KEY:

        raise ValueError(
            "OPENAI_API_KEY is not configured."
        )

    if not job_description.strip():

        raise ValueError(
            "Job description is empty."
        )


    user_profile = build_user_profile(
        profile
    )


    profile_json = json.dumps(
        user_profile,
        ensure_ascii=False,
        indent=2
    )


    language_instruction = (
        get_analysis_language(
            analysis_language
        )
    )


    user_prompt = f"""
{language_instruction}

============================================================
VERIFIED CANDIDATE PROFILE
============================================================

{profile_json}

============================================================
JOB VACANCY
============================================================

{job_description}

============================================================
YOUR TASK
============================================================

Evaluate this vacancy against the VERIFIED candidate profile.

Important:

- Base the score on evidence, not keyword overlap.
- Professional experience is stronger evidence than courses,
  education or personal projects.
- Respect every skill level.
- Respect every skill evidence/source.
- Ignore skills marked do_not_claim as positive evidence.
- Never upgrade language levels.
- Identify important mandatory gaps.
- Be conservative about advanced or expert requirements.
- Do not invent information missing from either the profile
  or vacancy.
- Determine employer type only from the supplied vacancy.
- Determine Zeitarbeit / Arbeitnehmerüberlassung risk only
  when supported by the vacancy.

Extract company, job title and city from the vacancy when possible.

If they cannot be determined reliably, return an empty string.

Return the requested structured analysis.
"""


    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )


    response = client.responses.parse(
        model=settings.OPENAI_MODEL,

        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        text_format=JobAnalysisResult,
    )


    result = response.output_parsed


    if result is None:

        raise ValueError(
            "The AI did not return a valid job analysis."
        )


    # Safety clamp just in case
    result.score = max(
        1,
        min(
            10,
            round(
                float(result.score),
                1
            )
        )
    )


    return result