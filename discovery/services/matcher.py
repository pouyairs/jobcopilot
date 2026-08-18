import re
from collections import defaultdict
from dataclasses import dataclass

from django.db.models import Q

from discovery.models import (
    DiscoveredJob,
    JobSearchTarget,
)


# =========================================================
# CONFIG
# =========================================================

DEFAULT_CANDIDATE_LIMIT = 600
DEFAULT_PER_TARGET_LIMIT = 50
DEFAULT_FINAL_LIMIT = 30

# Cheap matcher quality gate.
# This is NOT the final profile score.
MIN_TITLE_QUALITY_SCORE = 55.0

# Soft source diversity.
# Each already-selected job from the same source slightly
# reduces that source's priority for the next selection.
SOURCE_DIVERSITY_PENALTY = 4.0


# =========================================================
# GENERIC WORDS
# =========================================================

GENERIC_TITLE_WORDS = {
    "junior",
    "senior",
    "specialist",
    "employee",
    "mitarbeiter",
    "mitarbeiterin",
    "mwd",
    "m/w/d",
    "fmd",
    "f/m/d",
    "remote",
    "hybrid",
    "fulltime",
    "full-time",
    "parttime",
    "part-time",
    "all",
    "genders",
}


# =========================================================
# TITLE FAMILIES
# =========================================================

RELATED_TITLE_TERMS = {
    "it support": [
        "it support",
        "technical support",
        "user support",
        "desktop support",
        "service desk",
        "helpdesk",
        "help desk",
        "onsite support",
        "on site support",
        "field support",
        "field service",
        "workplace support",
        "it technician",
        "it-techniker",
        "it techniker",
        "support engineer",
        "support specialist",
        "application support",
        "applikationssupport",
    ],

    "application support": [
        "application support",
        "applikationssupport",
        "software support",
        "technical support",
        "support specialist",
        "support engineer",
        "it support",
        "application specialist",
        "application manager",
    ],

    "software tester": [
        "software tester",
        "software testing",
        "qa tester",
        "quality assurance",
        "qa engineer",
        "test engineer",
        "tester",
        "test analyst",
        "software test",
        "test automation",
    ],

    "customer support": [
        "customer support",
        "customer service",
        "customer care",
        "client support",
        "service agent",
        "support agent",
        "customer success",
    ],

    "customer manager": [
        "customer manager",
        "account manager",
        "customer success",
        "client manager",
        "customer care",
    ],
}


# =========================================================
# IT CONTEXT
# =========================================================

IT_CONTEXT_TERMS = [
    "it",
    "information technology",
    "technical",
    "technik",
    "techniker",
    "technician",
    "software",
    "hardware",
    "system",
    "systems",
    "systeme",
    "application",
    "applikation",
    "desktop",
    "workplace",
    "service desk",
    "helpdesk",
    "help desk",
    "network",
    "netzwerk",
    "windows",
    "microsoft",
    "cloud",
    "infrastructure",
    "infrastruktur",
    "computer",
    "pc",
    "endpoint",
    "field service",
    "onsite",
]


GENERIC_NON_IT_SUPPORT_TERMS = [
    "after sales support",
    "store support",
    "sales support",
    "supplier support",
    "operations support",
    "office support",
    "project support",
    "administrative support",
    "marketing support",
    "finance support",
    "logistics support",
    "rework support",
    "sustainability support",
]


# =========================================================
# ZEITARBEIT
# =========================================================

ZEITARBEIT_TERMS = [
    "zeitarbeit",
    "arbeitnehmerüberlassung",
    "arbeitnehmerueberlassung",
    "personalvermittlung",
    "personaldienstleister",
    "staffing",
    "temporary employment",
    "temporary worker",
    "temp agency",
]


# =========================================================
# FOREIGN LOCATIONS
# =========================================================

FOREIGN_LOCATION_MARKERS = [
    "united kingdom",
    "england",
    "scotland",
    "wales",
    "london",

    "france",
    "paris",

    "netherlands",
    "amsterdam",
    "rotterdam",

    "spain",
    "madrid",
    "barcelona",

    "italy",
    "milan",
    "rome",

    "poland",
    "warsaw",
    "krakow",

    "austria",
    "vienna",
    "wien",

    "switzerland",
    "zurich",
    "zuerich",
    "geneva",

    "belgium",
    "brussels",

    "ireland",
    "dublin",

    "portugal",
    "lisbon",

    "sweden",
    "stockholm",

    "denmark",
    "copenhagen",

    "norway",
    "oslo",

    "finland",
    "helsinki",

    "czech",
    "prague",

    "hungary",
    "budapest",

    "romania",
    "bucharest",

    "greece",
    "athens",
]


