from typing import Literal

from django.conf import settings

from openai import OpenAI
from pydantic import BaseModel, Field


class CVExperience(BaseModel):

    job_title: str = ""
    company: str = ""
    location: str = ""

    start_date: str = ""
    end_date: str = ""

    responsibilities: list[str] = Field(
        default_factory=list
    )

    technologies: list[str] = Field(
        default_factory=list
    )


class CVEducation(BaseModel):

    degree: str = ""
    institution: str = ""
    location: str = ""

    start_date: str = ""
    end_date: str = ""

    details: str = ""


class CVSkill(BaseModel):

    name: str

    level: Literal[
        "unclassified",
        "basic",
        "intermediate",
        "advanced",
        "expert"
    ] = "unclassified"

    source: Literal[
        "professional",
        "education",
        "project",
        "course",
        "self_taught",
        "unspecified"
    ] = "unspecified"


class CVLanguage(BaseModel):

    language: str

    level: Literal[
        "unspecified",
        "A1",
        "A2",
        "B1",
        "B2",
        "C1",
        "C2",
        "native"
    ] = "unspecified"

    original_level: str = ""


class CVCertification(BaseModel):

    name: str
    issuer: str = ""
    date: str = ""


class ParsedCV(BaseModel):

    full_name: str = ""
    city: str = ""
    country: str = ""

    professional_summary: str = ""

    experiences: list[CVExperience] = Field(
        default_factory=list
    )

    educations: list[CVEducation] = Field(
        default_factory=list
    )

    skills: list[CVSkill] = Field(
        default_factory=list
    )

    languages: list[CVLanguage] = Field(
        default_factory=list
    )

    certifications: list[CVCertification] = Field(
        default_factory=list
    )


CV_SYSTEM_PROMPT = """
You extract structured career information from a CV.

The CV may be written in German or English.

IMPORTANT RULES:

1. Only extract information supported by the CV.

2. Never invent:
   - skills
   - employers
   - responsibilities
   - tools
   - dates
   - education
   - certifications
   - language levels
   - achievements

3. Keep every work experience as a separate record.

4. Every responsibility or task must be a SEPARATE item.

5. Never merge multiple CV bullet points into one paragraph.

6. If the CV contains four responsibility bullets for a job,
   normally return four separate responsibility items.

7. Preserve the original meaning.
   Do not rewrite responsibilities to sound more senior.

8. Extract technologies only when they are explicitly supported
   by the CV.

SKILL LEVEL RULES:

9. Use "basic" when the CV explicitly indicates:
   Basic, Grundlagen, Beginner, Introductory, Limited,
   or similar wording.

10. Use "intermediate" when the CV provides evidence of regular,
    practical use but not advanced ownership or deep expertise.

11. Use "advanced" only when the skill is clearly demonstrated
    repeatedly in professional work with independent responsibility.

12. Use "expert" only when the CV explicitly supports expert-level
    mastery, leadership, architecture, mentoring, or equivalent
    deep experience.

13. If a skill is only listed in a skills section and its real
    proficiency cannot be determined, use "unclassified".

14. NEVER classify all listed skills as advanced.

SKILL SOURCE RULES:

15. Use "professional" when demonstrated in paid professional work.

16. Use "education" when supported mainly by university or formal
    education.

17. Use "project" for personal/non-professional projects.

18. Use "course" for courses or certifications.

19. Use "self_taught" only when the CV explicitly indicates
    self-learning.

20. Otherwise use "unspecified".

LANGUAGE RULES:

21. Never upgrade language ability.

22. Standard CEFR levels are:
    A1, A2, B1, B2, C1, C2.

23. If the CV says B1+, store:
    level = B1
    original_level = B1+

24. If the CV says B2-Niveau, store:
    level = B2
    original_level = B2-Niveau

25. If the CV says Native or Muttersprache:
    level = native
    original_level should preserve the original wording.

26. If the CV only says Fluent, Good, Advanced,
    Gute Kenntnisse or another non-CEFR description,
    do NOT guess a CEFR level.

    Use:
    level = unspecified

    and store the wording in original_level.

27. Education and certifications must remain separate records.

28. Missing information must remain empty.

29. This is CV extraction, not CV improvement.
"""


def parse_cv_with_ai(cv_text):

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    response = client.responses.parse(
        model=settings.OPENAI_MODEL,

        input=[
            {
                "role": "system",
                "content": CV_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    "Extract this CV into the required "
                    "structured profile:\n\n"
                    f"{cv_text}"
                ),
            },
        ],

        text_format=ParsedCV,
    )

    result = response.output_parsed

    if result is None:
        raise ValueError(
            "The AI could not parse this CV."
        )

    return result