from typing import Literal

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel, Field

from jobs.ai.analyzer import build_user_profile


# =========================================================
# ONE JOB RESULT
# =========================================================

class ProfileMatchItem(BaseModel):
    job_id: int

    score: float = Field(
        ge=1.0,
        le=10.0,
    )

    fit: Literal[
        "GOOD",
        "POSSIBLE",
        "WEAK",
    ]

    reason: str


# =========================================================
# BATCH RESULT
# =========================================================

class ProfileMatchBatch(BaseModel):
    matches: list[ProfileMatchItem]


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are a realistic job-profile matching assistant.

You receive:
1. One verified candidate profile.
2. Several job vacancies.

Your task is to rank EACH vacancy against the verified profile.

IMPORTANT:

This is NOT a job-title similarity score.

The score must represent how realistically the candidate matches
the actual requirements of the vacancy.

Rules:

1. Use ONLY information explicitly present in the verified profile.

2. Never invent:
   - professional experience
   - skills
   - certifications
   - responsibilities
   - technologies
   - language levels

3. Distinguish carefully between:
   - professional experience
   - basic knowledge
   - education
   - personal projects

4. Basic knowledge must NOT be treated as professional experience.

5. Read the vacancy requirements, not only the job title.

6. Mandatory requirements should strongly influence the score.

7. Missing advanced technologies, certifications, language levels,
   or required years of experience must reduce the score realistically.

8. A similar job title alone must NEVER create a high score.

9. Score every job from 1.0 to 10.0.

Use roughly:

8.0 - 10.0
Strong realistic profile match.

6.0 - 7.9
Reasonable profile match with manageable gaps.

4.0 - 5.9
Stretch / weak match.

1.0 - 3.9
Poor match with important missing requirements.

10. fit must be exactly:
GOOD
POSSIBLE
WEAK

11. reason must be short.
Maximum two sentences.

12. Be conservative and realistic.

13. Keep the returned job_id exactly identical to the supplied job_id.

14. Return exactly one result for every supplied vacancy.
"""


# =========================================================
# JOB TEXT
# =========================================================

def build_job_text(job):
    parts = []


    parts.append(
        f"JOB ID: {job.id}"
    )


    if job.title:
        parts.append(
            f"TITLE: {job.title}"
        )


    if job.company:
        parts.append(
            f"COMPANY: {job.company}"
        )


    if job.location:
        parts.append(
            f"LOCATION: {job.location}"
        )


    if job.remote:
        parts.append(
            "REMOTE: Yes"
        )


    description = (
        job.description
        or ""
    ).strip()


    # Discovery ranking does not need an extremely
    # long vacancy body.
    if len(description) > 6000:
        description = description[:6000]


    if description:
        parts.append(
            "DESCRIPTION:\n"
            + description
        )


    return "\n".join(
        parts
    ).strip()


# =========================================================
# BATCH PROFILE RANKING
# =========================================================

def rank_jobs_for_profile(
    profile,
    jobs,
):
    """
    Rank several DiscoveredJob objects with ONE AI request.

    Returns:
        dict[job_id, ProfileMatchItem]
    """

    jobs = list(
        jobs
    )


    if not jobs:
        return {}


    user_profile = (
        build_user_profile(
            profile
        )
    )


    vacancy_blocks = []


    for job in jobs:

        vacancy_blocks.append(
            build_job_text(
                job
            )
        )


    vacancies_text = (
        "\n\n"
        "========================================\n\n"
    ).join(
        vacancy_blocks
    )


    prompt = f"""
VERIFIED CANDIDATE PROFILE
==========================

{user_profile}


VACANCIES
=========

{vacancies_text}


TASK
====

Evaluate every vacancy against the verified candidate profile.

Important:
- This is profile matching, not title matching.
- Return one result for every JOB ID.
- Keep every supplied JOB ID unchanged.
- Be realistic.
- Do not inflate scores.
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
                "content": prompt,
            },
        ],

        text_format=ProfileMatchBatch,
    )


    result = (
        response.output_parsed
    )


    if result is None:
        raise ValueError(
            "AI did not return valid profile ranking."
        )


    expected_ids = {
        job.id
        for job in jobs
    }


    ranked = {}


    for item in result.matches:

        if item.job_id not in expected_ids:
            continue

        ranked[item.job_id] = item


    return ranked