# =========================================================
# RESULT
# =========================================================

@dataclass
class MatchResult:
    score: float
    title_score: float
    location_score: float
    remote_score: float
    zeitarbeit_penalty: float
    reason: str


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(value):
    if not value:
        return ""

    value = str(
        value
    ).lower().strip()

    value = (
        value
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )

    value = re.sub(
        r"[^a-z0-9\s\-\/]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def tokenize(value):
    normalized = normalize_text(
        value
    )

    tokens = []

    for token in normalized.split():
        token = token.strip()

        if not token:
            continue

        if token in GENERIC_TITLE_WORDS:
            continue

        if len(token) <= 1:
            continue

        tokens.append(
            token
        )

    return set(
        tokens
    )


# =========================================================
# TARGET FAMILY
# =========================================================

def detect_target_family(
    target_title,
):
    normalized = normalize_text(
        target_title
    )

    for family in RELATED_TITLE_TERMS:
        normalized_family = (
            normalize_text(
                family
            )
        )

        if (
            normalized_family
            in normalized
        ):
            return family

    if (
        "support"
        in normalized
        and "it"
        in normalized
    ):
        return "it support"

    if (
        "tester"
        in normalized
        or "testing"
        in normalized
        or "qa"
        in normalized.split()
    ):
        return "software tester"

    return ""


# =========================================================
# IT CONTEXT DETECTION
# =========================================================

def has_it_context(
    value,
):
    normalized = normalize_text(
        value
    )

    if not normalized:
        return False

    for term in IT_CONTEXT_TERMS:
        normalized_term = (
            normalize_text(
                term
            )
        )

        if (
            normalized_term
            in normalized
        ):
            return True

    return False


def is_generic_non_it_support(
    job_title,
):
    normalized = normalize_text(
        job_title
    )

    for term in (
        GENERIC_NON_IT_SUPPORT_TERMS
    ):
        normalized_term = (
            normalize_text(
                term
            )
        )

        if (
            normalized_term
            in normalized
        ):
            return True

    return False


# =========================================================
# TITLE MATCHING
# =========================================================

def title_phrase_match(
    target_title,
    job_title,
):
    target_normalized = (
        normalize_text(
            target_title
        )
    )

    job_normalized = (
        normalize_text(
            job_title
        )
    )

    if (
        not target_normalized
        or not job_normalized
    ):
        return 0.0

    target_family = (
        detect_target_family(
            target_title
        )
    )

    # -----------------------------------------------------
    # Exact / containment
    # -----------------------------------------------------

    if (
        target_normalized
        == job_normalized
    ):
        score = 100.0

    elif (
        target_normalized
        in job_normalized
    ):
        score = 95.0

    elif (
        job_normalized
        in target_normalized
    ):
        score = 90.0

    else:
        target_tokens = tokenize(
            target_title
        )

        job_tokens = tokenize(
            job_title
        )

        if (
            not target_tokens
            or not job_tokens
        ):
            score = 0.0

        else:
            overlap = (
                target_tokens
                & job_tokens
            )

            token_ratio = (
                len(overlap)
                / len(target_tokens)
            )

            score = (
                token_ratio
                * 80.0
            )

    # -----------------------------------------------------
    # Related title family bonus
    # -----------------------------------------------------

    if target_family:
        related_terms = (
            RELATED_TITLE_TERMS.get(
                target_family,
                [],
            )
        )

        for related_term in (
            related_terms
        ):
            normalized_related = (
                normalize_text(
                    related_term
                )
            )

            if (
                normalized_related
                in job_normalized
            ):
                score = max(
                    score,
                    78.0,
                )

    # =====================================================
    # IT SUPPORT QUALITY CONTROL
    # =====================================================

    if (
        target_family
        in {
            "it support",
            "application support",
        }
    ):
        job_has_support = (
            "support"
            in job_normalized
        )

        job_has_it_context = (
            has_it_context(
                job_title
            )
        )

        # Generic support role with no IT meaning.
        if (
            job_has_support
            and not job_has_it_context
        ):
            score = min(
                score,
                35.0,
            )

        # Explicitly known non-IT support patterns.
        if (
            is_generic_non_it_support(
                job_title
            )
            and not job_has_it_context
        ):
            score = min(
                score,
                25.0,
            )

        # Techniker / technician alone is not enough.
        if (
            (
                "techniker"
                in job_normalized
                or "technician"
                in job_normalized
            )
            and "support"
            not in job_normalized
            and "it"
            not in job_normalized
            and "software"
            not in job_normalized
            and "system"
            not in job_normalized
        ):
            score = min(
                score,
                40.0,
            )

    return min(
        round(
            score,
            1,
        ),
        100.0,
    )


# =========================================================
# LOCATION MATCHING
# =========================================================

def location_match(
    target,
    job,
):
    target_location = (
        normalize_text(
            target.location
        )
    )

    job_location = (
        normalize_text(
            job.location
        )
    )

    # No location restriction.
    if not target_location:
        return 100.0

    germany_terms = {
        "germany",
        "deutschland",
        "de",
    }

    # -----------------------------------------------------
    # Germany-wide
    # -----------------------------------------------------

    if (
        target_location
        in germany_terms
    ):
        for marker in (
            FOREIGN_LOCATION_MARKERS
        ):
            normalized_marker = (
                normalize_text(
                    marker
                )
            )

            if (
                normalized_marker
                in job_location
            ):
                return 10.0

        if job_location:
            return 90.0

        if job.remote:
            return 85.0

        return 70.0

    # -----------------------------------------------------
    # Specific city / region
    # -----------------------------------------------------

    if not job_location:
        if job.remote:
            return 80.0

        return 35.0

    if (
        target_location
        == job_location
    ):
        return 100.0

    if (
        target_location
        in job_location
    ):
        return 95.0

    if (
        job_location
        in target_location
    ):
        return 90.0

    target_parts = set(
        target_location.split()
    )

    job_parts = set(
        job_location.split()
    )

    overlap = (
        target_parts
        & job_parts
    )

    if overlap:
        return 70.0

    if job.remote:
        return 75.0

    return 25.0


# =========================================================
# REMOTE MATCHING
# =========================================================

def remote_match(
    target,
    job,
):
    if target.remote:
        if job.remote:
            return 100.0

        return 70.0

    if job.remote:
        return 60.0

    return 100.0


# =========================================================
# ZEITARBEIT
# =========================================================

def contains_zeitarbeit(
    job,
):
    haystack = normalize_text(
        " ".join(
            [
                job.title or "",
                job.company or "",
                job.description or "",
            ]
        )
    )

    for term in ZEITARBEIT_TERMS:
        normalized_term = (
            normalize_text(
                term
            )
        )

        if (
            normalized_term
            in haystack
        ):
            return True

    return False


# =========================================================
# FINAL CHEAP MATCH
# =========================================================

def calculate_match(
    target,
    job,
):
    title_score = (
        title_phrase_match(
            target.title,
            job.title,
        )
    )

    location_score = (
        location_match(
            target,
            job,
        )
    )

    remote_score = (
        remote_match(
            target,
            job,
        )
    )

    zeitarbeit_penalty = 0.0

    if (
        target.exclude_zeitarbeit
        and contains_zeitarbeit(
            job
        )
    ):
        zeitarbeit_penalty = 35.0

    final_score = (
        title_score * 0.68
        + location_score * 0.22
        + remote_score * 0.10
        - zeitarbeit_penalty
    )

    final_score = max(
        0.0,
        min(
            final_score,
            100.0,
        ),
    )

    reason_parts = []

    if title_score >= 85:
        reason_parts.append(
            "Strong job-title match"
        )

    elif title_score >= 65:
        reason_parts.append(
            "Related job-title match"
        )

    elif title_score >= 50:
        reason_parts.append(
            "Partial job-title match"
        )

    else:
        reason_parts.append(
            "Weak title match"
        )

    if location_score >= 90:
        reason_parts.append(
            "location matches"
        )

    elif job.remote:
        reason_parts.append(
            "remote option"
        )

    elif target.location:
        reason_parts.append(
            "location differs"
        )

    if zeitarbeit_penalty:
        reason_parts.append(
            (
                "possible temporary-"
                "employment risk"
            )
        )

    return MatchResult(
        score=round(
            final_score,
            1,
        ),

        title_score=round(
            title_score,
            1,
        ),

        location_score=round(
            location_score,
            1,
        ),

        remote_score=round(
            remote_score,
            1,
        ),

        zeitarbeit_penalty=round(
            zeitarbeit_penalty,
            1,
        ),

        reason=", ".join(
            reason_parts
        ),
    )


# =========================================================
# DATABASE PRE-FILTER
# =========================================================

def get_candidate_jobs_for_target(
    target,
    limit=DEFAULT_CANDIDATE_LIMIT,
):
    """
    Broad DB candidate search.

    It intentionally knows nothing about source names.
    """

    title_tokens = list(
        tokenize(
            target.title
        )
    )

    queryset = (
        DiscoveredJob.objects
        .filter(
            is_active=True
        )
    )

    title_query = Q()

    for token in title_tokens:
        title_query |= Q(
            title__icontains=token
        )

    target_normalized = (
        normalize_text(
            target.title
        )
    )

    target_family = (
        detect_target_family(
            target.title
        )
    )

    # -----------------------------------------------------
    # Related family terms
    # -----------------------------------------------------

    if target_family:
        for term in (
            RELATED_TITLE_TERMS.get(
                target_family,
                [],
            )
        ):
            title_query |= Q(
                title__icontains=term
            )

    # -----------------------------------------------------
    # Support discovery remains broad at DB level.
    # Python quality gate will remove bad matches later.
    # -----------------------------------------------------

    if (
        "support"
        in target_normalized
    ):
        broad_support_terms = [
            "support",
            "helpdesk",
            "service desk",
            "technician",
            "techniker",
            "workplace",
            "field service",
            "application",
        ]

        for term in (
            broad_support_terms
        ):
            title_query |= Q(
                title__icontains=term
            )

    if title_query:
        queryset = (
            queryset.filter(
                title_query
            )
        )

    return list(
        queryset.order_by(
            "-published_at",
            "-first_seen_at",
        )[:limit]
    )


# =========================================================
# CROSS-SOURCE DUPLICATE KEY
# =========================================================

def build_duplicate_key(
    job,
):
    """
    Source-independent approximate vacancy identity.
    """

    title = normalize_text(
        job.title
    )

    company = normalize_text(
        job.company
    )

    location = normalize_text(
        job.location
    )

    # Remove common gender markers.
    noise_patterns = [
        r"\bm\/w\/d\b",
        r"\bw\/m\/d\b",
        r"\bmwd\b",
        r"\bf\/m\/d\b",
        r"\bd\/m\/w\b",
        r"\ball genders\b",
    ]

    for pattern in noise_patterns:
        title = re.sub(
            pattern,
            "",
            title,
        )

    title = re.sub(
        r"\s+",
        " ",
        title,
    ).strip()

    # Remove postcode from beginning of location.
    location = re.sub(
        r"^\d{5}\s+",
        "",
        location,
    )

    location_parts = (
        location.split()
    )

    compact_location = " ".join(
        location_parts[:2]
    )

    return (
        title,
        company,
        compact_location,
    )


# =========================================================
# CROSS-SOURCE DEDUPLICATION
# =========================================================

def deduplicate_matches(
    matches,
):
    best_by_key = {}

    for item in matches:
        job = item["job"]

        key = build_duplicate_key(
            job
        )

        if (
            not key[0]
            or not key[1]
        ):
            key = (
                "job-id",
                job.id,
            )

        existing = (
            best_by_key.get(
                key
            )
        )

        if existing is None:
            best_by_key[
                key
            ] = item

            continue

        if (
            item["score"]
            > existing["score"]
        ):
            best_by_key[
                key
            ] = item

            continue

        if (
            item["score"]
            == existing["score"]
        ):
            new_description_length = len(
                item["job"].description
                or ""
            )

            old_description_length = len(
                existing["job"].description
                or ""
            )

            if (
                new_description_length
                > old_description_length
            ):
                best_by_key[
                    key
                ] = item

    return list(
        best_by_key.values()
    )


# =========================================================
# SOFT SOURCE DIVERSITY
# =========================================================

def diversify_by_source(
    matches,
    limit=DEFAULT_FINAL_LIMIT,
):
    """
    Source-agnostic soft diversity.

    Better jobs remain more important than source balance.

    A source receives a small ranking penalty each time
    one of its jobs has already been selected.

    Result:
    - multiple good sources get visibility
    - weak jobs are not injected just to satisfy quotas
    - one strong source may still dominate when deserved
    """

    if not matches:
        return []

    remaining = list(
        matches
    )

    selected = []

    selected_by_source = (
        defaultdict(int)
    )

    while (
        remaining
        and len(selected) < limit
    ):
        best_index = None
        best_adjusted_score = None

        for index, item in enumerate(
            remaining
        ):
            source = (
                item["job"].source
                or "unknown"
            )

            source_count = (
                selected_by_source[
                    source
                ]
            )

            adjusted_score = (
                float(
                    item["score"]
                )
                - (
                    source_count
                    * SOURCE_DIVERSITY_PENALTY
                )
            )

            if (
                best_adjusted_score
                is None
                or adjusted_score
                > best_adjusted_score
            ):
                best_adjusted_score = (
                    adjusted_score
                )

                best_index = index

        if best_index is None:
            break

        selected_item = (
            remaining.pop(
                best_index
            )
        )

        selected.append(
            selected_item
        )

        source = (
            selected_item[
                "job"
            ].source
            or "unknown"
        )

        selected_by_source[
            source
        ] += 1

    return selected


# =========================================================
# TARGET SHORTLIST
# =========================================================

def shortlist_for_target(
    target,
    candidate_limit=DEFAULT_CANDIDATE_LIMIT,
    shortlist_limit=DEFAULT_PER_TARGET_LIMIT,
):
    jobs = (
        get_candidate_jobs_for_target(
            target=target,
            limit=candidate_limit,
        )
    )

    ranked = []

    minimum_score = float(
        target.minimum_match_score
    )

    minimum_percent = (
        minimum_score
        * 10.0
    )

    for job in jobs:
        result = (
            calculate_match(
                target=target,
                job=job,
            )
        )

        # -------------------------------------------------
        # Quality gate:
        # location cannot rescue a clearly unrelated title.
        # -------------------------------------------------

        if (
            result.title_score
            < MIN_TITLE_QUALITY_SCORE
        ):
            continue

        # -------------------------------------------------
        # User threshold
        # -------------------------------------------------

        if (
            result.score
            < minimum_percent
        ):
            continue

        ranked.append(
            {
                "job": job,
                "target": target,
                "score": result.score,
                "reason": result.reason,
                "details": result,
            }
        )

    ranked.sort(
        key=lambda item: (
            item["score"]
        ),
        reverse=True,
    )

    return ranked[
        :shortlist_limit
    ]


# =========================================================
# USER SHORTLIST
# =========================================================

def shortlist_for_user(
    user,
    per_target_limit=DEFAULT_PER_TARGET_LIMIT,
    final_limit=DEFAULT_FINAL_LIMIT,
):
    """
    Source-independent discovery shortlist.

    Pipeline:

    Active targets
        ↓
    Broad DB candidate search
        ↓
    Cheap relevance score
        ↓
    Title quality gate
        ↓
    Same-job / multi-target dedup
        ↓
    Cross-source dedup
        ↓
    Soft source diversity
        ↓
    Final shortlist

    No source names are hardcoded here.
    """

    targets = (
        JobSearchTarget.objects
        .filter(
            user=user,
            active=True,
        )
        .order_by(
            "title"
        )
    )

    best_by_job = {}

    for target in targets:
        matches = (
            shortlist_for_target(
                target=target,
                candidate_limit=(
                    DEFAULT_CANDIDATE_LIMIT
                ),
                shortlist_limit=(
                    per_target_limit
                ),
            )
        )

        for item in matches:
            job = item["job"]

            existing = (
                best_by_job.get(
                    job.id
                )
            )

            if (
                existing is None
                or item["score"]
                > existing["score"]
            ):
                best_by_job[
                    job.id
                ] = item

    final_results = list(
        best_by_job.values()
    )

    final_results.sort(
        key=lambda item: (
            item["score"]
        ),
        reverse=True,
    )

    # -----------------------------------------------------
    # Duplicate vacancy across multiple sources
    # -----------------------------------------------------

    final_results = (
        deduplicate_matches(
            final_results
        )
    )

    final_results.sort(
        key=lambda item: (
            item["score"]
        ),
        reverse=True,
    )

    # -----------------------------------------------------
    # Generic soft source balance
    # -----------------------------------------------------

    final_results = (
        diversify_by_source(
            final_results,
            limit=final_limit,
        )
    )

    return final_results